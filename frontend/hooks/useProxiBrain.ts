import { useState, useCallback, useEffect, useRef } from 'react';
import { LogEntry, MessageSource, Complexity, AgentStatus } from '../types';

export const useProxiBrain = () => {
  const [status, setStatus] = useState<AgentStatus>('idle');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [complexity, setComplexity] = useState<Complexity>('fast');
  const voicesRef = useRef<SpeechSynthesisVoice[]>([]);

  // Pre-load voices to ensure we don't get the default robotic voice
  useEffect(() => {
    const loadVoices = () => {
      voicesRef.current = window.speechSynthesis.getVoices();
    };
    
    // Chrome loads voices asynchronously
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
    
    window.speechSynthesis.cancel(); // Stop previous

    const utterance = new SpeechSynthesisUtterance(text);
    
    // Priority: Google US English -> Microsoft Zira -> Default
    const preferredVoices = voicesRef.current;
    const techVoice = preferredVoices.find(v => v.name.includes('Google US English')) 
                   || preferredVoices.find(v => v.name.includes('Zira')) 
                   || preferredVoices[0];
                   
    if (techVoice) utterance.voice = techVoice;
    
    utterance.rate = 1.05; 
    utterance.pitch = 0.95; // Slightly deeper

    utterance.onstart = () => setStatus('speaking');
    utterance.onend = () => setStatus('idle');
    utterance.onerror = (e) => {
        console.error("TTS Error", e);
        setStatus('idle');
    };

    window.speechSynthesis.speak(utterance);
  }, []);

  const sendCommand = async (message: string) => {
    if (!message.trim()) return;

    addLog(MessageSource.USER, message);
    setStatus('processing');

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message, 
          complexity 
        })
      });

      if (!res.ok) {
        throw new Error(`Server error: ${res.status}`);
      }

      const data = await res.json();
      
      addLog(MessageSource.AGENT, data.response, { model: data.model_used });
      
      // Auto-speak the response
      speak(data.response);

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
      const res = await fetch('/api/vision', {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        throw new Error(`Vision Upload Error: ${res.status}`);
      }

      const data = await res.json();
      
      addLog(MessageSource.AGENT, data.response, { 
        model: data.model_used,
        type: 'vision_analysis',
        filename: file.name 
      });
      
      speak("Visual analysis complete. Rendering architect report.");

    } catch (err: any) {
      console.error(err);
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
    complexity,
    sendCommand,
    sendVisionCommand,
    toggleComplexity
  };
};
