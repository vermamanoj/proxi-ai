
import { useState, useEffect, useRef, useCallback } from 'react';
import { GoogleGenAI, LiveServerMessage, Modality } from '@google/genai';
import { LogEntry, MessageSource, ActiveToolState } from '../types';
import { API_BASE, SYSTEM_INSTRUCTION_RELAY, SYSTEM_INSTRUCTION_CHAT, TOOLS } from '../constants';
import { blobToBase64, createPcmBlob, decodeAudioData, encodePcm } from '../utils/audio';
import { createSession, updateSession, closeSession as closeSessionApi } from '../services/sessionService';

// Status messages that should NOT appear in chat (shown in compact indicator instead)
const STATUS_MESSAGES = [
  'Initializing Gemini Live Uplink...',
  'Uplink Established. Listening in 2s...',
  '🎤 Listening...',
  'Uplink Closed.',
  'Disconnected.',
  'New session started.',
  'Session restored.',
  'Connection Failed:',
  '🔴 Interrupted'
];

const isStatusMessage = (text: string): boolean => {
  return STATUS_MESSAGES.some(msg => text.startsWith(msg));
};

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'listening' | 'error';

export const useGeminiLive = (backendEnabled: boolean = true, audioOutputEnabled: boolean = true, complexity: 'fast' | 'deep' = 'fast') => {
  const [connected, setConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
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
  
  // Initialize logs from localStorage - but clear if stale (> 1 hour old)
  const [logs, setLogs] = useState<LogEntry[]>(() => {
    try {
      const saved = localStorage.getItem('proxi_session_logs');
      const savedAt = localStorage.getItem('proxi_session_timestamp');
      if (saved && savedAt) {
        const age = Date.now() - parseInt(savedAt);
        // Clear stale sessions (> 1 hour)
        if (age > 60 * 60 * 1000) {
          localStorage.removeItem('proxi_session_logs');
          localStorage.removeItem('proxi_session_timestamp');
          return [];
        }
        const parsed = JSON.parse(saved);
        return parsed.map((log: any) => ({ ...log, timestamp: new Date(log.timestamp) }));
      }
    } catch (e) { console.warn('Failed to restore session logs:', e); }
    return [];
  });
  const [volume, setVolume] = useState(0);
  
  // Persist logs to localStorage with timestamp
  useEffect(() => {
    try {
      localStorage.setItem('proxi_session_logs', JSON.stringify(logs));
      localStorage.setItem('proxi_session_timestamp', Date.now().toString());
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
  const taskInProgressRef = useRef<boolean>(false); // Prevent overlapping delegate_task calls

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
            
            // Prevent overlapping requests - if a task is already running, queue this one
            if (taskInProgressRef.current) {
                addLog(MessageSource.SYSTEM, `⏳ Task already in progress. Please wait...`);
                responses.push({ id: call.id, name: call.name, response: { result: "A task is already running. Please wait for it to complete." } });
                continue;
            }
            
            taskInProgressRef.current = true;
            addLog(MessageSource.SYSTEM, `Handing off to Core...`, { task });
            setActiveTool({ name: "Gemini 3 Pro", startTime: Date.now() });

            const controller = new AbortController();
            abortControllerRef.current = controller;

            try {
                // Session management: keep session for 10 minutes for multi-step tasks
                // ONLY expire session on timeout - do NOT reset based on message length
                const SESSION_TTL_MS = 10 * 60 * 1000; // 10 minutes for complex tasks
                const now = Date.now();
                const sessionExpired = !backendSessionRef.current || 
                    (now - backendSessionTimestampRef.current > SESSION_TTL_MS);
                
                if (sessionExpired) {
                    backendSessionRef.current = `session_${now}`;
                }
                // Always update timestamp to keep session alive during active use
                backendSessionTimestampRef.current = now;
                
                // Use complexity from UI setting
                const response = await fetch(`${API_BASE}/api/chat`, {
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
                                } else if (data.type === 'response' || data.type === 'final_response') {
                                    finalSummary = data.content;
                                    addLog(MessageSource.AGENT, `Core Result: ${data.content}`);
                                } else if (data.type === 'plan') {
                                    // Mission plan with goals
                                    addLog(MessageSource.SYSTEM, `📋 Mission Plan`, { plan: data.goals });
                                } else if (data.type === 'goal_update') {
                                    // Goal status update
                                    const statusEmoji = data.status === 'complete' ? '✅' : data.status === 'active' ? '🔄' : data.status === 'failed' ? '❌' : '⏳';
                                    addLog(MessageSource.SYSTEM, `${statusEmoji} ${data.goal_id}: ${data.status}${data.result ? ' - ' + data.result : ''}`, { goalUpdate: data });
                                } else if (data.type === 'approval_required') {
                                    // Command needs user approval
                                    addLog(MessageSource.SYSTEM, `🛡️ Approval Required: ${data.reason}`, { 
                                        approvalRequired: true, 
                                        command: data.command, 
                                        reason: data.reason,
                                        riskLevel: data.risk_level || 'moderate'
                                    });
                                } else if (data.type === 'escalation') {
                                    // Mission escalated to human
                                    addLog(MessageSource.SYSTEM, `🚨 Escalated to Human: ${data.reason}`, {
                                        escalation: true,
                                        missionId: data.mission_id,
                                        reason: data.reason
                                    });
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

                // Truncate response for voice output - Gemini can only speak ~500 chars well
                const voiceResult = finalSummary 
                    ? (finalSummary.length > 500 ? finalSummary.substring(0, 500) + "... Task completed. Check chat for full details." : finalSummary)
                    : "Task completed successfully.";
                responses.push({
                    id: call.id,
                    name: call.name,
                    response: { result: voiceResult }
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
                taskInProgressRef.current = false; // Allow new tasks
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
    console.log('[LIVE] 🎤 Starting voice connection...');
    
    try {
      setConnectionStatus('connecting');
      
      // Check if running in Capacitor (mobile app)
      const isCapacitor = typeof (window as any)?.Capacitor !== 'undefined';
      
      // Vite exposes env vars via import.meta.env with VITE_ prefix
      const apiKey = (import.meta as any).env?.VITE_GEMINI_API_KEY;
      console.log('[LIVE] API Key present:', !!apiKey, 'isCapacitor:', isCapacitor);
      
      if (!apiKey) {
        if (isCapacitor) {
          // Mobile app - voice mode not supported (API key can't be bundled for security)
          addLog(MessageSource.SYSTEM, '⚠️ Voice mode is not available on mobile. Use text chat instead.');
        } else {
          // Desktop - missing .env configuration
          addLog(MessageSource.SYSTEM, '⚠️ Voice mode requires VITE_GEMINI_API_KEY in frontend/.env');
        }
        setConnectionStatus('error');
        connectingRef.current = false;
        return;
      }

      console.log('[LIVE] Creating GoogleGenAI client...');
      const ai = new GoogleGenAI({ apiKey });
      console.log('[LIVE] Creating AudioContexts (input@16kHz, output@24kHz)...');
      inputContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
      
      // Create gain node for audio output control
      gainNodeRef.current = audioContextRef.current.createGain();
      gainNodeRef.current.gain.value = audioOutputEnabledRef.current ? 1 : 0;
      gainNodeRef.current.connect(audioContextRef.current.destination);
      
      console.log('[LIVE] Requesting microphone access...');
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log('[LIVE] ✓ Microphone access granted, tracks:', stream.getAudioTracks().length);
      streamRef.current = stream;

      // Use different config based on backend mode
      const systemInstruction = backendEnabledRef.current ? SYSTEM_INSTRUCTION_RELAY : SYSTEM_INSTRUCTION_CHAT;
      const tools = backendEnabledRef.current ? [{ functionDeclarations: TOOLS }] : undefined;
      
      console.log('[LIVE] Connecting to Gemini Live API (model: gemini-2.5-flash-native-audio-preview)...');
      const sessionPromise = ai.live.connect({
        model: 'gemini-2.5-flash-native-audio-preview-12-2025',
        config: {
          responseModalities: [Modality.AUDIO],
          systemInstruction,
          tools,
        },
        callbacks: {
          onopen: () => {
            console.log('[LIVE] ✓ WebSocket OPEN - Connected to Gemini Live!');
            setConnected(true);
            setConnectionStatus('connected');
            // Start muted for 2 seconds to let user compose thoughts
            setMicMuted(true);
            micMutedRef.current = true;
            
            // Auto-unmute after delay
            setTimeout(() => {
              if (connectedRef.current) {
                setMicMuted(false);
                micMutedRef.current = false;
                setConnectionStatus('listening');
              }
            }, 2000);
            
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
          onclose: () => { 
            console.log('[LIVE] WebSocket CLOSED');
            setConnected(false); 
            setConnectionStatus('disconnected'); 
          },
          onerror: (err) => { 
            console.error('[LIVE] ❌ WebSocket ERROR:', err);
            setConnectionStatus('error'); 
          }
        }
      });
      sessionRef.current = sessionPromise;
      console.log('[LIVE] Session promise created, awaiting connection...');

    } catch (err: any) {
      console.error('[LIVE] ❌ Connection FAILED:', err.message || err);
      setConnectionStatus('error');
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
    setConnectionStatus('disconnected');
    connectingRef.current = false;
    sessionRef.current = null;
    if (abortControllerRef.current) abortControllerRef.current.abort();
  };

  const toggleMicMute = useCallback(() => {
    setMicMuted(prev => {
      const newVal = !prev;
      micMutedRef.current = newVal;
      return newVal;
    });
  }, []);

  // Load a saved session's messages into current view
  const loadSession = useCallback((messages: any[]) => {
    const restoredLogs: LogEntry[] = messages.map(msg => ({
      id: msg.id || Math.random().toString(36).substring(7),
      timestamp: new Date(msg.timestamp),
      source: msg.source as MessageSource,
      text: msg.text,
      metadata: msg.metadata
    }));
    setLogs(restoredLogs);
    backendSessionRef.current = null; // Don't overwrite the loaded session
  }, [addLog]);

  // Save current session and start fresh
  const clearSession = useCallback(async () => {
    // Save current session if it has content
    if (backendSessionRef.current && logs.length > 1) {
      const sessionId = backendSessionRef.current;
      // Generate title from first user message
      const firstUserMsg = logs.find(l => l.source === MessageSource.USER);
      const title = firstUserMsg?.text?.substring(0, 50) || "Session";
      
      // Save session to backend
      try {
        await createSession(sessionId, title);
        await updateSession(sessionId, {
          messages: logs.map(l => ({
            id: l.id,
            timestamp: l.timestamp.toISOString(),
            source: l.source,
            text: l.text,
            metadata: l.metadata
          }))
        } as any);
        await closeSessionApi(sessionId);
      } catch (e) {
        console.warn('[Session] Failed to save session:', e);
      }
    }
    
    // Clear and start fresh
    setLogs([]);
    backendSessionRef.current = null;
    backendSessionTimestampRef.current = 0;
    taskInProgressRef.current = false;
  }, [addLog, logs]);

  // Filter out status messages from logs for chat display
  const chatLogs = logs.filter(log => !isStatusMessage(log.text));

  // Function to mark ALL remaining goals as failed (when user denies approval)
  const markActiveGoalFailed = useCallback((reason: string = 'User denied') => {
    // Find the most recent plan from logs
    for (let i = logs.length - 1; i >= 0; i--) {
      const log = logs[i];
      if (log.metadata?.plan) {
        // Mark ALL pending/active goals as cancelled
        const pendingGoals = log.metadata.plan.filter(
          (goal: any) => goal.status === 'active' || goal.status === 'pending'
        );
        for (const goal of pendingGoals) {
          addLog(MessageSource.SYSTEM, `❌ ${goal.id}: cancelled - ${reason}`, { 
            goalUpdate: { goal_id: String(goal.id), status: 'failed', result: reason }
          });
        }
        return;
      }
    }
  }, [logs, addLog]);

  // Auto-save session periodically (every 30 seconds if there's content)
  useEffect(() => {
    if (!backendSessionRef.current || logs.length < 2) return;
    
    const saveInterval = setInterval(async () => {
      if (backendSessionRef.current && logs.length > 1) {
        const sessionId = backendSessionRef.current;
        const firstUserMsg = logs.find(l => l.source === MessageSource.USER);
        const title = firstUserMsg?.text?.substring(0, 50) || "Session";
        try {
          await createSession(sessionId, title);
          await updateSession(sessionId, {
            messages: logs.map(l => ({
              id: l.id,
              timestamp: l.timestamp.toISOString(),
              source: l.source,
              text: l.text,
              metadata: l.metadata
            }))
          } as any);
        } catch (e) {
          // Silent fail for auto-save
        }
      }
    }, 30000);
    
    return () => clearInterval(saveInterval);
  }, [logs]);
  
  return { connected, connectionStatus, connect, disconnect, sendCommand, volume, logs, chatLogs, activeTool, micMuted, toggleMicMute, clearSession, loadSession, markActiveGoalFailed };
};

function decodeAtob(base64: string) {
    const binaryString = atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) bytes[i] = binaryString.charCodeAt(i);
    return bytes;
}
