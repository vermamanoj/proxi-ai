
import { useState, useCallback, useEffect, useRef } from 'react';
import { LogEntry, MessageSource, Complexity, AgentStatus, PendingAction, TraceStep } from '../types';

export const useProxiBrain = () => {
  const [status, setStatus] = useState<AgentStatus>('idle');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [lastTrace, setLastTrace] = useState<TraceStep[]>([]);
  const [complexity, setComplexity] = useState<Complexity>('fast');
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const voicesRef = useRef<SpeechSynthesisVoice[]>([]);

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

  const speak = useCallback((text: string) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const preferredVoices = voicesRef.current;
    const techVoice = preferredVoices.find(v => v.name.includes('Google US English')) 
                   || preferredVoices.find(v => v.name.includes('Zira')) 
                   || preferredVoices[0];
    if (techVoice) utterance.voice = techVoice;
    utterance.rate = 1.05; 
    utterance.pitch = 0.95; 
    utterance.onstart = () => setStatus('speaking');
    utterance.onend = () => {
      // If we have a pending action, switch to waiting state after speaking
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
    setPendingAction(null); // Clear previous

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message, 
          complexity 
        })
      });

      if (!res.ok) throw new Error(`Server error: ${res.status}`);

      const data = await res.json();
      
      addLog(MessageSource.AGENT, data.response, { model: data.used_model });
      
      // Update Trace Data
      if (data.trace_logs) {
         setLastTrace(data.trace_logs);
      }

      if (data.pending_action) {
        setPendingAction(data.pending_action);
        // Status will update to 'awaiting_confirmation' after speech ends
      }
      
      speak(data.response);

    } catch (err: any) {
      console.error(err);
      addLog(MessageSource.SYSTEM, `Error: ${err.message}`);
      setStatus('idle');
    }
  };

  const confirmAction = async () => {
    if (!pendingAction) return;
    
    addLog(MessageSource.SYSTEM, `Executing: ${pendingAction.description}`);
    setStatus('processing');

    try {
        const res = await fetch('/api/desktop/execute', { method: 'POST' });
        const data = await res.json();
        addLog(MessageSource.TOOL, `Ghost Operator Result: ${data.result}`);
        setPendingAction(null);
        setStatus('idle');
        speak("Action executed successfully.");
    } catch (err: any) {
        addLog(MessageSource.SYSTEM, `Execution Error: ${err.message}`);
        setStatus('idle');
    }
  };

  const cancelAction = () => {
      setPendingAction(null);
      addLog(MessageSource.SYSTEM, "Action cancelled by user.");
      setStatus('idle');
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

  const toggleComplexity = () => {
    setComplexity(prev => prev === 'fast' ? 'deep' : 'fast');
  };


  return {
    status,
    logs,
    lastTrace,
    complexity,
    pendingAction,
    sendCommand,
    sendVisionCommand,
    toggleComplexity,
    confirmAction,
    cancelAction
  };
};
