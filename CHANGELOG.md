# Changelog

All notable changes to Proxi are documented in this file.

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
