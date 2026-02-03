// index.tsx
import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import posthog from 'posthog-js';
import './index.css';
import App from './App';
import AppV2 from './components/AppV2';
import AppV3 from './components/AppV3';

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
  if (route === '#/v2') {
    return <App />;  // Old v1 is now v2 (has admin console, magic links)
  }
  if (route === '#/v1') {
    return <AppV2 />;  // Old v2 is now v1 (deprecated)
  }
  return <AppV3 />;  // v3 is now default
};

// Register service worker for PWA
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((err) => {
      console.warn('SW registration failed:', err);
    });
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
