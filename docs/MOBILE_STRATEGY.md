# Proxi Mobile App Strategy

**Last Updated:** January 28, 2026  
**Priority:** Post-Hackathon (P1)

---

## 1. Current State

### Web-Based Mobile Access
- ✅ Responsive React UI works on mobile browsers
- ✅ Gemini Live voice I/O functional
- ✅ Touch-friendly interface
- ⚠️ No push notifications
- ⚠️ Voice requires browser tab active
- ⚠️ No offline capability

### Limitations of PWA Approach
| Issue | Impact |
|-------|--------|
| Background audio | Voice stops when app backgrounded |
| Push notifications | Requires service worker setup |
| Camera access | Inconsistent across browsers |
| Always-on connection | Battery drain concerns |

---

## 2. Native App Recommendation

### Technology Choice: React Native

| Option | Pros | Cons |
|--------|------|------|
| **React Native** | Code reuse with web, fast dev | Bridge overhead |
| Flutter | Great performance | New language (Dart) |
| Native (Swift/Kotlin) | Best performance | 2x development effort |

**Recommendation:** React Native with Expo for rapid development.

### Why React Native?
1. **Code sharing** - 60-70% shared with web frontend
2. **Team expertise** - Already using React/TypeScript
3. **Expo** - Simplified build/deploy, OTA updates
4. **Community** - Large ecosystem, proven at scale

---

## 3. Mobile App Features

### Phase 1: MVP (4-6 weeks)

| Feature | Priority | Effort |
|---------|----------|--------|
| Login/auth | P0 | 1 week |
| Chat interface | P0 | 1 week |
| Voice commands | P0 | 2 weeks |
| Agent selector | P1 | 3 days |
| Push notifications | P1 | 1 week |
| Session persistence | P1 | 3 days |

### Phase 2: Enhanced (4 weeks)

| Feature | Priority | Effort |
|---------|----------|--------|
| Background voice | P1 | 1 week |
| Screenshot viewing | P1 | 3 days |
| Image upload (camera) | P1 | 1 week |
| Biometric login | P2 | 3 days |
| Offline queue | P2 | 1 week |
| Widgets (iOS/Android) | P3 | 1 week |

### Phase 3: Advanced (Ongoing)

| Feature | Priority | Notes |
|---------|----------|-------|
| Apple Watch / Wear OS | P3 | Quick commands |
| Siri / Google Assistant | P3 | Native voice triggers |
| CarPlay / Android Auto | P4 | Hands-free driving |

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     MOBILE APP ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  REACT NATIVE APP                                        │   │
│  │  ├── Auth (biometric + session)                         │   │
│  │  ├── Chat UI (shared components)                        │   │
│  │  ├── Voice (expo-av + Gemini Live)                      │   │
│  │  ├── Push (expo-notifications)                          │   │
│  │  └── State (Zustand or Redux)                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                      HTTPS + WebSocket                          │
│                            │                                    │
│  ┌─────────────────────────▼───────────────────────────────┐   │
│  │  PROXI CORE (Existing Backend)                          │   │
│  │  ├── /api/auth/* (existing)                             │   │
│  │  ├── /api/chat (existing)                               │   │
│  │  ├── /api/push/register (NEW)                           │   │
│  │  └── /api/push/send (NEW)                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Voice Implementation

### Challenge
Gemini Live uses WebRTC which has limited React Native support.

### Options

| Approach | Complexity | Quality |
|----------|------------|---------|
| **WebView for voice** | Low | Medium - may have latency |
| **Native WebRTC** | High | High - best performance |
| **Gemini REST + TTS** | Medium | Medium - no streaming |
| **expo-av recording** | Medium | Good - send audio chunks |

### Recommended: Hybrid Approach

1. Use `expo-av` for audio recording
2. Stream audio chunks to backend
3. Backend forwards to Gemini Live
4. Return audio response
5. Play via `expo-av`

```typescript
// Simplified flow
const startVoice = async () => {
  const recording = await Audio.Recording.createAsync();
  // Stream chunks to /api/voice/stream
  // Receive audio response
  // Play via Audio.Sound
};
```

---

## 6. Push Notifications

### Backend Additions

```python
# backend/push/push_service.py

class PushService:
    async def register_device(self, user_id: str, push_token: str):
        # Store token in DB
        pass
    
    async def send_notification(self, user_id: str, title: str, body: str):
        # Send via Expo Push API or FCM/APNs
        pass
```

### Notification Types

| Event | Notification |
|-------|--------------|
| Agent needs approval | "Proxi needs your approval to delete file.txt" |
| Task completed | "✅ CPU spike resolved - 15.4% now" |
| Escalation | "⚠️ Proxi needs help with multiple files found" |
| Agent offline | "🔴 Windows Desktop went offline" |

---

## 7. Development Timeline

### Hackathon Priority: LOW
Focus on web demo for hackathon. Mobile app is post-competition.

### Post-Hackathon Timeline

| Week | Milestone |
|------|-----------|
| 1-2 | Expo setup, navigation, auth |
| 3-4 | Chat UI, API integration |
| 5-6 | Voice recording + playback |
| 7 | Push notifications |
| 8 | Testing, polish, beta release |

### Team Requirements
- 1 React Native developer (can be existing React dev)
- Backend support for push endpoints
- Design support for mobile-specific UI

---

## 8. App Store Considerations

### iOS App Store
- Requires Apple Developer account ($99/year)
- Review process: 1-2 weeks first time
- Guidelines: No remote code execution concerns (we're just a client)

### Google Play Store
- Requires Google Play Console ($25 one-time)
- Review process: 1-3 days
- Less restrictive than iOS

### Beta Testing
- iOS: TestFlight (up to 10,000 testers)
- Android: Internal/Closed testing tracks

---

## 9. Competitive Advantage

### Why Mobile Matters
1. **"Always in your pocket"** - Desktop control from anywhere
2. **Push notifications** - Instant alerts for approvals
3. **Voice-first** - Natural interaction while multitasking
4. **Enterprise appeal** - IT admins, sales reps, executives

### Differentiation
- Most AI assistants are text-first
- Proxi mobile = voice-first OS control
- "Siri for your entire desktop, not just your phone"

---

## 10. Decision Points

### Build Now or Later?
**Later** - Focus on hackathon, then build mobile Q1 2026.

### Native or PWA?
**Native (React Native)** - Better voice, push, background support.

### iOS First or Android First?
**Both via React Native** - Single codebase, simultaneous release.

### Internal or Outsource?
**Internal** - Leverage existing React expertise, maintain quality.

---

*For current feature status, see [FEATURES.md](./FEATURES.md)*  
*For architecture details, see [ARCHITECTURE.md](./ARCHITECTURE.md)*
