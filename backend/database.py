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
    
    # Missions Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS missions (
            id TEXT PRIMARY KEY,
            goal TEXT,
            status TEXT,
            created_at TIMESTAMP
        )
    ''')
    
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
    log_system("Memory DB Initialized", "DB")

def create_mission_record(mission_id: str, goal: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO missions (id, goal, status, created_at) VALUES (?, ?, ?, ?)",
              (mission_id, goal, "ACTIVE", datetime.datetime.now()))
    conn.commit()
    conn.close()

def add_work_item_record(mission_id: str, item_type: str, source: str, attributes: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Ensure attributes are JSON string
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
