# Proxi Hackathon Demo Script
## "The Million-Dollar Minute"

---

## Overview

**Scenario:** Sales rep Sarah is at a client's office negotiating a $2.3M deal. Competitor just undercut by 12%. She has 10 minutes to respond or lose the deal. She can't leave the room.

**Tagline:** *"Your desktop, in your pocket. For the moments that can't wait."*

---

## Demo Flow (90 seconds)

### Setup
- Have mock legacy apps open on desktop (Pricing Tool + CRM)
- Have a Word doc with a proposal open
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

### Step 3: Update Proposal (30 sec)

**Voice:** *"Update my proposal document - change the price to $1.95M and add a note about the loyalty discount."*

**Proxi executes:**
- Opens/focuses Word document
- `look_at_screen()` → finds price field
- Selects and updates price to $1.95M
- Adds text about loyalty discount justification
- Saves document (Ctrl+S)
- `share_screenshot()` → Shows updated proposal

**Proxi responds:** *"Proposal updated with new price of $1.95M and loyalty discount note. Document saved."*

---

### Step 4: Close (15 sec)

**Presenter:** *"Sarah shows the updated proposal. Deal closed. All from her phone, without leaving the room."*

---

## Key Points for Judges

1. **No pre-scripting** - Proxi reasoned through unfamiliar UIs using vision
2. **Legacy systems** - SAP-like pricing tool and old CRM have no APIs
3. **Mobile-first** - Phone was the only interface available
4. **Time-critical** - 10-minute deadline, couldn't wait
5. **Real business value** - $2.3M deal saved
6. **Verification** - Screenshots proved each step worked

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

1. **Legacy Pricing Tool** - SAP-like interface with pricing tiers
2. **Legacy CRM** - Old-school customer database with search
3. **Proposal Document** - Word doc with editable price field

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

*Last Updated: January 2026*
