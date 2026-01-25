
import { useState, useCallback, useEffect, useRef } from 'react';
import { LogEntry, MessageSource, Complexity, AgentStatus, PendingAction, TraceStep, MissionState } from '../types';

export const useProxiBrain = () => {
  const [status, setStatus] = useState<AgentStatus>('idle');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [lastTrace, setLastTrace] = useState<TraceStep[]>([]);
  const [complexity, setComplexity] = useState<Complexity>('fast');
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [awaitingApproval, setAwaitingApproval] = useState(false); // Track if we're waiting for user approval
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

  const speak = useCallback((text: string) => {
    if (!window.speechSynthesis) return;
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
    utterance.onstart = () => setStatus('speaking');
    utterance.onend = () => {
      if (pendingAction) setStatus('awaiting_confirmation');
      else setStatus('idle');
    };
    utterance.onerror = () => setStatus('idle');
    window.speechSynthesis.speak(utterance);
  }, [pendingAction]);

  const sendCommand = async (message: string) => {
    if (!message.trim()) return;

    addLog(MessageSource.USER, message);
    setStatus('processing');
    setPendingAction(null);
    
    // Generate session ID if this is a new conversation
    // Only continue existing session if we're awaiting approval response
    let currentSessionId = sessionId;
    const isApprovalResponse = awaitingApproval && 
      ['yes', 'no', 'proceed', 'cancel', 'approve', 'deny'].some(
        word => message.toLowerCase().trim() === word || 
                message.toLowerCase().includes(word)
      );
    
    if (!currentSessionId || !isApprovalResponse) {
      currentSessionId = `session_${Date.now()}`;
      setSessionId(currentSessionId);
      // Add separator instead of clearing trace (keep history visible)
      if (lastTrace.length > 0) {
        updateTrace({ step_type: 'status_change', content: '───── New Conversation ─────', metadata: { separator: true } });
      }
    }
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
    let activityTimer: number;

    const resetActivityTimer = () => {
      if (activityTimer) window.clearTimeout(activityTimer);
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
                console.debug("[RAW STREAM]", line.substring(0, 100));
                
                const data = JSON.parse(line);
                
                // --- STATE UPDATES ---
                if (data.type === 'status_change') {
                    setMissionState(prev => ({
                        ...prev,
                        phase: data.phase,
                        activeTool: data.tool || undefined,
                        retryCount: data.retry ? prev.retryCount + 1 : prev.retryCount
                    }));
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
                        }
                        break;
                    case 'tool_result':
                        updateTrace({ step_type: 'tool_result', content: data.name, metadata: { output: data.content } });
                        break;
                    case 'response':
                        updateTrace({ step_type: 'final_response', content: data.content });
                        addLog(MessageSource.AGENT, data.content);
                        speak(data.content);
                        setMissionState(prev => ({ ...prev, active: false }));
                        
                        // Check if agent is asking for approval - if so, keep session alive
                        const responseText = (data.content || '').toLowerCase();
                        const isApprovalRequest = responseText.includes('should i proceed') || 
                                                  responseText.includes('reply \'yes\'') ||
                                                  responseText.includes('approve or') ||
                                                  responseText.includes('confirm or cancel');
                        setAwaitingApproval(isApprovalRequest);
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
        buffer += decoder.decode(value, { stream: !done });
        
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
      window.clearTimeout(activityTimer);
      if (flushTimer) clearTimeout(flushTimer);

      // Final flush
      if (buffer.trim()) {
         processBuffer(true);
      }

      setStatus('idle');

    } catch (err: any) {
      window.clearTimeout(activityTimer);
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
    addLog(MessageSource.USER, `[UPLOAD] ${file.name}: ${message}`);
    setStatus('analyzing_visuals');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('prompt', message);

    try {
      const res = await fetch('/api/vision', { method: 'POST', body: formData });
      if (!res.ok) throw new Error(`Vision Upload Error: ${res.status}`);
      const data = await res.json();
      addLog(MessageSource.AGENT, data.response, { 
        model: data.used_model,
        type: 'vision_analysis',
        filename: file.name 
      });
      speak("Visual analysis complete. Rendering architect report.");
    } catch (err: any) {
      addLog(MessageSource.SYSTEM, `Error: ${err.message}`);
      setStatus('idle');
    }
  };

  const confirmAction = async () => {}; 
  const cancelAction = () => { setPendingAction(null); setStatus('idle'); };
  const toggleComplexity = () => setComplexity(prev => prev === 'fast' ? 'deep' : 'fast');
  const logSystemError = (msg: string) => addLog(MessageSource.SYSTEM, msg);
  const clearSession = () => { setSessionId(null); setLastTrace([]); };



  return {
    status,
    logs,
    lastTrace,
    complexity,
    pendingAction,
    missionState,
    sessionId,
    sendCommand,
    sendVisionCommand,
    toggleComplexity,
    confirmAction,
    cancelAction,
    logSystemError,
    clearSession
  };
};
