# Proxi Mobile Strategy

**Last Updated:** January 31, 2026  
**Status:** PWA Implemented, Capacitor Optional  
**Priority:** P0 (ASAP)  
**Tech Stack:** PWA (Primary) + Capacitor (Optional)  
**Target:** iOS & Android

---

## 1. Executive Summary

Proxi now supports **two mobile deployment strategies**:

### Option A: PWA (Progressive Web App) 
- **Status:** Complete and working
- **Install:** Users visit HTTPS URL → "Add to Home Screen"
- **Benefits:** No app store, instant updates, works offline
- **Limitation:** Voice mode requires HTTPS + user permission

### Option B: Capacitor Native Wrapper (Original Plan)
- **Status:** Documented but faced CORS/connectivity issues
- **Use Case:** If native APIs are absolutely required

### Recommendation for Hackathon
**Use PWA** - simpler, already working, no app store delays.

---

## 1.1 PWA Implementation (v3.4.0)

PWA files created:
- `frontend/public/manifest.json` - App metadata, icons, theme
- `frontend/public/sw.js` - Service worker for offline caching
- `frontend/public/offline.html` - Offline fallback page
- `frontend/public/icons/` - 192x192 and 512x512 SVG icons

### How to Install (User Flow)
1. Visit `https://proxi.audista.com` on mobile browser
2. Browser shows "Add to Home Screen" prompt (or use menu)
3. App icon appears on home screen
4. Opens in standalone mode (no browser chrome)

### PWA Requirements
- HTTPS (required for service worker)
- manifest.json with icons
- Service worker registered
- Responsive design
- Offline page

---

## 2. Capacitor Approach (Alternative)

The original plan using Capacitor to wrap the React app in a native container.

### Benefits
- **Zero Logic Rewrite** - 100% code reuse of existing UI and business logic
- **Speed to Build** - Functional APK/IPA in 24-48 hours
- **Single Codebase** - Web + iOS + Android from one repo

### Known Issues (Why PWA is Preferred)
- **CORS/Connectivity:** Had unresolved issues with API calls from native container
- **API Key Exposure:** `VITE_GEMINI_API_KEY` bundled in APK is extractable
- **Voice/WebRTC:** Inconsistent behavior in mobile WebViews

**Mitigation:** Test on physical device in Phase 1. If fails, implement backend audio relay.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MOBILE APP ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  CAPACITOR NATIVE SHELL                              │   │
│  │  ├── Android (Kotlin) / iOS (Swift)                 │   │
│  │  ├── Native Plugins (Camera, Mic, Secure Storage)   │   │
│  │  └── System WebView (Chrome/Safari engine)          │   │
│  └─────────────────────────────────────────────────────┘   │
│                            │                                │
│  ┌─────────────────────────▼───────────────────────────┐   │
│  │  PROXI REACT APP (Bundled Local Files)              │   │
│  │  ├── App.tsx (existing UI)                          │   │
│  │  ├── useGeminiLive.ts (voice)                       │   │
│  │  └── useProxiBrain.ts (chat)                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                            │                                │
│                      HTTPS / WSS                            │
│                            │                                │
│  ┌─────────────────────────▼───────────────────────────┐   │
│  │  PROXI CORE BACKEND (Cloud)                         │   │
│  │  ├── /api/auth/* (login, sessions)                  │   │
│  │  ├── /api/chat (LLM orchestration)                  │   │
│  │  ├── /api/push/register (NEW - for notifications)   │   │
│  │  └── /api/voice/relay (NEW - fallback for WebRTC)   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

| Layer | Technology | Notes |
|-------|------------|-------|
| **UI** | React + Tailwind CSS | No changes required |
| **Native Shell** | Capacitor 5.x | Android + iOS platforms |
| **Voice** | WebRTC via WebView | Test first, fallback to relay |
| **Storage** | @capacitor/preferences | Secure storage for tokens |

---

## 3. Required Code Changes

### 3.1 Backend URL Configuration

Current code uses relative paths (`/api/chat`). Mobile needs absolute URLs.

**Add to `frontend/vite.config.ts`:**
```typescript
define: {
  'import.meta.env.VITE_API_BASE_URL': JSON.stringify(
    process.env.VITE_API_BASE_URL || ''
  )
}
```

**Update API calls to use:**
```typescript
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';
fetch(`${API_BASE}/api/chat`, ...)
```

### 3.2 API Key Security (CRITICAL)

**Problem:** `VITE_GEMINI_API_KEY` is bundled into APK - extractable by anyone.

**Solution:** Backend voice relay endpoint:
```python
# backend/main.py - NEW ENDPOINT
@app.post("/api/voice/session")
async def create_voice_session(user: User = Depends(get_current_user)):
    # Returns short-lived token for Gemini Live
    # Or proxies audio through backend
```

**For hackathon:** Acceptable risk. **For production:** Must fix.

### 3.3 Capacitor Configuration

**Create `capacitor.config.ts`:**
```typescript
import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.audista.proxi',
  appName: 'Proxi',
  webDir: 'dist',
  server: {
    // Production: use your deployed backend
    url: 'https://api.proxi.audista.com',
    cleartext: false  // HTTPS only
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: false
    }
  },
  android: {
    allowMixedContent: false  // Security: no HTTP
  },
  ios: {
    contentInset: 'always'  // Safe area handling
  }
};

export default config;
```

---

## 4. Security Strategy

### A. Secure Token Storage

| Risk | Solution |
|------|----------|
| localStorage dump on rooted device | Use `@capacitor/preferences` with encryption |
| API key in bundle | Move to backend proxy (post-hackathon) |

### B. Network Security

- **HTTPS only** - Set `cleartext: false` in Capacitor config
- **Domain whitelist** - Only allow `*.audista.com` in `allowNavigation`
- **Certificate pinning** - Add for production (post-hackathon)

### C. Permission Minimization

| Permission | When to Request |
|------------|-----------------|
| Microphone | On "Start Voice" button tap |
| Camera | On image upload tap |
| Push Notifications | After first successful login |

### D. Code Obfuscation

Vite production build already minifies. For extra security:
```typescript
// vite.config.ts
build: {
  minify: 'terser',
  terserOptions: {
    mangle: true,
    compress: { drop_console: true }
  }
}
```

---

## 5. Implementation Plan

### Phase 0: WebRTC Validation (Hours 0-2) ⚠️ CRITICAL

**Before any development**, test if Gemini Live works in mobile WebView:

1. Open `https://proxi.audista.com` on Android Chrome
2. Click microphone button
3. Speak and verify voice recognition works
4. Check for WebRTC errors in `chrome://inspect`

**If it fails:** Implement `/api/voice/relay` endpoint first.

### Phase 1: Capacitor Setup (Hours 2-4)

```bash
cd frontend
npm install @capacitor/core @capacitor/cli
npx cap init Proxi com.audista.proxi --web-dir dist

# Add platforms
npm install @capacitor/android @capacitor/ios
npx cap add android
npx cap add ios
```

### Phase 2: Build Configuration (Hours 4-6)

1. Update `vite.config.ts` with `base: './'`
2. Add `VITE_API_BASE_URL` to build
3. Build: `npm run build`
4. Sync: `npx cap sync`

### Phase 3: Native Permissions (Hours 6-8)

**Android (`android/app/src/main/AndroidManifest.xml`):**
```xml
<uses-permission android:name="android.permission.RECORD_AUDIO"/>
<uses-permission android:name="android.permission.CAMERA"/>
<uses-permission android:name="android.permission.INTERNET"/>
```

**iOS (`ios/App/App/Info.plist`):**
```xml
<key>NSMicrophoneUsageDescription</key>
<string>Proxi needs microphone access for voice commands</string>
<key>NSCameraUsageDescription</key>
<string>Proxi needs camera access to capture screenshots</string>
```

### Phase 4: Build & Sign (Hours 8-12)

**Android:**
```bash
cd android
./gradlew assembleRelease
# Sign with keystore
```

**iOS:**
- Open `ios/App/App.xcworkspace` in Xcode
- Set Team ID
- Archive → Distribute

### Phase 5: Testing (Hours 12-24)

| Test Case | Expected |
|-----------|----------|
| Login flow | Works with existing credentials |
| Text chat | Messages send/receive |
| Voice chat | Mic activates, Gemini responds |
| Image upload | Camera captures, sends to backend |
| Session persistence | Survives app restart |

---

## 6. Fallback: Backend Voice Relay

If WebRTC fails in WebView, implement this:

```python
# backend/services/voice_relay.py
import asyncio
from google import genai

class VoiceRelayService:
    async def create_session(self, user_id: str):
        """Create Gemini Live session on backend"""
        client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        session = await client.aio.live.connect(model='gemini-2.0-flash')
        return session_id
    
    async def send_audio(self, session_id: str, audio_chunk: bytes):
        """Forward audio chunk to Gemini"""
        session = self.sessions[session_id]
        await session.send(audio_chunk)
    
    async def receive_audio(self, session_id: str) -> bytes:
        """Get audio response from Gemini"""
        session = self.sessions[session_id]
        return await session.receive()
```

**Mobile app would:**
1. Record audio using Capacitor native plugin
2. POST chunks to `/api/voice/send`
3. GET responses from `/api/voice/receive`
4. Play audio using native player

---

## 7. Push Notifications (Post-MVP)

Essential for mobile UX:

| Event | Notification |
|-------|--------------|
| Approval needed | "Proxi needs approval to delete file.txt" |
| Task completed | "✅ Backup completed successfully" |
| Agent offline | "🔴 Windows Desktop disconnected" |

**Implementation:** Firebase Cloud Messaging (Android) + APNs (iOS)

---

## 8. Progress Tracker

### ✅ Completed (Jan 29, 2026)

| Step | Status | Notes |
|------|--------|-------|
| WebRTC tested on mobile browser | ✅ Done | Voice works in Android/iOS browsers |
| Capacitor 5.7.8 installed | ✅ Done | Using v5 for Node 20 compatibility |
| `vite.config.ts` updated | ✅ Done | `base: './'` for mobile, code-splitting |
| `capacitor.config.ts` created | ✅ Done | Security settings, domain whitelist |
| Android platform added | ✅ Done | `frontend/android/` generated |
| Android permissions configured | ✅ Done | Mic, camera, audio settings |
| Web assets synced | ✅ Done | `npx cap sync android` |
| **Native HTTP plugin** | ✅ Done | `@capacitor-community/http` - bypasses CORS |
| **Mobile-first login** | ✅ Done | Skips landing page, goes straight to login |
| **HTTP client wrapper** | ✅ Done | `services/httpClient.ts` - native on mobile |

### 🔲 Pending (Resume When Ready)

| Step | Command | Notes |
|------|---------|-------|
| **Set production backend URL** | Edit `capacitor.config.ts` | Uncomment `server.url` |
| **Open Android Studio** | `npx cap open android` | From `frontend/` directory |
| **Build debug APK** | `Build → Build APK(s)` | In Android Studio |
| **Generate release keystore** | Android Studio or `keytool` | For signed release |
| **Build release APK** | `./gradlew assembleRelease` | Signed APK for distribution |

### Commands Reference

```powershell
# From frontend/ directory

# Rebuild after frontend changes
$env:CAPACITOR_BUILD='true'; npm run build
npx cap sync android

# Open in Android Studio
npx cap open android

# Build APK from command line (requires Java + Android SDK)
cd android
./gradlew assembleDebug
# APK at: app/build/outputs/apk/debug/app-debug.apk
```

### Files Created

| File | Purpose |
|------|---------|
| `frontend/capacitor.config.ts` | Capacitor configuration |
| `frontend/android/` | Android native project |
| `frontend/android/app/src/main/AndroidManifest.xml` | Permissions |

---

## 9. iOS Setup (Future)

```bash
# From frontend/ directory
npm install @capacitor/ios@5.7.8
npx cap add ios
npx cap open ios  # Opens Xcode
```

**Requires:**
- macOS with Xcode installed
- Apple Developer account ($99/year)

---

## 10. Checklist

### Pre-Production
- [x] Test WebRTC on physical Android device via Chrome
- [ ] Test WebRTC on physical iOS device via Safari
- [ ] Generate Android keystore
- [ ] Get Apple Developer Team ID

### Development (Completed)
- [x] `npm install @capacitor/core @capacitor/cli`
- [x] Update `vite.config.ts` with `base: './'`
- [x] Add `VITE_API_BASE_URL` configuration
- [x] Create `capacitor.config.ts`
- [x] Add Android platform
- [x] Configure permissions in manifests
- [ ] Build and test APK on physical device

### Post-Hackathon
- [ ] Move Gemini API key to backend proxy
- [ ] Implement push notifications
- [ ] Add certificate pinning
- [ ] App Store / Play Store submission

---

*For architecture details, see [ARCHITECTURE.md](./ARCHITECTURE.md)*  
*For deployment guide, see [DEPLOY_OPS.md](./DEPLOY_OPS.md)*