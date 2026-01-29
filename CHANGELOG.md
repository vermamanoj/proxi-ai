# Changelog

All notable changes to Proxi are documented in this file.

## [2.5.0] - January 29, 2026

### Security
- **API Authentication**: All sensitive endpoints now require authentication
  - Chat, vision, sessions, missions, images, workstations
  - Admin-only: workstation registration/deletion, magic link management
- **Cloudflare Protection**: Bot challenge provides additional layer of defense

### Added
- **Windows Agent Script**: `scripts/register-windows-agent.ps1` for simplified setup
- **Mobile Camera**: Camera button now opens actual camera (not just gallery) via `capture="environment"`

### Changed
- **Mobile UX Simplified**: Removed Chat/Remote toggle - always Remote mode with Linux sandbox default
- **New Session Button**: Moved outside hamburger menu to main header
- **Settings Drawer**: Removed redundant mode details

### Fixed
- **Mobile Scroll**: Chat no longer auto-scrolls when user is reading history
- **Mobile Layout**: Uses `100dvh` for proper viewport on mobile browsers

### Documentation
- Updated Windows agent setup with Tailscale instructions
- Added workstations.json key/id matching requirement

---

## [2.4.0] - January 28, 2026

### Added
- **Multiline Input**: Textarea with Shift+Enter for newlines, Enter to submit
- **SQLite WAL Mode**: Concurrent database access with 30s timeout

### Changed
- **Default Agent Selection**: Improved priority (online default > default > online > first)
- **Session Creation**: Uses INSERT OR IGNORE to prevent UNIQUE constraint errors

### Fixed
- **Database Locked**: WAL mode + centralized `get_connection()` prevents concurrent access errors
- **Mission Panel**: Now receives full logs (not filtered) for proper goal extraction

---

## [2.3.0] - January 28, 2026

### Added
- **Remember Me**: Login checkbox for 24-hour sessions
- **Image Storage API**: Upload/retrieve session screenshots (`/api/sessions/{id}/images`)
- **Collapsible Mission Panel**: Horizontal stepper for mobile with expandable sections
- **Session Images Table**: SQLite storage for screenshots and user photos

### Changed
- **Session Timeout**: Extended from 1 hour to 6 hours default
- **Approval Modal**: Compact layout with scrollable description for long commands
- **Default Agent**: Linux Sandbox now auto-selected on startup
- **Stale Session Cleanup**: localStorage logs expire after 1 hour of inactivity

### Fixed
- **Container Crash**: Added missing `Path` import in main.py
- **Goal Tracking**: String ID matching for consistent goal updates
- **Cancel Task**: Now marks ALL remaining goals as failed (not just first)
- **Log Panel Scroll**: No longer auto-scrolls when user is reading history
- **Agent Selector**: Fixed `is_default` → `isDefault` field mapping

---

## [2.2.0] - January 2026

### Fixed
- **SDK Stability**: Reverted from experimental `google-genai` SDK to stable `google-generativeai` SDK
- **Tool Execution**: Fixed tool name mismatch causing "Tool not found" errors
- **Streaming**: Fixed empty candidates causing "list index out of range" errors
- **Transparency**: Agent now explains reasoning before every tool call

### Added
- **Transparency Protocol**: System instruction requires agent to explain WHAT, WHY, and expected outcome before each action
- **User Guide**: Comprehensive `USER_GUIDE.md` with usage documentation
- **Environment Template**: `.env.example` for easier setup
- **Improved Deployment**: Enhanced `deploy.sh` with better error handling and status messages

### Changed
- **Documentation**: Complete rewrite of `BLUEPRINT.md` and `README.md`
- **Windows Setup**: Updated `setup_windows.ps1` with correct SDK packages
- **Docker Compose**: Added `RUNTIME_MODE` environment variable and restart policies

### Technical Details
- Models: `gemini-2.0-flash` (fast), `gemini-2.5-pro-preview-06-05` (deep)
- SDK: `google-generativeai>=0.8.0`
- 25 registered tools across system, desktop, and integration categories

---

## [2.1.0] - January 2026

### Added
- **Verifiable Agent Architecture**: Triple Handshake Protocol (Assign → Execute → Verify)
- **Truth Layer**: Independent verification of task completion
- **Mock Desktop Service**: Safe demo mode for hackathon judges
- **Factory Pattern**: `RUNTIME_MODE` switch between DEMO and REAL
- **Mission Database**: SQLite storage for mission tracking
- **Neural Trace**: Real-time visualization of agent thoughts

### Changed
- Migrated to new SDK architecture (later reverted in 2.2.0)
- Added streaming NDJSON protocol for real-time updates

---

## [2.0.0] - December 2025

### Added
- **Desktop Control**: PyAutoGUI + PyWinAuto integration
- **Vision API**: Screenshot analysis via Gemini Vision
- **Voice Interface**: Gemini Live WebRTC integration
- **Mobile Telepresence**: Access from any browser

### Infrastructure
- FastAPI backend with async streaming
- React + Vite frontend
- Docker Compose deployment
- Nginx reverse proxy configuration

---

## [1.0.0] - November 2025

### Initial Release
- Basic chat interface
- Simple tool execution
- GitHub integration tools
