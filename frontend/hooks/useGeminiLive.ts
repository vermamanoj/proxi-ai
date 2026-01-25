
import { useState, useEffect, useRef, useCallback } from 'react';
import { GoogleGenAI, LiveServerMessage, Modality } from '@google/genai';
import { LogEntry, MessageSource, ActiveToolState } from '../types';
import { SYSTEM_INSTRUCTION, TOOLS } from '../constants';
import { blobToBase64, createPcmBlob, decodeAudioData, encodePcm } from '../utils/audio';

export const useGeminiLive = () => {
  const [connected, setConnected] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [volume, setVolume] = useState(0);
  const [activeTool, setActiveTool] = useState<ActiveToolState | null>(null);

  // Refs for audio handling to avoid re-renders
  const audioContextRef = useRef<AudioContext | null>(null);
  const inputContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const nextStartTimeRef = useRef<number>(0);
  const sessionRef = useRef<any>(null); 
  const sourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
  
  // Ref for aborting active backend requests
  const abortControllerRef = useRef<AbortController | null>(null);

  const addLog = useCallback((source: MessageSource, text: string, metadata?: any) => {
    setLogs(prev => [...prev, {
      id: Math.random().toString(36).substring(7),
      timestamp: new Date(),
      source,
      text,
      metadata
    }]);
  }, []);

  const handleToolCall = async (functionCalls: any[]) => {
    const responses = [];
    
    for (const call of functionCalls) {
        // --- 1. STOP EXECUTION ---
        if (call.name === 'stop_execution') {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
                abortControllerRef.current = null;
                addLog(MessageSource.SYSTEM, "🛑 Execution Stopped via Voice Command.");
                responses.push({
                    id: call.id,
                    name: call.name,
                    response: { result: "Execution stopped. The background task has been cancelled." }
                });
            } else {
                 responses.push({
                    id: call.id,
                    name: call.name,
                    response: { result: "No active background task to stop." }
                });
            }
            continue;
        }

        // --- 2. DELEGATE TASK ---
        if (call.name === 'delegate_task') {
            const task = call.args.task_description;
            
            addLog(MessageSource.SYSTEM, `Handing off to Gemini 3 Core...`, { task });
            setActiveTool({ name: "Gemini 3 Pro (Reasoning)", startTime: Date.now() });

            // Create new AbortController for this request
            const controller = new AbortController();
            abortControllerRef.current = controller;

            try {
                // RELAY PATTERN:
                // We send the text to the Backend API.
                // CHANGED: complexity from 'fast' to 'deep' to ensure Gemini 3 Pro uses Thinking and assign_mission.
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: task, complexity: 'deep' }), 
                    signal: controller.signal
                });

                if (!response.body) {
                     throw new Error("Empty Response from Backend");
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let done = false;
                let finalSummary = "";
                let failureDetected = false;

                while (!done) {
                    const { value, done: doneReading } = await reader.read();
                    done = doneReading;
                    const chunkValue = decoder.decode(value, { stream: !done });
                    const lines = chunkValue.split('\n').filter(line => line.trim() !== '');

                    for (const line of lines) {
                        try {
                            const data = JSON.parse(line);
                            
                            // Visualize the "Thought Process" of Gemini 3 in the logs
                            if (data.type === 'llm_thought') {
                                addLog(MessageSource.AGENT, `(Thinking) ${data.content}`);
                            } 
                            else if (data.type === 'tool_call_batch') {
                                data.calls.forEach((c: any) => addLog(MessageSource.TOOL, `Core Executing: ${c.name}`, c.args));
                            }
                            else if (data.type === 'tool_result') {
                                addLog(MessageSource.TOOL, `Result: ${data.name}`, { output: data.content });
                                // Passive Failure Detection
                                if (String(data.content).toLowerCase().includes("error") || String(data.content).toLowerCase().includes("failed")) {
                                    failureDetected = true;
                                }
                            }
                            else if (data.type === 'response') {
                                finalSummary = data.content;
                                addLog(MessageSource.AGENT, `Core Result: ${data.content}`);
                            }
                            else if (data.type === 'error') {
                                addLog(MessageSource.SYSTEM, `Core Error Detected: ${data.content}`);
                                failureDetected = true;
                            }
                        } catch (e) {
                            // JSON Parse errors on chunks are common in streams, ignore partials
                        }
                    }
                }

                // INTELLIGENT ERROR INJECTION:
                // If the backend didn't crash but logged errors, force the Voice Agent to acknowledge it.
                if (failureDetected && !finalSummary.toLowerCase().includes("error")) {
                    finalSummary = `(SYSTEM WARNING: Some tools reported errors during execution). ${finalSummary}`;
                }

                // Return the final text from Gemini 3 back to Gemini 2.5 (Voice)
                responses.push({
                    id: call.id,
                    name: call.name,
                    response: { result: finalSummary || "Task finished, but no summary was provided." }
                });

            } catch (err: any) {
                const errMsg = err.message || "";
                
                if (err.name === 'AbortError') {
                    addLog(MessageSource.SYSTEM, "Request Aborted.");
                    responses.push({
                         id: call.id, name: call.name, 
                         response: { result: "Task was cancelled by user." }
                    });
                } 
                else if (errMsg.includes("Failed to fetch") || errMsg.includes("NetworkError") || errMsg.includes("Connection refused")) {
                    addLog(MessageSource.SYSTEM, "❌ CRITICAL: Backend Connection Failed. Is the Python server running?");
                    responses.push({
                        id: call.id,
                        name: call.name,
                        response: { result: "BACKEND_OFFLINE: Connection to Proxi Core failed. Please ensure the Python backend server is running on localhost:8000." }
                    });
                } else {
                    addLog(MessageSource.SYSTEM, `Core Agent Error: ${errMsg}`);
                    responses.push({
                        id: call.id,
                        name: call.name,
                        response: { result: `Critical Error executing task: ${errMsg}. Please report this to the user.` }
                    });
                }
            } finally {
                setActiveTool(null);
                abortControllerRef.current = null;
            }
        } else {
            // Fallback for unknown tools
            responses.push({
                id: call.id,
                name: call.name,
                response: { result: "Error: Unknown tool." }
            });
        }
    }
    return responses;
  };

  const connect = async () => {
    try {
      addLog(MessageSource.SYSTEM, "Initializing Gemini Live Uplink...");
      
      const apiKey = process.env.API_KEY;
      if (!apiKey) {
        throw new Error("API_KEY not found in environment.");
      }

      const ai = new GoogleGenAI({ apiKey });
      
      // Setup Audio Contexts
      inputContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
      
      // Start Microphone
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Connect to Gemini 2.5 (The Voice Interface)
      const sessionPromise = ai.live.connect({
        model: 'gemini-2.5-flash-native-audio-preview-12-2025',
        config: {
          responseModalities: [Modality.AUDIO],
          systemInstruction: SYSTEM_INSTRUCTION,
          tools: [{ functionDeclarations: TOOLS }],
        },
        callbacks: {
          onopen: () => {
            setConnected(true);
            addLog(MessageSource.SYSTEM, "Uplink Established. Audio Stream Active.");
            
            // Setup Audio Processing for Input
            if (!inputContextRef.current) return;
            const source = inputContextRef.current.createMediaStreamSource(stream);
            const processor = inputContextRef.current.createScriptProcessor(4096, 1, 1);
            
            processor.onaudioprocess = (e) => {
              const inputData = e.inputBuffer.getChannelData(0);
              // Calculate volume for visualizer
              let sum = 0;
              for (let i = 0; i < inputData.length; i++) {
                sum += inputData[i] * inputData[i];
              }
              setVolume(Math.sqrt(sum / inputData.length));

              // Send to Gemini
              const pcmBlob = createPcmBlob(inputData);
              sessionPromise.then(session => {
                session.sendRealtimeInput({ media: pcmBlob });
              });
            };

            source.connect(processor);
            processor.connect(inputContextRef.current.destination);
            
            sourceRef.current = source;
            processorRef.current = processor;
          },
          onmessage: async (message: LiveServerMessage) => {
             // 1. Handle Interruption (Barge-In)
             if (message.serverContent?.interrupted) {
                 addLog(MessageSource.SYSTEM, "🛑 Audio Interrupted by User");
                 // Clear all playing audio
                 sourcesRef.current.forEach(source => {
                     try { source.stop(); } catch(e) {}
                 });
                 sourcesRef.current.clear();
                 // Reset time cursor to current
                 if (audioContextRef.current) {
                     nextStartTimeRef.current = audioContextRef.current.currentTime;
                 }
                 return; // Skip processing other content in this interrupted message
             }

             // 2. Handle Tool Calls (The Relay Logic)
             if (message.toolCall) {
                const responses = await handleToolCall(message.toolCall.functionCalls);
                sessionPromise.then(session => {
                    session.sendToolResponse({ functionResponses: responses });
                });
             }

             // 3. Handle Audio Output
             const audioData = message.serverContent?.modelTurn?.parts?.[0]?.inlineData?.data;
             if (audioData && audioContextRef.current) {
                 const ctx = audioContextRef.current;
                 nextStartTimeRef.current = Math.max(nextStartTimeRef.current, ctx.currentTime);
                 
                 const audioBuffer = await decodeAudioData(
                    decodeAtob(audioData),
                    ctx,
                    24000,
                    1
                 );
                 
                 const source = ctx.createBufferSource();
                 source.buffer = audioBuffer;
                 source.connect(ctx.destination);
                 source.addEventListener('ended', () => {
                     sourcesRef.current.delete(source);
                 });
                 source.start(nextStartTimeRef.current);
                 nextStartTimeRef.current += audioBuffer.duration;
                 sourcesRef.current.add(source);
             }
          },
          onclose: () => {
             setConnected(false);
             addLog(MessageSource.SYSTEM, "Uplink Closed.");
          },
          onerror: (err) => {
             console.error(err);
             addLog(MessageSource.SYSTEM, "Error: " + err.message);
          }
        }
      });
      sessionRef.current = sessionPromise;

    } catch (err: any) {
      addLog(MessageSource.SYSTEM, `Connection Failed: ${err.message}`);
      setConnected(false);
    }
  };

  const disconnect = () => {
    if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
    }
    if (processorRef.current && inputContextRef.current) {
        processorRef.current.disconnect();
        inputContextRef.current.close();
    }
    if (audioContextRef.current) {
        audioContextRef.current.close();
    }
    sourcesRef.current.forEach(source => source.stop());
    sourcesRef.current.clear();
    setConnected(false);
    
    // Also abort any pending backend request
    if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
    }

    addLog(MessageSource.SYSTEM, "Disconnected by user.");
  };

  return {
    connected,
    connect,
    disconnect,
    volume,
    logs,
    activeTool
  };
};

function decodeAtob(base64: string) {
    const binaryString = atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes;
}
