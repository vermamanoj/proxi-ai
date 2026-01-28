# Proxi Hackathon Submission Checklist

**Competition:** Google Gemini Hackathon  
**Prize Pool:** $50,000 Top Prize  
**Judging Period:** February 10-27, 2026

---

## 1. Judging Criteria

| Criterion | Weight | Our Strength |
|-----------|--------|--------------|
| **Technical Execution** | 40% | Deep Gemini integration (Flash, Pro, Vision, Live) |
| **Innovation/Wow Factor** | 30% | Verifiable Agent + OS-level control (rare!) |
| **Potential Impact** | 20% | Enterprise IT automation, accessibility |
| **Presentation/Demo** | 10% | Mobile telepresence story |

### Current Estimated Score: **~3.5/5**
### Target Score: **4.6/5** (Top 3 Prize territory)

---

## 2. Submission Requirements

| Requirement | Status | Notes |
|-------------|--------|-------|
| ☐ Working demo URL | 🔄 | proxi.audista.com |
| ☐ 3-minute demo video | 📋 | Use DEMO_SCRIPT.md |
| ☐ 200-word Gemini write-up | 📋 | See template below |
| ☐ Architecture diagram | ✅ | In docs/ARCHITECTURE.md |
| ☐ Public repository | ✅ | github.com/vermamanoj/proxi-ai |
| ☐ Testing credentials | ✅ | demo/demo123, judge/gemini2026 |

---

## 3. Pre-Submission Checklist

### Demo Environment
- [ ] Production deploy verified (proxi.audista.com)
- [ ] HTTPS working
- [ ] Linux agent online and set as default
- [ ] Windows agent available (optional but impressive)
- [ ] Mock apps accessible (CRM, Pricing Tool)
- [ ] Brand template PPT in place

### Core Functionality
- [ ] Login working with demo credentials
- [ ] Voice commands functional (Gemini Live)
- [ ] Text commands functional
- [ ] Screenshot sharing works
- [ ] Triple Handshake verification visible
- [ ] Agent selector shows correct status

### Demo Scenario Test
- [ ] Run full DEMO_SCRIPT.md scenario
- [ ] Time it (target: under 3 minutes)
- [ ] Record any failures, fix them
- [ ] Prepare fallback responses

---

## 4. Demo Video Script

**Duration:** 3 minutes max

### Opening (15 sec)
> "This is Proxi - your AI desktop agent that works when you can't be at your desk."

### Problem Statement (20 sec)
> "Sarah is closing a $2.3M deal. Competition just undercut by 12%. She has 10 minutes to respond but can't leave the meeting room. She pulls out her phone..."

### Demo Flow (2 min)

| Time | Action | Shows |
|------|--------|-------|
| 0:00-0:20 | Voice: "Check our pricing system for minimum margin" | Vision analysis of legacy UI |
| 0:20-0:45 | Voice: "What's Acme Corp's history in our CRM?" | Multi-app navigation |
| 0:45-1:15 | Voice: "Find the brand template PPT I downloaded" | File discovery |
| 1:15-2:00 | Voice: "Create a business case slide" | PowerPoint automation |

### Closing (25 sec)
> "In under 3 minutes, Sarah gathered data from 2 legacy apps, found a forgotten file, and created a business case - all from her phone. Deal saved."
> 
> "Proxi: Full OS control. Verifiable results. Mobile telepresence."

---

## 5. 200-Word Gemini Write-up (Template)

```
Proxi leverages Google Gemini's multimodal capabilities to create the first 
verifiable OS-level AI agent accessible from mobile devices.

**Gemini Integration:**

1. **Gemini 2.0 Flash** powers rapid tool execution and real-time responses, 
   enabling natural voice conversations with sub-second latency.

2. **Gemini Vision** analyzes legacy application interfaces that lack APIs - 
   reading data from SAP-like systems, CRMs, and desktop apps through 
   screenshot analysis.

3. **Gemini Live** provides WebRTC-based voice I/O, letting users command 
   their desktop hands-free from their phone.

4. **Gemini Pro** handles complex multi-step reasoning when tasks require 
   planning across multiple applications.

**Innovation:**

Unlike browser-only agents, Proxi provides full OS control - mouse, keyboard, 
window management, and system commands. Our "Triple Handshake" protocol 
(Assign → Execute → Verify) ensures the agent proves task completion through 
independent system checks, not just LLM claims.

**Impact:**

Proxi enables "work while on the move" - sales reps closing deals from client 
sites, IT admins resolving incidents from anywhere, and accessibility for 
users who need voice-first computer control.

Built with: Gemini API, FastAPI, React, PyAutoGUI
```

---

## 6. Competitive Differentiators

### What Makes Proxi Unique

| Aspect | Competitors | Proxi |
|--------|-------------|-------|
| **Scope** | Browser DOM only | Full OS control |
| **Legacy Apps** | ❌ Cannot access | ✅ Vision-based reading |
| **Verification** | Trust LLM output | ✅ Independent audit |
| **Mobile Access** | Limited | ✅ Full telepresence |
| **Voice Control** | Text-first | ✅ Gemini Live native |

### Key Talking Points

1. **"No API? No problem."** - Proxi reads legacy UIs through vision
2. **"Proof, not promises."** - Triple Handshake verifies before reporting success
3. **"Your desktop in your pocket."** - True mobile OS control
4. **"Works with what you have."** - No integration required for existing apps

---

## 7. Risk Mitigation

### Demo Failures

| Risk | Mitigation |
|------|------------|
| Voice not working | Have text input ready as backup |
| Agent offline | Pre-check 10 min before demo |
| PPT not found | Have file path memorized |
| Vision misreads | Prepare to manually guide |

### Fallback Phrases

- "Let me try another approach..."
- "The desktop is connecting..."
- "I'll use the keyboard shortcut instead..."

---

## 8. Timeline to Submission

### Week of Feb 3-9

| Day | Task |
|-----|------|
| Mon | Final code freeze, deploy to production |
| Tue | Full demo run-through, fix issues |
| Wed | Record demo video (multiple takes) |
| Thu | Edit video, write submission text |
| Fri | Submit before deadline |
| Sat-Sun | Buffer for any issues |

### Feb 10 - Judging Starts

- Monitor for judge access
- Be ready to answer questions
- Keep demo environment stable

---

## 9. Judge Access

### Magic Link for Judges

```
https://proxi.audista.com/magic?token=GEMINI_JUDGE_2026
```

- Role: `judge`
- Permissions: Chat, view agents, trigger demo
- Session: 24 hours
- No password required

### Standard Credentials

| Username | Password | Role |
|----------|----------|------|
| `demo` | `demo123` | User |
| `judge` | `gemini2026` | Judge |
| `admin` | `proxi_admin_2026` | Admin |

---

## 10. Post-Submission

### If We Win
- Prepare for press/interviews
- Plan scaling strategy
- Consider enterprise pilot

### Regardless of Outcome
- Write blog post about the build
- Open source key components
- Continue development toward production

---

*Good luck! 🚀*
