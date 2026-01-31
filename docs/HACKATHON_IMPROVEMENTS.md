# Proxi Hackathon Improvements Tracker

> **Goal:** First Prize in Google Gemini 3 Hackathon  
> **Deadline:** Feb 9, 2026 @ 5:00 PM PST  
> **Last Updated:** Jan 31, 2026 10:56 AM

---

## Priority Order (Revised after code review)

| # | Item | Status | Complexity | Notes |
|---|------|--------|------------|-------|
| 1 | Build demo web apps (CRM/Pricing) with navigation | 🔴 TODO | Medium | JSON backend, multi-tab UI |
| 2 | Test/fix navigation tools (pywinauto, focus_window) | 🔴 TODO | Medium | Agent struggled in last test |
| 3 | Configure evidence display for demo mode | 🔴 TODO | Low | Feature EXISTS (#ID system), just needs flag |
| 4 | Fix Mermaid error handling | 🟡 PARTIAL | Low | Try/catch EXISTS, but still crashes on bad syntax |
| 5 | Document command_guard safety for presentation | 🔴 TODO | Low | PROXI_DEV_MODE bypass exists |
| 6 | Consider user ! override for blocked commands | 🔴 TODO | Low | Design decision |
| 7 | Fix verification for complex tasks only | � INVESTIGATE | Medium | Code exists, may be prompting issue |
| 8 | Polish landing page | 🔴 TODO | Low | After video |
| 9 | Record 3-minute demo video | 🔴 TODO | - | LAST STEP |

---

## 1. Verification System - CLARIFIED

### User Feedback
- Verification was **overkill for simple tasks** (ls, pwd, ps)
- **CPU verification always failed** because CPU% changes every second (agent: 60%, verifier: 30%)
- **Want verification only for complex jobs**: terminate process, create PPT, etc.
- Something may be wrong with code path

### Code Status (Verified)
- ✅ `orchestrator.py` has full Triple Handshake: `assign_mission()`, `report_execution()`, `verify_mission()`
- ✅ `gemini_service.py:1857-1869` calls `verify_mission()` after `report_execution()`
- ✅ Yields `{"type": "verification", "status": "success/failed"}` to frontend
- ✅ `MissionControl.tsx` shows verification outcomes (lines 141-161)
- ⚠️ Only triggers when agent uses Triple Handshake tools - LLM may skip them

### Possible Issues
1. System prompt tells LLM when to use Triple Handshake, but LLM doesn't always follow
2. `complexity: quick` mode says "skips verification" in UI tooltip
3. For transient metrics (CPU), verification will always fail (by design)

### Action
- **Defer** - Focus on demo apps first. If agent claims work but didn't do it during demo, investigate prompt

---

## 2. Evidence System - ALREADY EXISTS!

### Code Review Findings
- ✅ `gemini_service.py:1154-1210` has `store_evidence()`, `get_evidence()`, `list_evidence()`
- ✅ Evidence IDs are 8-char hex like `#7326d`
- ✅ Agent stores evidence with: `📎 Evidence #abc123 stored for: [claim]`
- ✅ User can say "show evidence #abc123" to retrieve
- ⚠️ Currently "evidence on demand" - only shown when user asks

### For Demo/Judges
Need to **surface evidence automatically** during demo, not hide it.

### Options
1. Add `PROXI_DEMO_MODE` flag → auto-display evidence in chat
2. Have agent call `list_evidence()` at end of each task
3. Add evidence panel to UI that auto-populates

### Image Size Concern (User Raised)
- Evidence may include screenshots → memory/latency issues
- Solution: Compress/resize images before sending to frontend
- Check `evidence['data'][:5000]` limit in code - may need to handle images separately

---

## 3. Mermaid Rendering - PARTIALLY FIXED

### Code Review Findings
- ✅ `MermaidDiagram.tsx` has try/catch with error fallback (lines 100-128)
- ✅ `sanitizeMermaidSyntax()` function cleans common LLM issues (lines 17-28)
- ✅ Shows error state with raw code if parse fails
- ⚠️ Still crashes on some complex syntax (user screenshot shows parse error)

### Problem
Current sanitizer only fixes parentheses in quoted strings. LLM generates other invalid patterns.

### Solution Options
1. **Enhance sanitizer** - Add more pattern fixes
2. **Server-side PNG** - User mentioned PNG feature exists, need to check
3. **Stricter prompt** - Tell LLM to use simple Mermaid syntax only

### Check
- Look for PNG/image generation for Mermaid in backend
- May already exist as `send_file_to_mobile()` or similar

---

## 4. Judge Trust Problem

### Problem
Judges use magic link, see Proxi chat UI, but can't verify if:
- Proxi is actually executing commands
- Or just returning scripted responses

### User's Video Plan
- **Split-screen recording**: Mobile (left) + Desktop (right)
- Judges see correlation between voice command and desktop action
- This solves trust for video submission

### For Live Demo (magic link)
- Use existing evidence feature (#ID system)
- Configure to auto-show evidence during demo
- Keep images small to avoid latency

### Recommendation
1. **Video**: Split-screen recording (user's plan) ✅
2. **Live**: Auto-display evidence with small thumbnails
3. **Don't need**: RDP/SSH access for judges

---

## 5. Demo Apps (CRM/Pricing) - PRIORITY

### Current State
- `demo/pricing-tool.html` (10KB static HTML)
- `demo/crm.html` (22KB static HTML)
- Static files, no interactivity, looks fake

### User Requirements
1. **Functional web app** with JSON backend (like real CRMs)
2. **Multiple tabs** - Proxi must navigate, not find everything on front page
3. **Dummy data** for multiple clients
4. **Test navigation tools** - Agent struggled in last test
5. **Use system-first approach**: pywinauto/Windows automation, then vision if needed

### Architecture
```
demo-apps/
├── server.py              # Flask, port 5050
├── static/
│   └── style.css          # Corporate theme
├── templates/
│   ├── pricing/
│   │   ├── dashboard.html
│   │   ├── clients.html   # Tab: Client list
│   │   ├── products.html  # Tab: Product catalog
│   │   └── quotes.html    # Tab: Quote builder
│   └── crm/
│       ├── dashboard.html
│       ├── contacts.html  # Tab: Contact list
│       ├── deals.html     # Tab: Deal pipeline
│       └── activities.html
└── data/
    ├── pricing.json       # Product prices, margins
    └── customers.json     # Customer records
```

### Navigation Tools Available (from code review)
- `focus_window(title)` - Bring window to front
- `browser_command(action, url)` - NEW_TAB, NAVIGATE, SEARCH, etc.
- `click_at(x, y)` - Direct click
- `type_text(text)` - Keyboard input
- `scan_ui_tree()` - Get UI elements via pywinauto
- `get_observation()` - Screenshot + SoM overlay

### Story Angle
> "Sarah has read-only console access to a legacy Oracle pricing system. No API. She copies numbers to Excel manually every week."

---

## 6. Command Guard Safety - DOCUMENT FOR PRESENTATION

### Code Review Findings
- ✅ `command_guard.py` is comprehensive (682 lines)
- ✅ Three tiers: BLOCKED (always denied), NEEDS_APPROVAL (user must confirm), SAFE (auto-run)
- ✅ Covers: file ops, privilege escalation, network attacks, registry, disk ops
- ✅ `FileGuard` protects sensitive paths (.env, .ssh, system files)
- ✅ `PROXI_DEV_MODE=true` bypasses approvals for demo/testing

### For Presentation
Highlight this as **security differentiator**:
- "Proxi has 70+ blocked command patterns"
- "Destructive commands require human approval"
- "Protected paths can never be deleted"

### User Override via ! Prefix (New Feature Request)
Allow users to run blocked commands manually:
- User types `!rm -rf /tmp/test` → bypasses LLM restriction
- LLM still can't run it, but human can override
- Keeps LLM safe while allowing power users flexibility

### Implementation
- Check if message starts with `!`
- If yes, execute directly without command_guard check
- Log with `[USER_OVERRIDE]` tag

## 7. Landing Page Polish

### TODO
- [ ] Embed 3-minute video in hero section
- [ ] Add Gemini 3 features one-liner
- [ ] Architecture diagram (PNG/SVG)
- [ ] "For Judges" quick-start section

---

## 8. Demo Video Structure (3 minutes)

### Option A: Single Hero Demo (Recommended)
```
0:00-0:10  Hook: "What if your phone could control your desktop?"
0:10-1:40  Sales Emergency demo (voice command, legacy app, PPT creation)
1:40-2:00  Show verification evidence + artifacts
2:00-2:30  Quick SOC demo montage (multi-desktop switching)
2:30-2:50  Architecture diagram + Gemini features
2:50-3:00  Call to action: "Try it live at proxi.audista.com"
```

### Recording Setup
- Left: Mobile phone screen (portrait)
- Right: Windows desktop (landscape)
- Narration: Explain what's happening

---

## Open Questions (Updated)

1. ~~**Verification UI**: Badge inline vs collapsible panel?~~ → Use existing evidence system
2. ~~**Evidence storage**: Where to persist artifacts?~~ → Already in memory (`evidence_store` dict)
3. ~~**Demo apps**: Flask server or static files?~~ → Flask with JSON backend
4. ~~**Mermaid**: Client or server?~~ → Client-side exists, enhance error handling
5. **NEW**: Should `!` prefix bypass blocked commands or just approval-required?
6. **NEW**: How to auto-show evidence in demo mode without cluttering mobile UI?

---

## Progress Log

| Date | Item | Change |
|------|------|--------|
| Jan 31 AM | Created tracker | Initial gaps identified |
| Jan 31 10:56 | Code review | Found existing evidence system, Mermaid handling, command_guard |
| Jan 31 10:56 | Priority shift | Demo apps now #1 priority (user feedback) |
| | | |

