import { useState, useEffect, useCallback, useRef } from 'react';

export type BackendStatus = 'connected' | 'disconnected' | 'checking';

export const useBackendHealth = (intervalMs: number = 5000) => {
  const [status, setStatus] = useState<BackendStatus>('checking');
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [mode, setMode] = useState<string>('unknown');
  const intervalRef = useRef<number | null>(null);

  const checkHealth = useCallback(async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000); // 3s timeout
      
      const response = await fetch('/api/health', {
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      if (response.ok) {
        const data = await response.json();
        setStatus('connected');
        setMode(data.mode || 'unknown');
      } else {
        setStatus('disconnected');
      }
    } catch (err) {
      setStatus('disconnected');
    }
    setLastChecked(new Date());
  }, []);

  // Initial check and periodic keepalive
  useEffect(() => {
    checkHealth(); // Initial check
    
    intervalRef.current = window.setInterval(checkHealth, intervalMs);
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [checkHealth, intervalMs]);

  return { status, lastChecked, mode, checkHealth };
};
