# 08 — Database

## Overview

Proxi uses **SQLite** with WAL (Write-Ahead Logging) mode for all persistent data storage. The database is managed by `backend/database.py` (322 lines) and stores missions, work items, chat sessions, and session images.

**File location**:
- Development: `backend/data/proxi.db` (or repo root)
- Docker: `/app/data/proxi.db` (mounted volume for persistence)

---

## Connection Configuration

```python
class Database:
    def __init__(self, db_path=None):
        self.db_path = db_path or self._default_db_path()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")       # Concurrent reads
        self.conn.execute("PRAGMA foreign_keys=ON")         # Enforce FK constraints
        self.conn.row_factory = sqlite3.Row                 # Dict-like row access
        self._create_tables()
```

**Key settings**:
- `check_same_thread=False` — Required for FastAPI's async context
- `journal_mode=WAL` — Allows concurrent reads during writes
- `foreign_keys=ON` — Enforces referential integrity

---

## Schema

### Table: `missions`

Stores Triple Handshake mission records.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID mission identifier |
| `goal` | TEXT | NOT NULL | Mission objective |
| `verification_criteria` | TEXT | | JSON string defining verification checks |
| `status` | TEXT | DEFAULT 'assigned' | `assigned`, `pending_verification`, `verified`, `failed`, `escalated` |
| `assigned_at` | TEXT | | ISO timestamp of creation |
| `completed_at` | TEXT | | ISO timestamp of completion |
| `execution_summary` | TEXT | | Agent's summary of what was done |
| `verification_result` | TEXT | | Result of verification check |
| `session_id` | TEXT | | Associated chat session |

### Table: `work_items`

Tracks individual work items within missions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID work item identifier |
| `mission_id` | TEXT | FOREIGN KEY → missions.id | Parent mission |
| `type` | TEXT | NOT NULL | Item type (e.g., "command", "file_op") |
| `source` | TEXT | | Origin of the work item |
| `attributes` | TEXT | | JSON string with item-specific data |
| `status` | TEXT | DEFAULT 'pending' | `pending`, `in_progress`, `completed`, `failed` |
| `created_at` | TEXT | | ISO timestamp |

### Table: `sessions`

Stores chat conversation sessions with full message history.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID session identifier |
| `title` | TEXT | DEFAULT 'New Session' | User-visible session name |
| `user_id` | TEXT | | Username who owns the session |
| `status` | TEXT | DEFAULT 'active' | `active`, `archived` |
| `messages` | TEXT | | JSON array of message objects |
| `goals` | TEXT | | JSON array of parsed goals from PLAN |
| `created_at` | TEXT | | ISO timestamp |
| `updated_at` | TEXT | | ISO timestamp (updated on each save) |

#### Message Format (within `messages` JSON)

```json
[
  {
    "role": "user",
    "content": "Kill the high-CPU process",
    "timestamp": "2026-02-10T14:00:00"
  },
  {
    "role": "assistant",
    "content": "I'll check system health first...",
    "timestamp": "2026-02-10T14:00:02",
    "tool_calls": [
      {"name": "get_system_health", "params": {}, "result": "..."}
    ]
  }
]
```

#### Goals Format (within `goals` JSON)

```json
[
  {"id": "G1", "title": "Check system health", "status": "completed", "result": "CPU at 99.8%"},
  {"id": "G2", "title": "Identify high-CPU process", "status": "completed", "result": "ffmpeg PID 1337"},
  {"id": "G3", "title": "Kill the process", "status": "active", "result": null}
]
```

### Table: `session_images`

Stores screenshots and uploaded images associated with sessions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID image identifier |
| `session_id` | TEXT | FOREIGN KEY → sessions.id | Parent session |
| `image_data` | TEXT | | Base64-encoded image data |
| `caption` | TEXT | | Description or context |
| `timestamp` | TEXT | | ISO timestamp |

---

## CRUD Operations

### Missions

```python
# Create
db.create_mission(mission_id, goal, verification_criteria, session_id)

# Read
mission = db.get_mission(mission_id)
missions = db.list_missions(session_id=session_id, status="assigned")

# Update
db.update_mission(mission_id, status="verified", verification_result="...")
db.update_mission_execution(mission_id, execution_summary="...", status="pending_verification")

# The mission lifecycle:
# create → update execution → update status (verified/failed/escalated)
```

### Sessions

```python
# Create
db.create_session(session_id, user_id, title="New Session")

# Read
session = db.get_session(session_id)           # Full session with messages
sessions = db.list_sessions(user_id)           # User's session list (no messages)

# Update
db.save_session(session_id, messages_json, goals_json)
db.update_session_title(session_id, new_title)

# Delete
db.delete_session(session_id)
```

### Session Images

```python
# Store
db.save_session_image(image_id, session_id, image_data_base64, caption)

# Retrieve
images = db.get_session_images(session_id)
```

---

## Schema Migrations

The database uses a simple additive migration pattern — new columns are added via `ALTER TABLE` with `try/except` to handle already-existing columns:

```python
def _create_tables(self):
    # Create base tables
    self.conn.execute("""
        CREATE TABLE IF NOT EXISTS missions (
            id TEXT PRIMARY KEY,
            goal TEXT NOT NULL,
            ...
        )
    """)

    # Additive migrations
    migrations = [
        "ALTER TABLE sessions ADD COLUMN goals TEXT DEFAULT '[]'",
        "ALTER TABLE sessions ADD COLUMN user_id TEXT DEFAULT ''",
        "ALTER TABLE missions ADD COLUMN session_id TEXT DEFAULT ''",
    ]
    for migration in migrations:
        try:
            self.conn.execute(migration)
        except sqlite3.OperationalError:
            pass  # Column already exists
```

This approach is simple and safe for a hackathon codebase — it never drops data and handles repeated runs gracefully.

---

## Session History Management

### Trimming

To prevent context window overflow, session history is trimmed before sending to Gemini:

```python
# In gemini_service.py
max_history = mode_config.get("session_history_size", 50)
if len(session_messages) > max_history:
    # Keep first 2 messages (system context) + last (max_history - 2)
    session_messages = session_messages[:2] + session_messages[-(max_history - 2):]
```

**Global default**: 50 messages (configurable in `modes.json` → `global.session_history_size`).

### Periodic Saves

During long-running chat interactions, sessions are saved to the database every 5 tool calls:

```python
# In main.py SSE handler
if event.get("type") == "tool_result":
    tool_count += 1
    if tool_count % 5 == 0:
        database.save_session(session_id, messages, goals)
```

This prevents data loss if the server crashes mid-conversation.

### Session Resume

If a previous response was interrupted, the user can type "continue" and the system detects it:

```python
if user_message.lower().strip() in ["continue", "go on", "keep going"]:
    # Inject special prompt: "Continue from where you left off"
    # Load last partial response from session
```

---

## Data Lifecycle

```
Session Created (user starts chat)
    │
    ├─ Messages appended (each user/assistant turn)
    ├─ Goals parsed from PLAN_START/PLAN_END blocks
    ├─ Images saved (screenshots, uploads)
    ├─ Missions created/updated (Triple Handshake)
    │
    ├─ Periodic saves every 5 tool calls
    │
    └─ Session persisted on stream completion
        │
        ├─ User can list/rename/delete sessions
        └─ Sessions survive server restarts
```

---

## Separate Storage Systems

Note that authentication data uses **separate JSON files**, not SQLite:

| Data | Storage | File |
|------|---------|------|
| Users | JSON | `backend/auth/users.json` |
| Sessions (auth) | JSON | `backend/auth/sessions.json` |
| Magic Links | JSON | `backend/auth/magic_links.json` |
| Login Events | JSON | `backend/auth/login_events.json` |
| Workstations | JSON | `backend/registry/workstations.json` |
| Chat sessions + missions | SQLite | `data/proxi.db` |

This split is historical — auth was implemented before the SQLite database was added. Consolidation is a potential post-hackathon improvement.

---

## Backup & Recovery

### Docker Volume

In docker compose, the data directory is mounted as a volume:

```yaml
volumes:
  - ./data:/app/data    # SQLite database
  - ./.env:/app/.env    # Environment variables
```

### Manual Backup

```powershell
# Windows
Copy-Item data\proxi.db data\proxi_backup_$(Get-Date -Format 'yyyyMMdd').db

# Linux
cp data/proxi.db data/proxi_backup_$(date +%Y%m%d).db
```

### WAL Recovery

If the database is corrupted, WAL recovery can be attempted:

```python
import sqlite3
conn = sqlite3.connect("data/proxi.db")
conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
conn.close()
```

---

*Previous: [Prompt Engineering ←](07_prompt_engineering.md) | Next: [Deployment →](09_deployment.md)*
