
import { useState, useEffect, useRef, useCallback } from 'react';
import { GoogleGenAI, LiveServerMessage, Modality } from '@google/genai';
import { LogEntry, MessageSource, ActiveToolState } from '../types';
import { SYSTEM_INSTRUCTION_RELAY, SYSTEM_INSTRUCTION_CHAT, TOOLS } from '../constants';
import { blobToBase64, createPcmBlob, decodeAudioData, encodePcm } from '../utils/audio';

export const useGeminiLive = (backendEnabled: boolean = true, audioOutputEnabled: boolean = true, complexity: 'fast' | 'deep' = 'fast') => {
  const [connected, setConnected] = useState(false);
  const connectedRef = useRef(false); // Ref for use in audio callback
  const backendEnabledRef = useRef(backendEnabled);
  const audioOutputEnabledRef = useRef(audioOutputEnabled);
  const complexityRef = useRef(complexity); // Track complexity for delegate_task
  
  // Keep refs in sync with state/props
  useEffect(() => {
    connectedRef.current = connected;
  }, [connected]);
  
  useEffect(() => {
    backendEnabledRef.current = backendEnabled;
  }, [backendEnabled]);
  
  useEffect(() => {
    complexityRef.current = complexity;
  }, [complexity]);
  
  useEffect(() => {
    audioOutputEnabledRef.current = audioOutputEnabled;
    // Update gain node if it exists
    if (gainNodeRef.current) {
      gainNodeRef.current.gain.value = audioOutputEnabled ? 1 : 0;
    }
  }, [audioOutputEnabled]);
  
  // Initialize logs from localStorage
  const [logs, setLogs] = useState<LogEntry[]>(() => {
    try {
      const saved = localStorage.getItem('proxi_session_logs');
      if (saved) {
        const parsed = JSON.parse(saved);
        // Restore Date objects
        return parsed.map((log: any) => ({ ...log, timestamp: new Date(log.timestamp) }));
      }
    } catch (e) { console.warn('Failed to restore session logs:', e); }
    return [];
  });
  const [volume, setVolume] = useState(0);
  
  // Persist logs to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('proxi_session_logs', JSON.stringify(logs));
    } catch (e) { console.warn('Failed to save session logs:', e); }
  }, [logs]);
  const [activeTool, setActiveTool] = useState<ActiveToolState | null>(null);
  const [micMuted, setMicMuted] = useState(false);
  const micMutedRef = useRef(false); // Ref for use in audio callback
  const gainNodeRef = useRef<GainNode | null>(null); // For audio output muting

  const audioContextRef = useRef<AudioContext | null>(null);
  const inputContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const connectingRef = useRef(false); // Guard against multiple connect calls
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const nextStartTimeRef = useRef<number>(0);
  const sessionRef = useRef<Promise<any> | null>(null); 
  const sourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
  const abortControllerRef = useRef<AbortController | null>(null);
  const backendSessionRef = useRef<string | null>(null); // Track backend session for delegate_task
  const backendSessionTimestampRef = useRef<number>(0); // Session expiry tracking

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
            // sendClientContent is the correct method for Gemini Live API
            session.sendClientContent({ turns: [{ role: 'user', parts: [{ text }] }], turnComplete: true });
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
                // Session management: keep session for 5 minutes for follow-ups like "yes"
                const SESSION_TTL_MS = 5 * 60 * 1000;
                const now = Date.now();
                const sessionExpired = !backendSessionRef.current || 
                    (now - backendSessionTimestampRef.current > SESSION_TTL_MS);
                const isNewTopic = task.length > 50; // Long messages = new topic
                
                if (sessionExpired || isNewTopic) {
                    backendSessionRef.current = `session_${now}`;
                    backendSessionTimestampRef.current = now;
                }
                
                // Use complexity from UI setting
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        message: task, 
                        complexity: complexityRef.current,
                        session_id: backendSessionRef.current 
                    }), 
                    signal: controller.signal
                });

                // Handle non-OK responses
                if (!response.ok) {
                    const errorMsg = response.status === 0 
                        ? "Backend is offline. Please start the backend server."
                        : `Backend error: ${response.status} ${response.statusText}`;
                    addLog(MessageSource.SYSTEM, `⚠️ ${errorMsg}`);
                    responses.push({
                        id: call.id,
                        name: call.name,
                        response: { result: errorMsg }
                    });
                    continue;
                }

                const reader = response.body?.getReader();
                const decoder = new TextDecoder();
                let done = false;
                let finalSummary = "";
                let buffer = "";  // Buffer for incomplete JSON lines

                if (reader) {
                    while (!done) {
                        const { value, done: doneReading } = await reader.read();
                        done = doneReading;
                        buffer += decoder.decode(value, { stream: !done });
                        
                        // Process complete lines (ending with newline)
                        const lines = buffer.split('\n');
                        // Keep the last incomplete fragment in buffer
                        buffer = lines.pop() || '';

                        for (const line of lines) {
                            if (!line.trim()) continue;
                            try {
                                const data = JSON.parse(line);
                                if (data.type === 'llm_thought') {
                                    addLog(MessageSource.AGENT, `(Thinking) ${data.content}`);
                                } else if (data.type === 'tool_call_batch') {
                                    data.calls.forEach((c: any) => addLog(MessageSource.TOOL, `Core Executing: ${c.name}`, c.args));
                                } else if (data.type === 'tool_result') {
                                    // Mark tool as completed with result
                                    addLog(MessageSource.TOOL, `✓ ${data.name}`, { result: data.content, completed: true });
                                } else if (data.type === 'status_change' && data.metadata?.screenshot) {
                                    // Handle screenshot - add to logs with metadata for display
                                    addLog(MessageSource.AGENT, data.content || 'Screenshot', { screenshot: data.metadata.screenshot });
                                } else if (data.type === 'response') {
                                    finalSummary = data.content;
                                    addLog(MessageSource.AGENT, `Core Result: ${data.content}`);
                                }
                            } catch (e) {
                                console.warn('[LIVE] Failed to parse line:', line.substring(0, 100));
                            }
                        }
                    }
                    
                    // Process any remaining data in buffer
                    if (buffer.trim()) {
                        try {
                            const data = JSON.parse(buffer);
                            if (data.type === 'status_change' && data.metadata?.screenshot) {
                                addLog(MessageSource.AGENT, data.content || 'Screenshot', { screenshot: data.metadata.screenshot });
                            } else if (data.type === 'response') {
                                finalSummary = data.content;
                                addLog(MessageSource.AGENT, `Core Result: ${data.content}`);
                            }
                        } catch (e) {}
                    }
                }

                responses.push({
                    id: call.id,
                    name: call.name,
                    response: { result: finalSummary || "Task completed." }
                });

            } catch (err: any) {
                const isNetworkError = err.name === 'TypeError' || err.message?.includes('fetch');
                const isAborted = err.name === 'AbortError';
                const errorMsg = isAborted 
                    ? "Task cancelled by user."
                    : isNetworkError 
                    ? "⚠️ Cannot reach backend. Is the server running?"
                    : `Core Error: ${err.message}`;
                addLog(MessageSource.SYSTEM, errorMsg);
                responses.push({
                    id: call.id,
                    name: call.name,
                    response: { result: errorMsg }
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
    // Prevent multiple simultaneous connections
    if (connectingRef.current || sessionRef.current) {
      console.debug('[LIVE] Connection already in progress or established, skipping');
      return;
    }
    connectingRef.current = true;
    
    try {
      addLog(MessageSource.SYSTEM, "Initializing Gemini Live Uplink...");
      const apiKey = process.env.API_KEY;
      if (!apiKey) throw new Error("API_KEY missing");

      const ai = new GoogleGenAI({ apiKey });
      inputContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
      
      // Create gain node for audio output control
      gainNodeRef.current = audioContextRef.current.createGain();
      gainNodeRef.current.gain.value = audioOutputEnabledRef.current ? 1 : 0;
      gainNodeRef.current.connect(audioContextRef.current.destination);
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Use different config based on backend mode
      const systemInstruction = backendEnabledRef.current ? SYSTEM_INSTRUCTION_RELAY : SYSTEM_INSTRUCTION_CHAT;
      const tools = backendEnabledRef.current ? [{ functionDeclarations: TOOLS }] : undefined;
      
      const sessionPromise = ai.live.connect({
        model: 'gemini-2.5-flash-native-audio-preview-12-2025',
        config: {
          responseModalities: [Modality.AUDIO],
          systemInstruction,
          tools,
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

              // Only send audio if mic is not muted and connection is active
              if (!micMutedRef.current && connectedRef.current) {
                const pcmBlob = createPcmBlob(inputData);
                sessionPromise.then(session => {
                  try {
                    session.sendRealtimeInput({ media: pcmBlob });
                  } catch (e) {
                    // Ignore errors when WebSocket is closing
                  }
                }).catch(() => {});
              }
            };

            source.connect(processor);
            processor.connect(inputContextRef.current.destination);
            sourceRef.current = source;
            processorRef.current = processor;
          },
          onmessage: async (message: LiveServerMessage) => {
             const msg = message as any;
             
             // Debug: log message type
             const hasAudio = !!msg.serverContent?.modelTurn?.parts?.[0]?.inlineData?.data;
             const hasText = !!msg.serverContent?.modelTurn?.parts?.find((p: any) => p.text);
             const hasTranscript = !!msg.serverContent?.inputTranscript || !!msg.serverContent?.turnComplete;
             if (!hasAudio) {
               console.debug('[LIVE]', { 
                 interrupted: msg.serverContent?.interrupted,
                 inputTranscript: msg.serverContent?.inputTranscript,
                 turnComplete: msg.serverContent?.turnComplete,
                 hasText,
                 toolCall: !!msg.toolCall
               });
             }
             
             if (msg.serverContent?.interrupted) {
                 addLog(MessageSource.SYSTEM, "🛑 Interrupted");
                 sourcesRef.current.forEach(s => s.stop());
                 sourcesRef.current.clear();
                 return;
             }
             
             // Capture user's transcribed speech - try multiple field locations
             const userTranscript = msg.serverContent?.inputTranscript 
                 || msg.serverContent?.groundingMetadata?.retrievalQueries?.[0]
                 || msg.inputTranscript;
             if (userTranscript && typeof userTranscript === 'string' && userTranscript.trim()) {
                 console.debug('[LIVE] User said:', userTranscript);
                 addLog(MessageSource.USER, userTranscript.trim());
             }
             
             // Capture model's text response (filter out thinking patterns for clean display)
             const modelText = msg.serverContent?.modelTurn?.parts?.find((p: any) => p.text)?.text;
             if (modelText) {
                 // Don't log internal thinking patterns starting with ** in chat mode
                 const isThinkingPattern = modelText.trim().startsWith('**') && modelText.includes('**');
                 if (!backendEnabledRef.current && isThinkingPattern) {
                     console.debug('[LIVE] Filtered thinking:', modelText.substring(0, 50));
                 } else {
                     addLog(MessageSource.AGENT, modelText);
                 }
             }
             
             if (message.toolCall?.functionCalls) {
                const responses = await handleToolCall(message.toolCall.functionCalls);
                sessionPromise.then(s => s.sendToolResponse({ functionResponses: responses }));
             }
             const audioData = message.serverContent?.modelTurn?.parts?.[0]?.inlineData?.data;
             if (audioData && audioContextRef.current && gainNodeRef.current) {
                 const ctx = audioContextRef.current;
                 nextStartTimeRef.current = Math.max(nextStartTimeRef.current, ctx.currentTime);
                 const audioBuffer = await decodeAudioData(decodeAtob(audioData), ctx, 24000, 1);
                 const source = ctx.createBufferSource();
                 source.buffer = audioBuffer;
                 source.connect(gainNodeRef.current); // Connect through gain node for mute control
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
      connectingRef.current = false;
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
    connectingRef.current = false;
    sessionRef.current = null;
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
