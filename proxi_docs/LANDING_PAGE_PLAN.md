# Landing Page Visual Content Plan

**Created:** Feb 11, 2026  
**Status:** Planned  
**Context:** Current landing page (`frontend/components/LandingPage.tsx`) is entirely text + Lucide icons. No screenshots, videos, or product visuals. For a product built around visual desktop control, this is a critical gap.

---

## Priority Assets

### P0 — Hero Demo Video (30-60s, autoplay muted loop)
- **Placement**: Hero section, below subtitle, above CTAs
- **Content**: Phone → type "Kill the high-CPU process" → agent screenshots desktop → identifies process → kills it → sends confirmation screenshot back to chat
- **Shows**: Full Command → Execute → Verify loop
- **Format**: MP4, `<video autoPlay muted loop playsInline>`, dark bg, ~16:9

### P1 — Split-Screen Image: Phone + Desktop
- **Placement**: Solution section (replace/augment the Smartphone icon block)
- **Content**: Left = phone mockup with Proxi chat UI; Right = desktop showing agent navigating Chrome
- **Shows**: "Control your PC from your phone" concept at a glance

### P1 — Set-of-Mark (SoM) Vision Screenshot
- **Placement**: "Multimodal Vision" card in Powered by Gemini section
- **Content**: Actual SoM-annotated screenshot (numbered UI elements overlaid on real desktop)
- **Shows**: How Gemini vision grounding works — the core technical differentiator

### P1 — Verification Evidence Screenshot
- **Placement**: "Verified Execution" card in Trust by Design section
- **Content**: Chat UI showing: user request → agent trace → screenshot proof → green verification badge
- **Shows**: Proxi proves work, not just claims it

### P2 — Approval Flow GIF
- **Placement**: "Safety & Control" card in Trust by Design section
- **Content**: Agent encounters sensitive command → approval card appears → user taps Approve → command executes
- **Shows**: Traffic-light safety system in real action

### P2 — 4-Step Annotated Screenshots
- **Placement**: How It Works section (supplement each step card)
- **Steps**:
  1. **Command** — Phone mockup with natural language input
  2. **Execute** — Desktop screenshot of Proxi navigating an app
  3. **Approve** — Approval modal with a sensitive command
  4. **Verify** — Chat showing returned screenshot + checkmark

### P3 — Use Case Video Gallery (15-20s clips each)
- **Placement**: New section after "How It Works"
- **Clips**:
  - IT Incident Response: check Task Manager → kill runaway process → confirm
  - PowerPoint from Phone: add slide with chart → send screenshot
  - Security Investigation: run commands → store evidence → render attack path
  - Legacy App Automation: navigate CRM → fill form → confirm

### P3 — Architecture Diagram (Branded)
- **Placement**: Near Gemini section or new "Under the Hood" section
- **Content**: Clean version of `Phone → Core (Brain) → Agent (Hands)` with animated arrows

---

## OS-Aware Section Visuals
- **Unlocked card**: Screenshot of Proxi clicking through a GUI app (e.g., Windows Settings)
- **Locked card**: Terminal output showing Proxi executing commands while desktop is locked

---

## Implementation Notes
- All video/image assets go in `frontend/public/assets/` or a CDN
- Use `<video>` with `poster` frame for hero video
- Phone mockups: use a CSS device frame or a PNG mockup template
- Screenshots should be captured from the running app at 1920x1080, cropped/annotated
- Consider lazy loading for below-the-fold assets
- Mobile: use responsive `srcset` or smaller video files

---

*Last updated: Feb 11, 2026*
