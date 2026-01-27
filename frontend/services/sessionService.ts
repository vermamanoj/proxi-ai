import { API_BASE } from '../constants';

export interface SessionGoal {
  id: string;
  title: string;
  status: 'pending' | 'active' | 'complete' | 'failed';
  requirementId?: string;
  result?: string;
}

export interface SessionMessage {
  id: string;
  timestamp: string;
  source: 'user' | 'agent' | 'system' | 'tool';
  text: string;
  metadata?: any;
}

export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  status: 'active' | 'closed';
  requirements: string[];
  goals: SessionGoal[];
  messages: SessionMessage[];
}

export interface SessionSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  status: string;
}

// Create a new session in backend
export async function createSession(sessionId: string, title?: string): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, title })
    });
  } catch (e) {
    console.warn('[Session] Failed to create session:', e);
  }
}

// Get session details
export async function getSession(sessionId: string): Promise<Session | null> {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    console.warn('[Session] Failed to get session:', e);
    return null;
  }
}

// Update session data
export async function updateSession(sessionId: string, data: Partial<Session>): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
  } catch (e) {
    console.warn('[Session] Failed to update session:', e);
  }
}

// Get list of sessions
export async function getSessions(limit: number = 20): Promise<SessionSummary[]> {
  try {
    const res = await fetch(`${API_BASE}/api/sessions?limit=${limit}`);
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    console.warn('[Session] Failed to get sessions:', e);
    return [];
  }
}

// Close/archive a session
export async function closeSession(sessionId: string): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/sessions/${sessionId}/close`, { method: 'POST' });
  } catch (e) {
    console.warn('[Session] Failed to close session:', e);
  }
}

// Add a goal to session
export async function addSessionGoal(sessionId: string, goal: SessionGoal): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/sessions/${sessionId}/goals`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(goal)
    });
  } catch (e) {
    console.warn('[Session] Failed to add goal:', e);
  }
}

// Update goal status
export async function updateGoalStatus(sessionId: string, goalId: string, status: string, result?: string): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/sessions/${sessionId}/goals/${goalId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status, result })
    });
  } catch (e) {
    console.warn('[Session] Failed to update goal:', e);
  }
}

// Save messages to session (batch update)
export async function saveSessionMessages(sessionId: string, messages: SessionMessage[]): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages })
    });
  } catch (e) {
    console.warn('[Session] Failed to save messages:', e);
  }
}
