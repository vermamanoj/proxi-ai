
import { useState, useCallback, useEffect, useRef } from 'react';
import { LogEntry, MessageSource, Complexity, AgentStatus, PendingAction, TraceStep, MissionState } from '../types';

export const useProxiBrain = (audioEnabled: boolean = true) => {
  const [status, setStatus] = useState<AgentStatus>('idle');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [lastTrace, setLastTrace] = useState<TraceStep[]>([]);
  const [complexity, setComplexity] = useState<Complexity>('fast');
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionTimestamp, setSessionTimestamp] = useState<number>(0); // Track when session was created
  const [awaitingApproval, setAwaitingApproval] = useState(false); // Track if we're waiting for user approval
  const [isSpeaking, setIsSpeaking] = useState(false); // Track if TTS is active
  const voicesRef = useRef<SpeechSynthesisVoice[]>([]);

  // Mission State Tracking
  const [missionState, setMissionState] = useState<MissionState>({
    active: false,
    phase: 'idle',
    goal: '',
    verification: { status: 'pending' },
    retryCount: 0
  });

  useEffect(() => {
    const loadVoices = () => {
      voicesRef.current = window.speechSynthesis.getVoices();
    };
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
    loadVoices();
  }, []);

  const addLog = useCallback((source: MessageSource, text: string, metadata?: any) => {
    setLogs(prev => [...prev, {
      id: Math.random().toString(36).substring(7),
      timestamp: new Date(),
      source,
      text,
      metadata
    }]);
  }, []);

  const updateTrace = (step: TraceStep) => {
      setLastTrace(prev => [...prev, step]);
  };

  const cleanTextForSpeech = (text: string) => {
      return text.replace(/[*#_`]/g, '')
                 .replace(/\[.*?\]/g, '')
                 .replace(/\(https?:\/\/.*?\)/g, '');
  };

  const stopSpeaking = useCallback(() => {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, []);

  // Stop speech when audio is disabled
  useEffect(() => {
    if (!audioEnabled) {
      stopSpeaking();
    }
  }, [audioEnabled, stopSpeaking]);

  const speak = useCallback((text: string) => {
    // Skip TTS if audio is disabled
    if (!audioEnabled || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    
    const cleanText = cleanTextForSpeech(text);
    const utterance = new SpeechSynthesisUtterance(cleanText);
    const preferredVoices = voicesRef.current;
    const techVoice = preferredVoices.find(v => v.name.includes('Google US English')) 
                   || preferredVoices.find(v => v.name.includes('Zira')) 
                   || preferredVoices[0];
    if (techVoice) utterance.voice = techVoice;
    utterance.rate = 1.05; 
    utterance.pitch = 0.95; 
    utterance.onstart = () => {
      setStatus('speaking');
      setIsSpeaking(true);
    };
    utterance.onend = () => {
      setIsSpeaking(false);
      if (pendingAction) setStatus('awaiting_confirmation');
      else setStatus('idle');
    };
    utterance.onerror = () => {
      setIsSpeaking(false);
      setStatus('idle');
    };
    window.speechSynthesis.speak(utterance);
  }, [pendingAction, audioEnabled]);

  const sendCommand = async (message: string, isButtonApproval: boolean = false) => {
    if (!message.trim()) return;

    // SECURITY: Block audio/text approval for destructive actions - require button click
    const isApprovalWord = ['yes', 'no', 'proceed', 'cancel', 'approve', 'deny'].some(
      word => message.toLowerCase().trim() === word
    );
    
    if (pendingAction && isApprovalWord && !isButtonApproval) {
      addLog(MessageSource.SYSTEM, "⚠️ Security: Destructive actions require button approval. Please click Approve or Deny.");
      return;
    }

    addLog(MessageSource.USER, message);
    setStatus('processing');
    setPendingAction(null);
    
    // Session persistence: keep session for 10 minutes for multi-step tasks
    // ONLY expire on timeout - do NOT reset based on message length
    const SESSION_TTL_MS = 10 * 60 * 1000; // 10 minutes for complex tasks
    const now = Date.now();
    let currentSessionId = sessionId;
    
    // Check if session is still valid (exists and not expired)
    const sessionExpired = !currentSessionId || (now - sessionTimestamp > SESSION_TTL_MS);
    
    if (sessionExpired) {
      currentSessionId = `session_${Date.now()}`;
      setSessionId(currentSessionId);
      // Clear trace for new conversation (prevents stale data confusion)
      setLastTrace([]);
    }
    // Always update timestamp to keep session alive during active use
    setSessionTimestamp(now);
    setAwaitingApproval(false); // Reset at start of each request
    
    setMissionState({
        active: true,
        phase: 'planning',
        goal: lastTrace.length === 0 ? message : missionState.goal, // Keep original goal for follow-ups
        verification: { status: 'pending' },
        retryCount: 0
    });

    updateTrace({ step_type: 'user_input', content: message, metadata: { complexity } });

    // --- TIMEOUT SETUP ---
    const controller = new AbortController();
    let activityTimer: number | undefined;

    const resetActivityTimer = () => {
      if (activityTimer !== undefined) window.clearTimeout(activityTimer);
      activityTimer = window.setTimeout(() => {
          controller.abort();
          addLog(MessageSource.SYSTEM, "System Alert: Network Timeout. No data received for 60 seconds.");
          setStatus('idle');
          setMissionState(prev => ({ ...prev, phase: 'failed', active: false }));
      }, 60000); 
    };

    resetActivityTimer();

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, complexity, session_id: currentSessionId }),
        signal: controller.signal
      });
      
      if (!response.ok) {
          throw new Error(`Connection Failed (${response.status} ${response.statusText}). Check Backend.`);
      }

      if (!response.body) throw new Error("No response body received.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let buffer = '';
      
      // Force Flush Timer: If data sits in buffer for 1s, process it.
      let flushTimer: number | null = null;
      
      const processBuffer = (force = false) => {
         const lines = buffer.split('\n');
         // If forcing, take everything. If not, keep the last fragment.
         const pending = force ? '' : lines.pop() || '';
         
         for (const line of lines) {
            if (!line.trim()) continue;
            try {
                // Debug log to see raw stream in console
                const isScreenshot = line.includes('screenshot');
                console.log("[RAW STREAM]", isScreenshot ? `SCREENSHOT LINE (${line.length} chars)` : line.substring(0, 100));
                
                const data = JSON.parse(line);
                console.log("[PARSED]", data.type, data.phase || '', data.metadata?.screenshot ? 'HAS_SCREENSHOT' : '');
                
                // --- STATE UPDATES ---
                if (data.type === 'status_change') {
                    setMissionState(prev => ({
                        ...prev,
                        phase: data.phase,
                        activeTool: data.tool || undefined,
                        retryCount: data.retry ? prev.retryCount + 1 : prev.retryCount
                    }));
                    
                    // Handle screenshots - add to trace for display
                    if (data.metadata?.screenshot) {
                        console.log('[SCREENSHOT] Received screenshot data, length:', data.metadata.screenshot.length);
                        updateTrace({ 
                            step_type: 'status_change', 
                            content: data.content || 'Screenshot', 
                            metadata: { screenshot: data.metadata.screenshot }
                        });
                    }
                }
                else if (data.type === 'verification') {
                    setMissionState(prev => ({
                        ...prev,
                        verification: {
                            status: data.status,
                            reason: data.reason
                        }
                    }));
                }
                
                // --- STANDARD LOGGING ---
                switch (data.type) {
                    case 'llm_thought':
                        updateTrace({ step_type: 'llm_thought', content: data.content });
                        break;
                    case 'tool_call_batch':
                        for (const call of data.calls) {
                             updateTrace({ step_type: 'tool_call', content: call.name, metadata: { args: call.args } });
                             // Track Triple Handshake phases
                             if (call.name === 'assign_mission') {
                                 setMissionState(prev => ({ ...prev, active: true, phase: 'planning', goal: call.args?.goal || prev.goal }));
                             } else if (call.name === 'report_execution') {
                                 setMissionState(prev => ({ ...prev, phase: 'verifying' }));
                             }
                        }
                        break;
                    case 'tool_result':
                        updateTrace({ step_type: 'tool_result', content: data.name, metadata: { output: data.content } });
                        // Track verification results
                        if (data.name === 'assign_mission') {
                            setMissionState(prev => ({ ...prev, phase: 'executing' }));
                        } else if (data.content?.includes('VERIFICATION')) {
                            const passed = data.content.includes('PASSED') || data.content.includes('verified');
                            const failed = data.content.includes('FAILED');
                            setMissionState(prev => ({
                                ...prev,
                                phase: passed ? 'success' : failed ? 'failed' : prev.phase,
                                verification: { status: passed ? 'success' : failed ? 'failed' : 'pending' }
                            }));
                        }
                        break;
                    case 'response':
                        updateTrace({ step_type: 'final_response', content: data.content });
                        addLog(MessageSource.AGENT, data.content);
                        speak(data.content);
                        setMissionState(prev => ({ ...prev, active: false }));
                        
                        // Check if agent is asking for approval - if so, keep session alive and show approval UI
                        const responseText = (data.content || '').toLowerCase();
                        const isApprovalRequest = responseText.includes('should i proceed') || 
                                                  responseText.includes('should i kill') ||
                                                  responseText.includes('reply \'yes\'') ||
                                                  responseText.includes('approve or') ||
                                                  responseText.includes('confirm or cancel') ||
                                                  responseText.includes('requires approval') ||
                                                  responseText.includes('authorization required') ||
                                                  responseText.includes('approve this action') ||
                                                  responseText.includes('confirm to proceed');
                        setAwaitingApproval(isApprovalRequest);
                        
                        // Show approval card when agent asks for confirmation
                        if (isApprovalRequest) {
                            setPendingAction({
                                type: 'confirmation',
                                description: data.content,
                                data: { responseText: data.content }
                            });
                            setStatus('awaiting_confirmation');
                        }
                        break;
                    case 'error':
                        addLog(MessageSource.SYSTEM, `Error: ${data.content}`);
                        setMissionState(prev => ({ ...prev, phase: 'failed', active: false }));
                        break;
                }
            } catch (e) {
                console.warn("Failed to parse chunk, probably incomplete JSON:", line);
            }
         }
         buffer = pending;
      };

      while (!done) {
        resetActivityTimer();
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        const chunk = decoder.decode(value, { stream: !done });
        console.log('[CHUNK] Received chunk, size:', chunk.length);
        buffer += chunk;
        
        // Debug buffer state for screenshot
        if (buffer.includes('"phase":"screenshot"') || buffer.includes('"phase": "screenshot"')) {
          console.log('[BUFFER] SCREENSHOT DETECTED! buffer length:', buffer.length);
        }
        
        // Try to process immediately
        processBuffer();
        
        // If buffer still has data (incomplete line), set a force flush timer
        if (buffer.trim().length > 0) {
            if (flushTimer) clearTimeout(flushTimer);
            flushTimer = window.setTimeout(() => {
                console.log("[FORCE FLUSH] Buffer stalled, forcing parse.");
                processBuffer(true);
            }, 1000);
        }
      }

      // Cleanup
      if (activityTimer !== undefined) window.clearTimeout(activityTimer);
      if (flushTimer) clearTimeout(flushTimer);

      // Final flush
      if (buffer.trim()) {
         processBuffer(true);
      }

      setStatus('idle');

    } catch (err: any) {
      if (activityTimer !== undefined) window.clearTimeout(activityTimer);
      console.error(err);
      
      if (err.name === 'AbortError') {
         // Already logged by timer callback
      } else {
         addLog(MessageSource.SYSTEM, `System Alert: ${err.message}`);
         setStatus('idle');
         setMissionState(prev => ({ ...prev, phase: 'failed', active: false }));
      }
    }
  };

  const sendVisionCommand = async (file: File, message: string) => {
    addLog(MessageSource.USER, `[IMAGE] ${file.name}: ${message}`);
    setStatus('processing');
    
    // Update trace for this vision request
    updateTrace({ step_type: 'user_input', content: `[Image: ${file.name}] ${message}`, metadata: { hasImage: true } });

    const formData = new FormData();
    formData.append('file', file);
    formData.append('prompt', message);
    formData.append('complexity', complexity);

    try {
      // Use new streaming vision-action endpoint
      const response = await fetch('/api/vision-action', { method: 'POST', body: formData });
      if (!response.ok) throw new Error(`Vision Action Error: ${response.status}`);
      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let buffer = '';

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        buffer += decoder.decode(value, { stream: !done });
        
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            if (data.type === 'status_change') {
              if (data.metadata?.screenshot) {
                updateTrace({ step_type: 'status_change', content: data.content, metadata: data.metadata });
              }
            } else if (data.type === 'tool_call_batch') {
              data.calls.forEach((c: any) => updateTrace({ step_type: 'tool_call', content: `${c.name}(${JSON.stringify(c.args)})` }));
            } else if (data.type === 'tool_result') {
              updateTrace({ step_type: 'tool_result', content: data.content, metadata: { name: data.name } });
            } else if (data.type === 'response') {
              updateTrace({ step_type: 'final_response', content: data.content });
              addLog(MessageSource.AGENT, data.content);
            } else if (data.type === 'llm_thought') {
              updateTrace({ step_type: 'status_change', content: data.content, metadata: { phase: 'thinking' } });
            }
          } catch (e) {}
        }
      }
      
      setStatus('idle');
    } catch (err: any) {
      addLog(MessageSource.SYSTEM, `Error: ${err.message}`);
      setStatus('idle');
    }
  };

  const confirmAction = async () => {
    setPendingAction(null);
    // Send "yes" with button approval flag to bypass security check
    await sendCommand('yes', true);
  }; 
  const cancelAction = () => { 
    setPendingAction(null); 
    setStatus('idle');
    // Send "no" with button approval flag
    sendCommand('no', true);
  };
  const toggleComplexity = () => setComplexity(prev => prev === 'fast' ? 'deep' : 'fast');
  const logSystemError = (msg: string) => addLog(MessageSource.SYSTEM, msg);
  const clearSession = () => { setSessionId(null); setSessionTimestamp(0); setLastTrace([]); };



  return {
    status,
    logs,
    lastTrace,
    complexity,
    pendingAction,
    missionState,
    sessionId,
    isSpeaking,
    sendCommand,
    sendVisionCommand,
    toggleComplexity,
    confirmAction,
    cancelAction,
    logSystemError,
    clearSession
  };
};
