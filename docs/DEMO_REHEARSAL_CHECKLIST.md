# Proxi Demo Rehearsal Checklist

## Pre-Demo Setup

### 1. Start All Services
```powershell
# Check Docker containers are running
docker ps

# Expected containers:
# - proxi-ai-core-1 (port 4000)
# - proxi-ai-frontend-1 (port 4002)
# - proxi-ai-agent-1 (port 4001)
# - proxi-ai-forensic-investigation-1 (port 5081)

# Start Windows agent (from proxi-win-agent folder)
cd E:\data\proxi-win-agent
.\venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8081
```

### 2. Start Demo Apps
```powershell
# In separate terminals:
cd E:\data\proxi-ai\demo-apps\pricing-app
npm start

cd E:\data\proxi-ai\demo-apps\crm-app
npm start
```

### 3. Verify Access
- [ ] Frontend: http://localhost:4002
- [ ] Core API: http://localhost:4000/api/health
- [ ] Linux Agent: http://localhost:4001/health
- [ ] Windows Agent: http://localhost:8081/health

---

## Demo Scenario 1: Sales Emergency (Primary)

### Story
> "Sarah is a Sales Manager at TechSolutions. She's about to board a flight but just got a call - ACME Corp's CEO wants updated pricing for their renewal meeting in 2 hours."

### Test Steps

#### Phase 1: Voice Command
- [ ] Open Proxi on mobile (http://proxi.audista.com or localhost:4002)
- [ ] Login with magic link
- [ ] Say: "I need the current pricing for ACME Corporation from our pricing system"

#### Phase 2: Navigate Legacy App
- [ ] Verify Proxi brings Pricing App to foreground
- [ ] Verify Proxi navigates to Clients tab
- [ ] Verify Proxi finds ACME Corporation
- [ ] Check: Agent reads pricing data ($2,082.50/seat, 15% discount, 750 seats)

#### Phase 3: Create PowerPoint
- [ ] Say: "Create a PowerPoint proposal with this pricing and a 20% renewal discount"
- [ ] Verify PPT opens and slides are created
- [ ] Check: Title slide, pricing slide, discount slide

#### Phase 4: Evidence & Verification
- [ ] Check: Evidence cards appear in chat (📎 Evidence #xxx)
- [ ] Expand evidence to see screenshot/data
- [ ] Verify Triple Handshake completed (if thorough mode)

### Expected Duration: ~90 seconds

---

## Demo Scenario 2: SOC Training (Secondary)

### Story
> "Train new SOC analysts by investigating a simulated breach in a sandboxed environment."

### Test Steps

#### Phase 1: Connect to Forensic Container
- [ ] Say: "Connect to the Linux forensic container"
- [ ] Verify agent switch notification appears

#### Phase 2: Investigation Commands
- [ ] Say: "Check for suspicious processes and network connections"
- [ ] Verify terminal commands execute (ps, netstat, ss)
- [ ] Check: Output appears in chat

#### Phase 3: Multi-Desktop Switch
- [ ] Say: "Now check the Windows server for related activity"
- [ ] Verify smooth agent switch
- [ ] Verify Windows commands execute

#### Phase 4: Generate Report
- [ ] Say: "Generate a Mermaid diagram of the attack chain"
- [ ] Verify diagram renders (no parse errors)
- [ ] Check: Diagram is expandable/zoomable

### Expected Duration: ~60 seconds

---

## Feature Verification Checklist

### Navigation Tools
- [ ] `focus_window()` brings correct app to front
- [ ] `scan_ui_tree()` detects Electron app elements
- [ ] `click_at()` clicks correct positions
- [ ] `browser_command()` works (NEW_TAB, NAVIGATE)

### Security Features
- [ ] Blocked command rejected (try: `!rm -rf /`)
- [ ] Approval-required command prompts user
- [ ] Safe command auto-executes
- [ ] `!` prefix bypasses approval (not blocked)

### UI Features
- [ ] Evidence cards render inline
- [ ] Evidence expands/collapses on click
- [ ] Mermaid diagrams render without errors
- [ ] Agent switch notifications appear
- [ ] Processing indicator shows during execution

### Voice Features
- [ ] Microphone activates on button press
- [ ] Voice transcription appears
- [ ] Response is spoken back (if enabled)

---

## Recording Setup (Split-Screen)

### OBS Configuration
1. **Scene 1: Split View**
   - Left: Phone screen capture (portrait, 40% width)
   - Right: Desktop screen capture (landscape, 60% width)

2. **Audio Sources**
   - Microphone (voice commands)
   - Desktop audio (optional)

3. **Overlays**
   - "LIVE" indicator (optional)
   - Proxi logo watermark (corner)

### Recording Tips
- Start recording BEFORE starting demo
- Leave 2-3 seconds pause between actions for clarity
- Narrate what you're doing
- Keep total under 3 minutes
- Have backup recording in case of errors

---

## Troubleshooting

### Agent Not Responding
```powershell
# Check agent health
curl http://localhost:8081/health

# Check Core can reach agent
curl http://localhost:4000/api/workstations
```

### Electron App Not Detected
```python
# Test pywinauto detection
from pywinauto import Desktop
desktop = Desktop(backend='uia')
print([w.window_text() for w in desktop.windows()])
```

### Evidence Not Showing
- Ensure agent is using `store_evidence()` tool
- Check message content for `📎 Evidence #` marker

### Mermaid Errors
- Check console for parse errors
- Try simpler diagram syntax
- Sanitizer handles most issues automatically

---

## Final Checks Before Recording

- [ ] All services running
- [ ] Demo apps open and visible
- [ ] Phone connected to same network
- [ ] Voice working (test with simple command)
- [ ] Screen recording software ready
- [ ] Quiet environment for audio
- [ ] Browser cache cleared (fresh state)
- [ ] Session logged out (start fresh)

---

*Good luck with the demo! 🚀*
