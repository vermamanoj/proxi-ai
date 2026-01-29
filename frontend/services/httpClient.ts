/**
 * HTTP Client - Uses native HTTP on Capacitor, fetch on web
 * Bypasses CORS/Cloudflare issues on mobile
 */

import { CapacitorHttp, HttpResponse } from '@capacitor/core';
import { API_BASE } from '../constants';

const isCapacitor = typeof (window as any)?.Capacitor !== 'undefined';

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  headers?: Record<string, string>;
  body?: any;
  credentials?: 'include' | 'omit' | 'same-origin';
}

interface ApiResponse<T = any> {
  ok: boolean;
  status: number;
  data: T | null;
  error?: string;
}

/**
 * Make an HTTP request using native HTTP on mobile, fetch on web
 */
export async function httpRequest<T = any>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<ApiResponse<T>> {
  const url = `${API_BASE}${endpoint}`;
  const { method = 'GET', headers = {}, body, credentials = 'include' } = options;

  console.log(`[HTTP] ${method} ${url} (native: ${isCapacitor})`);

  if (isCapacitor) {
    // Use Capacitor native HTTP - bypasses CORS entirely
    try {
      const response: HttpResponse = await CapacitorHttp.request({
        url,
        method,
        headers: {
          'Content-Type': 'application/json',
          ...headers,
        },
        data: body,
        webFetchExtra: {
          credentials,
        },
      });

      console.log(`[HTTP] Response: ${response.status}`);

      return {
        ok: response.status >= 200 && response.status < 300,
        status: response.status,
        data: response.data as T,
      };
    } catch (error: any) {
      console.error('[HTTP] Native request failed:', error);
      return {
        ok: false,
        status: 0,
        data: null,
        error: error.message || 'Network error',
      };
    }
  } else {
    // Use standard fetch for web
    try {
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...headers,
        },
        body: body ? JSON.stringify(body) : undefined,
        credentials,
      });

      let data: T | null = null;
      const contentType = response.headers.get('content-type');
      if (contentType?.includes('application/json')) {
        data = await response.json();
      }

      return {
        ok: response.ok,
        status: response.status,
        data,
      };
    } catch (error: any) {
      console.error('[HTTP] Fetch failed:', error);
      return {
        ok: false,
        status: 0,
        data: null,
        error: error.message || 'Network error',
      };
    }
  }
}

// Convenience methods
export const api = {
  get: <T = any>(endpoint: string, headers?: Record<string, string>) =>
    httpRequest<T>(endpoint, { method: 'GET', headers }),

  post: <T = any>(endpoint: string, body?: any, headers?: Record<string, string>) =>
    httpRequest<T>(endpoint, { method: 'POST', body, headers }),

  put: <T = any>(endpoint: string, body?: any, headers?: Record<string, string>) =>
    httpRequest<T>(endpoint, { method: 'PUT', body, headers }),

  delete: <T = any>(endpoint: string, headers?: Record<string, string>) =>
    httpRequest<T>(endpoint, { method: 'DELETE', headers }),
};
