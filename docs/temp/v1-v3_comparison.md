V1 (App.tsx) vs V3 (AppV3.tsx) - Feature Comparison
📊 Overview
Metric	V1	V3
Lines	905	762 (after fix)
Layout	Single column, centered	Sidebar + main
Components	15 imported	10 imported
✅ Features Present in BOTH
Feature	Notes
Authentication flow	Landing → Login → App
useProxiBrain hook	Text/vision commands
useGeminiLive hook	Voice I/O
useWorkstations hook	Agent selection
ChatView	Message display
MissionPanelCollapsible	Goal tracking
ApprovalModal	Action approvals
Image staging	Camera/file upload
Mode selector	Quick/Balanced/Deep/Plan
Audio toggle	TTS on/off
❌ Features MISSING in V3
Feature	V1 Location	Impact
useBackendHealth	Line 116	No backend status indicator
Debug Logs Toggle	Lines 191-218	Can't see thinking/verbose
EscalationAlert	Lines 651-673	No "agent needs help" UI
ApprovalCard (inline)	Lines 636-648	Only modal, no inline
SessionHistory panel	Lines 868-883	Sidebar lists but can't load
AdminPanel	Lines 885-888	No magic link management
MobileMenu	Lines 492-508	No hamburger menu
Continue button	Lines 771-779	No "stalled" recovery UI
Floating New Session	Lines 890-898	No quick reset button
Voice viz bars	Lines 838-860	No animated volume bars
Settings drawer	Lines 511-621	No settings panel
Magic link handling	Lines 32-49	No ?magic= URL parsing

as on 01-feb-26
