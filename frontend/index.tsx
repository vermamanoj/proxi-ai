// index.tsx
import React, { useState, useEffect, Suspense, lazy } from 'react';
import ReactDOM from 'react-dom/client';
import posthog from 'posthog-js';
import './index.css';

// Lazy load App versions - only the active one will be loaded
const App = lazy(() => import('./App'));
const AppV2 = lazy(() => import('./components/AppV2'));
const AppV3 = lazy(() => import('./components/AppV3'));

// Loading fallback
const LoadingFallback = () => (
  <div className="h-screen bg-black flex items-center justify-center">
    <div className="text-center">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#00f0ff" strokeWidth="2" className="mx-auto mb-4 animate-pulse">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
      </svg>
      <p className="text-gray-400 text-sm">Loading Proxi...</p>
    </div>
  </div>
);

// Initialize PostHog with session recording
const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY;
if (POSTHOG_KEY) {
  posthog.init(POSTHOG_KEY, {
    api_host: 'https://app.posthog.com',
    capture_pageview: true,
    capture_pageleave: true,
    autocapture: true,
    // Session recording config
    disable_session_recording: false,
    session_recording: {
      maskAllInputs: false,  // Set true to mask sensitive inputs
      maskInputOptions: {
        password: true,  // Always mask passwords
      },
    },
    // Performance
    loaded: (posthog) => {
      if (import.meta.env.DEV) {
        console.log('[PostHog] Initialized');
      }
    },
  });
}

// Export for use in components
export { posthog };

// Simple hash router
// v3 = primary (default landing page after login)
// v2 = legacy v1 (admin console, magic links)
// v1 = temporary/deprecated
const Router: React.FC = () => {
  const [route, setRoute] = useState(window.location.hash);

  useEffect(() => {
    const handleHashChange = () => setRoute(window.location.hash);
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  // Routes: /#/v2 = legacy with admin features, /#/v1 = deprecated
  // Default = v3 (new primary)
  const AppComponent = route === '#/v2' ? App : route === '#/v1' ? AppV2 : AppV3;
  
  return (
    <Suspense fallback={<LoadingFallback />}>
      <AppComponent />
    </Suspense>
  );
};

// Register service worker for PWA with forced update
if ('serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      // Force update check on every page load
      const registration = await navigator.serviceWorker.register('/sw.js', { updateViaCache: 'none' });
      
      // Check for updates immediately
      registration.update();
      
      // If there's a waiting worker, activate it
      if (registration.waiting) {
        registration.waiting.postMessage({ type: 'SKIP_WAITING' });
      }
      
      // Listen for new service worker
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // New version available, reload to activate
              console.log('[SW] New version available, reloading...');
              window.location.reload();
            }
          });
        }
      });
    } catch (err) {
      console.warn('SW registration failed:', err);
    }
  });
}

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error("Could not find root element to mount to");
}

const root = ReactDOM.createRoot(rootElement);
root.render(
  <React.StrictMode>
    <Router />
  </React.StrictMode>
);
