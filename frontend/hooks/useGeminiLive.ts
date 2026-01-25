
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
  const [micMuted, setMicMuted] = useState(false);
  const micMutedRef = useRef(false); // Ref for use in audio callback

  const audioContextRef = useRef<AudioContext | null>(null);
  const inputContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const nextStartTimeRef = useRef<number>(0);
  const sessionRef = useRef<Promise<any> | null>(null); 
  const sourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
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

  const sendCommand = useCallback((text: string) => {
    if (!sessionRef.current) {
        addLog(MessageSource.SYSTEM, "Cannot send command: Uplink not active.");
        return;
    }
    
    addLog(MessageSource.USER, text, { method: "UI_INJECTION" });
    
    sessionRef.current.then(session => {
        try {
            // Using 'true' for endOfTurn to prompt immediate response
            session.send({ parts: [{ text }] }, true);
        } catch (e: any) {
            addLog(MessageSource.SYSTEM, `Failed to send command: ${e.message}`);
        }
    }).catch(e => {
        addLog(MessageSource.SYSTEM, `Session Error: ${e.message}`);
    });
  }, [addLog]);

  const handleToolCall = async (functionCalls: any[]) => {
    const responses = [];
    
    for (const call of functionCalls) {
        if (call.name === 'stop_execution') {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
                abortControllerRef.current = null;
                responses.push({ id: call.id, name: call.name, response: { result: "Stopped." } });
            }
            continue;
        }

        if (call.name === 'delegate_task') {
            const task = call.args.task_description;
            addLog(MessageSource.SYSTEM, `Handing off to Core...`, { task });
            setActiveTool({ name: "Gemini 3 Pro", startTime: Date.now() });

            const controller = new AbortController();
            abortControllerRef.current = controller;

            try {
                // Use 'deep' complexity for robust reasoning
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: task, complexity: 'deep' }), 
                    signal: controller.signal
                });

                const reader = response.body?.getReader();
                const decoder = new TextDecoder();
                let done = false;
                let finalSummary = "";

                if (reader) {
                    while (!done) {
                        const { value, done: doneReading } = await reader.read();
                        done = doneReading;
                        const chunkValue = decoder.decode(value, { stream: !done });
                        const lines = chunkValue.split('\n');

                        for (const line of lines) {
                            if (!line.trim()) continue;
                            try {
                                const data = JSON.parse(line);
                                if (data.type === 'llm_thought') {
                                    addLog(MessageSource.AGENT, `(Thinking) ${data.content}`);
                                } else if (data.type === 'tool_call_batch') {
                                    data.calls.forEach((c: any) => addLog(MessageSource.TOOL, `Core Executing: ${c.name}`, c.args));
                                } else if (data.type === 'response') {
                                    finalSummary = data.content;
                                    addLog(MessageSource.AGENT, `Core Result: ${data.content}`);
                                }
                            } catch (e) {}
                        }
                    }
                }

                responses.push({
                    id: call.id,
                    name: call.name,
                    response: { result: finalSummary || "Task completed." }
                });

            } catch (err: any) {
                addLog(MessageSource.SYSTEM, `Core Error: ${err.message}`);
                responses.push({
                    id: call.id,
                    name: call.name,
                    response: { result: `Error: ${err.message}` }
                });
            } finally {
                setActiveTool(null);
                abortControllerRef.current = null;
            }
        }
    }
    return responses;
  };

  const connect = async () => {
    try {
      addLog(MessageSource.SYSTEM, "Initializing Gemini Live Uplink...");
      const apiKey = process.env.API_KEY;
      if (!apiKey) throw new Error("API_KEY missing");

      const ai = new GoogleGenAI({ apiKey });
      inputContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

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
            addLog(MessageSource.SYSTEM, "Uplink Established.");
            
            if (!inputContextRef.current) return;
            const source = inputContextRef.current.createMediaStreamSource(stream);
            const processor = inputContextRef.current.createScriptProcessor(4096, 1, 1);
            
            processor.onaudioprocess = (e) => {
              const inputData = e.inputBuffer.getChannelData(0);
              // Calc Volume
              let sum = 0;
              for (let i = 0; i < inputData.length; i++) sum += inputData[i] * inputData[i];
              const currentVolume = Math.sqrt(sum / inputData.length);
              setVolume(micMutedRef.current ? 0 : currentVolume);

              // Only send audio if mic is not muted
              if (!micMutedRef.current) {
                const pcmBlob = createPcmBlob(inputData);
                sessionPromise.then(session => session.sendRealtimeInput({ media: pcmBlob }));
              }
            };

            source.connect(processor);
            processor.connect(inputContextRef.current.destination);
            sourceRef.current = source;
            processorRef.current = processor;
          },
          onmessage: async (message: LiveServerMessage) => {
             if (message.serverContent?.interrupted) {
                 addLog(MessageSource.SYSTEM, "🛑 Interrupted");
                 sourcesRef.current.forEach(s => s.stop());
                 sourcesRef.current.clear();
                 return;
             }
             if (message.toolCall?.functionCalls) {
                const responses = await handleToolCall(message.toolCall.functionCalls);
                sessionPromise.then(s => s.sendToolResponse({ functionResponses: responses }));
             }
             const audioData = message.serverContent?.modelTurn?.parts?.[0]?.inlineData?.data;
             if (audioData && audioContextRef.current) {
                 const ctx = audioContextRef.current;
                 nextStartTimeRef.current = Math.max(nextStartTimeRef.current, ctx.currentTime);
                 const audioBuffer = await decodeAudioData(decodeAtob(audioData), ctx, 24000, 1);
                 const source = ctx.createBufferSource();
                 source.buffer = audioBuffer;
                 source.connect(ctx.destination);
                 source.addEventListener('ended', () => sourcesRef.current.delete(source));
                 source.start(nextStartTimeRef.current);
                 nextStartTimeRef.current += audioBuffer.duration;
                 sourcesRef.current.add(source);
             }
          },
          onclose: () => { setConnected(false); addLog(MessageSource.SYSTEM, "Uplink Closed."); },
          onerror: (err) => { console.error(err); addLog(MessageSource.SYSTEM, "Error: " + err.message); }
        }
      });
      sessionRef.current = sessionPromise;

    } catch (err: any) {
      addLog(MessageSource.SYSTEM, `Connection Failed: ${err.message}`);
      setConnected(false);
    }
  };

  const disconnect = () => {
    streamRef.current?.getTracks().forEach(t => t.stop());
    processorRef.current?.disconnect();
    inputContextRef.current?.close();
    audioContextRef.current?.close();
    sourcesRef.current.forEach(s => s.stop());
    sourcesRef.current.clear();
    setConnected(false);
    if (abortControllerRef.current) abortControllerRef.current.abort();
    addLog(MessageSource.SYSTEM, "Disconnected.");
  };

  const toggleMicMute = useCallback(() => {
    setMicMuted(prev => {
      const newVal = !prev;
      micMutedRef.current = newVal;
      return newVal;
    });
  }, []);

  return { connected, connect, disconnect, sendCommand, volume, logs, activeTool, micMuted, toggleMicMute };
};

function decodeAtob(base64: string) {
    const binaryString = atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) bytes[i] = binaryString.charCodeAt(i);
    return bytes;
}
