import sqlite3
import json
import datetime
from pathlib import Path
from backend.utils.logger import log_system

DB_PATH = Path("proxi_memory.db")

def init_db():
    """Initialize the SQLite database with missions and work_items tables."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Missions Table - NOW WITH VERIFICATION COLUMNS
    c.execute('''
        CREATE TABLE IF NOT EXISTS missions (
            id TEXT PRIMARY KEY,
            goal TEXT,
            status TEXT,
            created_at TIMESTAMP,
            verification_criteria TEXT,
            verification_status TEXT,
            logs_summary TEXT
        )
    ''')
    
    # Schema Migration for existing DBs (Idempotent)
    try:
        c.execute("ALTER TABLE missions ADD COLUMN verification_criteria TEXT")
    except sqlite3.OperationalError: pass
    try:
        c.execute("ALTER TABLE missions ADD COLUMN verification_status TEXT")
    except sqlite3.OperationalError: pass
    try:
        c.execute("ALTER TABLE missions ADD COLUMN logs_summary TEXT")
    except sqlite3.OperationalError: pass
    
    # Work Items Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS work_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mission_id TEXT,
            type TEXT,
            source TEXT,
            status TEXT,
            attributes TEXT,
            FOREIGN KEY(mission_id) REFERENCES missions(id)
        )
    ''')
    
    # Sessions Table - For chat history and goal tracking
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            status TEXT DEFAULT 'active',
            requirements TEXT,
            goals TEXT,
            messages TEXT
        )
    ''')
    
    # Migration: Add user_id column if missing
    try:
        c.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT")
    except sqlite3.OperationalError: pass
    
    conn.commit()
    conn.close()
    log_system("Memory DB Initialized (Verifiable Agent Schema)", "DB")

def create_mission_record(mission_id: str, goal: str, criteria: dict = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    criteria_json = json.dumps(criteria) if criteria else "{}"
    c.execute("INSERT INTO missions (id, goal, status, created_at, verification_criteria, verification_status) VALUES (?, ?, ?, ?, ?, ?)",
              (mission_id, goal, "ACTIVE", datetime.datetime.now(), criteria_json, "PENDING"))
    conn.commit()
    conn.close()

def update_mission_verification(mission_id: str, status: str, summary: str = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if summary:
        c.execute("UPDATE missions SET verification_status = ?, logs_summary = ? WHERE id = ?", (status, summary, mission_id))
    else:
        c.execute("UPDATE missions SET verification_status = ? WHERE id = ?", (status, mission_id))
    conn.commit()
    conn.close()

def get_mission_record(mission_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM missions WHERE id = ?", (mission_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def add_work_item_record(mission_id: str, item_type: str, source: str, attributes: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    attr_json = json.dumps(attributes)
    c.execute("INSERT INTO work_items (mission_id, type, source, status, attributes) VALUES (?, ?, ?, ?, ?)",
              (mission_id, item_type, source, "NEW", attr_json))
    item_id = c.lastrowid
    conn.commit()
    conn.close()
    return item_id

def get_missions_list():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM missions ORDER BY created_at DESC")
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows

def get_mission_items_list(mission_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM work_items WHERE mission_id = ?", (mission_id,))
    rows = []
    for row in c.fetchall():
        d = dict(row)
        try:
            d['attributes'] = json.loads(d['attributes'])
        except:
            d['attributes'] = {}
        rows.append(d)
    conn.close()
    return rows

def update_item_status_record(item_id: int, status: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE work_items SET status = ? WHERE id = ?", (status, item_id))
    conn.commit()
    conn.close()

# ============== SESSION MANAGEMENT ==============

def create_session(session_id: str, title: str = None, user_id: str = None):
    """Create a new session with optional user association."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.datetime.now()
    c.execute(
        "INSERT INTO sessions (id, user_id, title, created_at, updated_at, status, requirements, goals, messages) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (session_id, user_id, title or "New Session", now, now, "active", "[]", "[]", "[]")
    )
    conn.commit()
    conn.close()
    return session_id

def get_session(session_id: str):
    """Get a session by ID."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = c.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d['requirements'] = json.loads(d['requirements'] or '[]')
        d['goals'] = json.loads(d['goals'] or '[]')
        d['messages'] = json.loads(d['messages'] or '[]')
        return d
    return None

def update_session(session_id: str, title: str = None, requirements: list = None, goals: list = None, messages: list = None, status: str = None):
    """Update session data."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    updates = ["updated_at = ?"]
    values = [datetime.datetime.now()]
    
    if title is not None:
        updates.append("title = ?")
        values.append(title)
    if requirements is not None:
        updates.append("requirements = ?")
        values.append(json.dumps(requirements))
    if goals is not None:
        updates.append("goals = ?")
        values.append(json.dumps(goals))
    if messages is not None:
        updates.append("messages = ?")
        values.append(json.dumps(messages))
    if status is not None:
        updates.append("status = ?")
        values.append(status)
    
    values.append(session_id)
    c.execute(f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?", values)
    conn.commit()
    conn.close()

def append_session_message(session_id: str, message: dict):
    """Append a message to session history."""
    session = get_session(session_id)
    if session:
        messages = session['messages']
        messages.append(message)
        update_session(session_id, messages=messages)

def append_session_goal(session_id: str, goal: dict):
    """Append a goal to session."""
    session = get_session(session_id)
    if session:
        goals = session['goals']
        goals.append(goal)
        update_session(session_id, goals=goals)

def update_session_goal(session_id: str, goal_id: str, status: str, result: str = None):
    """Update a goal's status."""
    session = get_session(session_id)
    if session:
        goals = session['goals']
        for g in goals:
            if g.get('id') == goal_id:
                g['status'] = status
                if result:
                    g['result'] = result
                break
        update_session(session_id, goals=goals)

def get_sessions_list(limit: int = 20, user_id: str = None):
    """Get recent sessions, optionally filtered by user."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if user_id:
        c.execute("SELECT id, user_id, title, created_at, updated_at, status FROM sessions WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?", (user_id, limit))
    else:
        c.execute("SELECT id, user_id, title, created_at, updated_at, status FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows

def close_session(session_id: str):
    """Mark session as closed."""
    update_session(session_id, status="closed")
