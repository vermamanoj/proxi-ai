# Proxi Hackathon Demo Script
## "The Million-Dollar Minute"

---

## Overview

**Scenario:** Sales rep Sarah is at a client's office negotiating a $2.3M deal. Competitor just undercut by 12%. She has 10 minutes to respond or lose the deal. She can't leave the room.

**Tagline:** *"Your desktop, in your pocket. For the moments that can't wait."*

---

## Demo Flow (~2 minutes)

### Setup
- Have mock legacy apps open on desktop (Pricing Tool + CRM)
- Have a brand template .pptx in Downloads folder (dated within last 7 days)
- Open Proxi on phone (or browser in mobile view)

### Step 1: Check Pricing System (20 sec)

**Voice:** *"I need the minimum margin we can offer for enterprise tier. Check our pricing system."*

**Proxi executes:**
- `look_at_screen()` → sees desktop
- `open_target()` or navigates to Pricing Tool window
- `look_at_screen()` → analyzes the legacy interface
- Clicks/types to navigate to Enterprise tier
- `share_screenshot()` → Shows result

**Proxi responds:** *"Minimum margin for Enterprise tier is 18%. Based on the $2.3M deal, you can go as low as $2.02M."*

---

### Step 2: Check Client History (25 sec)

**Voice:** *"What's this client's total purchase history with us? Check the CRM."*

**Proxi executes:**
- Opens/focuses legacy CRM window
- `look_at_screen()` → analyzes CRM interface
- Types client name in search
- `click_at()` → clicks search/view
- `share_screenshot()` → Shows customer record

**Proxi responds:** *"Acme Corp has purchased $4.7M over 3 years. They qualify for Platinum loyalty discount - additional 5% off."*

---

### Step 3: Find Brand Template (25 sec)

**Voice:** *"I downloaded our company's brand template a few days ago but forgot the name. Find PowerPoint files from the last 7 days in my Downloads folder and show me what you find."*

**Proxi executes:**
- `run_terminal_command()` → searches Downloads for recent .pptx files
- `share_screenshot()` → Shows list of files found

**Proxi responds:** *"I found 3 PowerPoint files from the last 7 days: 'TechSolutions_BrandTemplate_2026.pptx', 'Q1_Planning.pptx', and 'Meeting_Notes.pptx'. Which one is your brand template?"*

---

### Step 4: Create Business Case (30 sec)

**Voice:** *"Use the TechSolutions brand template. Create a business case slide justifying a lower margin for this deal."*

**Proxi executes:**
- `open_target()` → opens the brand template
- `ppt_add_slide()` → adds new slide
- `ppt_edit_text()` → adds title: "Strategic Deal Justification"
- `ppt_edit_text()` → adds content with key points:
  - Customer LTV: $4.7M
  - Minimum margin: 18%
  - Recommended price: $1.95M
  - Loyalty discount: 5%
- `ppt_save_presentation()` → saves to Desktop
- `share_screenshot()` → Shows completed slide

**Proxi responds:** *"Business case created using your brand template. Saved to Desktop as 'AcmeCorp_DealJustification.pptx'."*

---

### Step 5: Close (15 sec)

**Presenter:** *"Sarah shows the business case to her manager via screen share. Discount approved. Deal closed. All from her phone, without leaving the room."*

---

## Key Points for Judges

1. **No pre-scripting** - Proxi reasoned through unfamiliar UIs using vision
2. **Legacy systems** - SAP-like pricing tool and old CRM have no APIs
3. **Mobile-first** - Phone was the only interface available
4. **Time-critical** - 10-minute deadline, couldn't wait
5. **Real business value** - $2.3M deal saved
6. **File discovery** - Found forgotten file by searching recent downloads
7. **Document creation** - Built business case in PowerPoint on-the-fly
8. **Human-in-loop** - Asked user to confirm which template before proceeding

---

## Technical Capabilities Demonstrated

| Gemini 3 Feature | How Used |
|------------------|----------|
| Voice I/O | Natural language commands via Gemini Live |
| Vision | Analyzing legacy UI layouts |
| Reasoning | Figuring out how to navigate unknown software |
| Tool Calling | 30+ tools for OS control |
| Multimodal | Voice + Vision + Text in single flow |

---

## Fallback Responses

If something doesn't work perfectly:
- "Let me try another approach..." (shows adaptability)
- Manual intervention: "Proxi identified the data, let me click to confirm"

---

## Mock Apps Required

1. **Legacy Pricing Tool** - SAP-like interface with pricing tiers (`demo/pricing-tool.html`)
2. **Legacy CRM** - Old-school customer database with interactive tabs (`demo/crm.html`)
3. **Brand Template** - PowerPoint .pptx file in Downloads folder (use any branded template)

---

## What Makes This IMPOSSIBLE Without Proxi

| Alternative | Why It Fails |
|-------------|--------------|
| Call colleague | In meetings, don't know systems |
| Remote desktop | Can't navigate complex UIs on phone |
| RPA | Not pre-scripted for this request |
| ChatGPT/Claude | Can't access desktop |
| Leave the room | Lose the deal |

---

*Last Updated: January 27, 2026*

---

## 📊 Test Results (2026-01-27 02:49 AM)

### Test Scenario
User prompt: *"I am in client meeting I need some data from pricing tool and crm database. You will find links to these tools in desktop. I am in a deal closing situation, competition has given new quote which is lesser than us. I think we give new quote at 14% margin we might win. You need to find whats minimum margin allowed. Also if there is any approval needed then we will have to build business case. Check details of client acme corporation from crm and build a business case. Then put it into a PPT, there would be a brand related PPT that I downloaded today."*

### Execution Timeline

| Time | Action | Tool Used | Result |
|------|--------|-----------|--------|
| 02:49:41 | Scan desktop | `run_terminal_command` | Found pricing-tool.html, crm.html ✅ |
| 02:49:46 | Open Pricing Tool | `open_target` | Opened successfully ✅ |
| 02:49:50 | Analyze pricing UI | `look_at_screen` | Extracted margin rules ✅ |
| 02:50:08 | Open CRM | `open_target` | Opened successfully ✅ |
| 02:50:12 | Analyze CRM | `look_at_screen` | Found Acme Corp ✅ |
| 02:51:11 | Parallel open | `open_target` x2 | Both apps opened ✅ |
| 02:52:57 | Focus Pricing Tool | `open_target` | Navigated to approval section ✅ |
| 02:53:20 | Check PPT | `ppt_get_active_presentation` | Found brand template.pptx ✅ |
| 02:53:34 | Duplicate slide | `ppt_duplicate_slide` | Created slide 4 ✅ |
| 02:54:22 | Better layout | `ppt_delete_slide` + `ppt_duplicate_slide` | Used Slide 2 layout ✅ |
| 02:54:30 | Edit content | `ppt_edit_text` x2 | Title + bullets added ✅ |
| 02:54:47 | Verify | `look_at_screen` | Confirmed slide content ✅ |

### Data Extracted

**From Pricing Tool:**
- Minimum Margin: 18%
- Target Margin: 28%
- Policy: Deals below 15% require CFO approval
- Floor Price: $1,850.00/seat/year

**From CRM (Acme Corporation):**
- Client ID: CLI-4532
- Industry: Technology/Software
- Account Tier: Enterprise
- Loyalty Status: Platinum (3+ years, $3M+ lifetime)
- Lifetime Value: $4,700,000
- Account Manager: Sarah Johnson

### Output Generated

**Slide Title:** BUSINESS CASE: ACME RENEWAL

**Content:**
- Situation: Competitor undercutting pricing. High risk of churn.
- Client: Acme Corporation (Platinum Status).
- Value: $4.7M Lifetime Value, Strategic Partner.
- Proposal: Match pricing with 14% Margin.
- Policy Check: 14% is below 15% threshold.
- Requirement: CFO Approval Required.
- Recommendation: Approve exception to secure key account.

### Observations

1. **Vision Accuracy:** Correctly read data from both legacy-style web apps
2. **Intelligent Decisions:** System chose better slide layout autonomously (deleted Slide 3, used Slide 2)
3. **Session Recovery:** "Try again" command maintained context (1 history item preserved)
4. **Tool Orchestration:** 20+ tool calls coordinated smoothly
5. **Total Time:** ~5 minutes (includes one retry)

### Issues Noted
- First CRM lookup stalled briefly (needed "Try again")
- Window focus sometimes failed, system adapted by reopening apps

### Verdict: ✅ DEMO READY
