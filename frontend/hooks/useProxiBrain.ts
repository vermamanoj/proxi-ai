
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

  const updateTrace = (step: TraceStep) => {
      setLastTrace(prev => [...prev, step]);
  };

  const cleanTextForSpeech = (text: string) => {
      // Remove Markdown bold/italic/code markers
      return text.replace(/[*#_`]/g, '')
                 .replace(/\[.*?\]/g, '') // Remove [links]
                 .replace(/\(https?:\/\/.*?\)/g, ''); // Remove (urls)
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
    setLastTrace([]); // Clear trace for new command
    
    // Initial trace step
    updateTrace({ step_type: 'user_input', content: message, metadata: { complexity } });

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, complexity })
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        const chunkValue = decoder.decode(value, { stream: !done });
        
        // Split by newline for NDJSON
        const lines = chunkValue.split('\n').filter(line => line.trim() !== '');
        
        for (const line of lines) {
            try {
                const data = JSON.parse(line);
                
                switch (data.type) {
                    case 'llm_thought':
                        updateTrace({ step_type: 'llm_thought', content: data.content });
                        break;
                    case 'tool_call_batch':
                        // data.calls is array of {name, args}
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
                        break;
                    case 'error':
                        addLog(MessageSource.SYSTEM, `Error: ${data.content}`);
                        break;
                }
            } catch (e) {
                console.error("Failed to parse chunk", line);
            }
        }
      }

      setStatus('idle');

    } catch (err: any) {
      console.error(err);
      addLog(MessageSource.SYSTEM, `Error: ${err.message}`);
      setStatus('idle');
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

  // ... rest of actions (confirm/cancel/toggle)
  const confirmAction = async () => {}; // Atomic mode deprecated
  const cancelAction = () => { setPendingAction(null); setStatus('idle'); };
  const toggleComplexity = () => setComplexity(prev => prev === 'fast' ? 'deep' : 'fast');

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
