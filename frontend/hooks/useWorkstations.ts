import { useState, useEffect, useCallback } from 'react';
import { API_BASE } from '../constants';
import { DEFAULT_WORKSTATIONS, Workstation, WorkstationStatus } from '../config/workstations';

interface UseWorkstationsResult {
  workstations: Workstation[];
  activeWorkstation: Workstation | null;
  isLoading: boolean;
  error: string | null;
  backendAvailable: boolean;
  setActiveWorkstation: (id: string) => void;
  refreshWorkstations: () => Promise<void>;
}

/**
 * Hook for managing workstation state.
 * Fetches from backend API when available, falls back to static config.
 */
export function useWorkstations(): UseWorkstationsResult {
  const [workstations, setWorkstations] = useState<Workstation[]>(DEFAULT_WORKSTATIONS);
  const [activeWorkstationId, setActiveWorkstationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [backendAvailable, setBackendAvailable] = useState(false);

  // Fetch workstations from backend
  const fetchFromBackend = useCallback(async (): Promise<Workstation[] | null> => {
    try {
      const response = await fetch(`${API_BASE}/api/workstations`, {
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        setBackendAvailable(true);
        return data.workstations || data;
      }
      return null;
    } catch (err) {
      console.warn('Backend unavailable, using static workstation config');
      setBackendAvailable(false);
      return null;
    }
  }, []);

  // Check health of a single workstation
  const checkWorkstationHealth = useCallback(async (ws: Workstation): Promise<WorkstationStatus> => {
    try {
      // For localhost containers, check directly
      if (ws.host === '127.0.0.1' || ws.host === 'localhost') {
        const response = await fetch(`http://${ws.host}:${ws.port}/health`, {
          method: 'GET',
          signal: AbortSignal.timeout(3000),
        });
        return response.ok ? 'online' : 'offline';
      }
      
      // For remote workstations, ask backend to check
      if (backendAvailable) {
        const response = await fetch(`${API_BASE}/api/workstations/${ws.id}/health`, {
          credentials: 'include',
        });
        if (response.ok) {
          const data = await response.json();
          return data.status as WorkstationStatus;
        }
      }
      
      return 'unknown';
    } catch {
      return 'offline';
    }
  }, [backendAvailable]);

  // Refresh all workstations
  const refreshWorkstations = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Try backend first
      const backendWorkstations = await fetchFromBackend();
      
      if (backendWorkstations) {
        // Map snake_case from backend to camelCase for frontend
        const mappedWorkstations = backendWorkstations.map((ws: any) => ({
          ...ws,
          isDefault: ws.is_default || ws.isDefault || false,
        }));
        setWorkstations(mappedWorkstations);
      } else {
        // Use static config with health checks
        const updatedWorkstations = await Promise.all(
          DEFAULT_WORKSTATIONS.map(async (ws) => ({
            ...ws,
            status: await checkWorkstationHealth(ws),
          }))
        );
        setWorkstations(updatedWorkstations);
      }
    } catch (err) {
      setError('Failed to load workstations');
      setWorkstations(DEFAULT_WORKSTATIONS);
    } finally {
      setIsLoading(false);
    }
  }, [fetchFromBackend, checkWorkstationHealth]);

  // Initial load
  useEffect(() => {
    refreshWorkstations();
    
    // Refresh every 30 seconds
    const interval = setInterval(refreshWorkstations, 30000);
    return () => clearInterval(interval);
  }, [refreshWorkstations]);

  // Set default active workstation - prioritize online default, then any online, then first
  useEffect(() => {
    if (!activeWorkstationId && workstations.length > 0 && !isLoading) {
      // Priority: online default > any default > first online > first
      const onlineDefault = workstations.find(w => w.isDefault && w.status === 'online');
      const anyDefault = workstations.find(w => w.isDefault);
      const firstOnline = workstations.find(w => w.status === 'online');
      const defaultWs = onlineDefault || anyDefault || firstOnline || workstations[0];
      console.log('[Workstations] Auto-selecting:', defaultWs.id, defaultWs.name);
      setActiveWorkstationId(defaultWs.id);
    }
  }, [workstations, activeWorkstationId, isLoading]);

  const setActiveWorkstation = useCallback(async (id: string) => {
    // Check if agent is online before activating
    const ws = workstations.find(w => w.id === id);
    if (ws && ws.status === 'offline') {
      setError(`Cannot select "${ws.name}" - agent is offline`);
      console.warn(`Attempted to select offline agent: ${id}`);
      return;
    }
    
    setActiveWorkstationId(id);
    setError(null);
    
    // Notify backend to activate this agent for proxied tool execution
    if (backendAvailable) {
      try {
        const response = await fetch(`${API_BASE}/api/workstations/${id}/activate`, {
          method: 'POST',
          credentials: 'include',
        });
        if (!response.ok) {
          const data = await response.json();
          setError(data.detail || 'Failed to activate agent');
          return;
        }
        console.log(`Activated agent: ${id}`);
      } catch (err) {
        console.warn('Failed to activate agent on backend:', err);
        setError('Failed to connect to agent');
      }
    }
  }, [backendAvailable, workstations]);

  const activeWorkstation = workstations.find(w => w.id === activeWorkstationId) || null;

  return {
    workstations,
    activeWorkstation,
    isLoading,
    error,
    backendAvailable,
    setActiveWorkstation,
    refreshWorkstations,
  };
}

export default useWorkstations;
