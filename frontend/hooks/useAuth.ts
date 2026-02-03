import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/httpClient';
import posthog from 'posthog-js';

interface User {
  username: string;
  displayName: string;
  role: string;
}

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  isLoading: boolean;
}

export function useAuth() {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    isLoading: true,
  });

  // Check session on mount
  useEffect(() => {
    checkSession();
  }, []);

  const checkSession = useCallback(async () => {
    const isCapacitor = typeof (window as any)?.Capacitor !== 'undefined';
    console.log(`[Auth] Checking session - mobile: ${isCapacitor}`);
    
    const response = await api.get('/api/auth/session');
    console.log(`[Auth] Session check response: ${response.status}`);
    
    if (response.ok && response.data) {
      console.log(`[Auth] Session valid for: ${response.data.username}`);
      setAuthState({
        isAuthenticated: true,
        user: {
          username: response.data.username,
          displayName: response.data.display_name,
          role: response.data.role,
        },
        isLoading: false,
      });
    } else {
      console.log(`[Auth] No valid session (${response.status})`);
      setAuthState({
        isAuthenticated: false,
        user: null,
        isLoading: false,
      });
    }
  }, []);

  const login = useCallback(async (username: string, password: string, rememberMe: boolean = false): Promise<boolean> => {
    const isCapacitor = typeof (window as any)?.Capacitor !== 'undefined';
    console.log(`[Auth] Login attempt - user: ${username}, mobile: ${isCapacitor}`);
    
    const response = await api.post('/api/auth/login', { username, password, remember_me: rememberMe });
    console.log(`[Auth] Response status: ${response.status}`);
    
    if (response.ok && response.data) {
      const user = {
        username: response.data.username,
        displayName: response.data.display_name,
        role: response.data.role,
      };
      setAuthState({
        isAuthenticated: true,
        user,
        isLoading: false,
      });
      localStorage.setItem('proxi_auth', JSON.stringify(user));
      console.log(`[Auth] Login successful: ${user.username}`);
      
      // Identify user in PostHog for analytics
      posthog.identify(user.username, {
        name: user.displayName,
        role: user.role,
      });
      
      return true;
    }
    
    console.error(`[Auth] Login failed - status: ${response.status}, error: ${response.error}`);
    return false;
  }, []);

  const logout = useCallback(async () => {
    await api.post('/api/auth/logout');
    localStorage.removeItem('proxi_auth');
    posthog.reset();  // Clear PostHog user identification
    setAuthState({
      isAuthenticated: false,
      user: null,
      isLoading: false,
    });
  }, []);

  const redeemMagicLink = useCallback(async (token: string): Promise<boolean> => {
    const response = await api.post(`/api/auth/magic-link/${token}/redeem`);
    
    if (response.ok && response.data) {
      const user = {
        username: response.data.username,
        displayName: response.data.display_name,
        role: response.data.role,
      };
      setAuthState({
        isAuthenticated: true,
        user,
        isLoading: false,
      });
      localStorage.setItem('proxi_auth', JSON.stringify(user));
      return true;
    }
    console.error('Magic link redemption failed:', response.error);
    return false;
  }, []);

  return {
    ...authState,
    login,
    logout,
    checkSession,
    redeemMagicLink,
  };
}

export default useAuth;
