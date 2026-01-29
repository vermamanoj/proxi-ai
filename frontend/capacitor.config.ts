import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.audista.proxi',
  appName: 'Proxi',
  webDir: 'dist',
  
  // Server configuration for API calls
  server: {
    // For development: leave empty to use relative paths with proxy
    // For production: set to your backend URL (e.g., 'https://api.proxi.audista.com')
    // url: 'https://api.proxi.audista.com',
    cleartext: false,  // Security: block HTTP, require HTTPS
    allowNavigation: [
      'https://*.audista.com',
      'https://*.google.com',  // For Gemini API
      'wss://*.google.com'     // For Gemini Live WebSocket
    ]
  },

  // Android-specific settings
  android: {
    allowMixedContent: true,   // Allow during development
    captureInput: true,        // Better keyboard handling
    webContentsDebuggingEnabled: true  // Enable for debugging - disable in production
  },

  // Plugins configuration
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      backgroundColor: '#0a0a0f',  // Match Proxi dark theme
      showSpinner: false
    }
  }
};

export default config;
