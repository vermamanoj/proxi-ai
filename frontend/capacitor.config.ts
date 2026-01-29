import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.audista.proxi',
  appName: 'Proxi',
  webDir: 'dist',
  
  server: {
    // This ensures your origin is consistent. 
    // If your logs say 'http://localhost', keep this as 'http'.
    androidScheme: 'http', 
    cleartext: false,
    allowNavigation: [
      'https://*.audista.com',
      'https://*.google.com',
      'wss://*.google.com'
    ]
  },

  android: {
    allowMixedContent: true,
    captureInput: true,
    webContentsDebuggingEnabled: true
  },

  plugins: {
    // ADD THIS SECTION: This tells Capacitor to handle 'fetch' calls 
    // using native Android code instead of the restricted WebView browser.
    CapacitorHttp: {
      enabled: true,
    },
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      backgroundColor: '#0a0a0f',
      showSpinner: false
    }
  }
};

export default config;