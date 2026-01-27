import { useState, useEffect, useCallback } from 'react';
import { API_BASE } from '../constants';

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
    try {
      const response = await fetch(`${API_BASE}/api/auth/session`, {
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        setAuthState({
          isAuthenticated: true,
          user: {
            username: data.username,
            displayName: data.display_name,
            role: data.role,
          },
          isLoading: false,
        });
      } else {
        setAuthState({
          isAuthenticated: false,
          user: null,
          isLoading: false,
        });
      }
    } catch (error) {
      console.error('Session check failed:', error);
      // For demo/hackathon: allow bypass if backend is not available
      const savedAuth = localStorage.getItem('proxi_auth');
      if (savedAuth) {
        try {
          const user = JSON.parse(savedAuth);
          setAuthState({
            isAuthenticated: true,
            user,
            isLoading: false,
          });
          return;
        } catch (e) {
          // Invalid saved auth
        }
      }
      setAuthState({
        isAuthenticated: false,
        user: null,
        isLoading: false,
      });
    }
  }, []);

  const login = useCallback(async (username: string, password: string): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ username, password }),
      });

      if (response.ok) {
        const data = await response.json();
        const user = {
          username: data.username,
          displayName: data.display_name,
          role: data.role,
        };
        setAuthState({
          isAuthenticated: true,
          user,
          isLoading: false,
        });
        // Save to localStorage for demo purposes
        localStorage.setItem('proxi_auth', JSON.stringify(user));
        return true;
      }
      return false;
    } catch (error) {
      console.error('Login failed:', error);
            return false;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch (error) {
      console.error('Logout API failed:', error);
    }
    
    // Clear local state regardless of API success
    localStorage.removeItem('proxi_auth');
    setAuthState({
      isAuthenticated: false,
      user: null,
      isLoading: false,
    });
  }, []);

  const redeemMagicLink = useCallback(async (token: string): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE}/api/auth/magic-link/${token}/redeem`, {
        method: 'POST',
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        const user = {
          username: data.username,
          displayName: data.display_name,
          role: data.role,
        };
        setAuthState({
          isAuthenticated: true,
          user,
          isLoading: false,
        });
        localStorage.setItem('proxi_auth', JSON.stringify(user));
        return true;
      }
      return false;
    } catch (error) {
      console.error('Magic link redemption failed:', error);
      return false;
    }
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
