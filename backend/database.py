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
