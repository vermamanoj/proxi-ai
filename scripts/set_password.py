#!/usr/bin/env python3
"""
Set custom passwords for Proxi users.

Run from project root (host machine, NOT inside Docker):
  python scripts/set_password.py <username> <new_password>

Examples:
  python scripts/set_password.py demo ProxiDemo2026
  python scripts/set_password.py admin SecureAdmin99
  python scripts/set_password.py judge JudgeAccess42

Password is saved to: backend/auth/users.json
(This file is volume-mounted into the core container)
"""

import sys
import os
import json
import hashlib
from pathlib import Path

def hash_password(password: str) -> str:
    """Hash password using same method as auth_service."""
    salt = "proxi_hackathon_salt_2026"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

def find_users_file() -> Path:
    """Find users.json relative to script location."""
    script_dir = Path(__file__).parent
    # Script is in /scripts, users.json is in /backend/auth
    project_root = script_dir.parent
    return project_root / "backend" / "auth" / "users.json"

def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/set_password.py <username> <new_password>")
        print("\nAvailable users: demo, judge, admin")
        print("\nTip: Use passwords that are:")
        print("  - 8+ characters")
        print("  - Easy to type on mobile (avoid complex symbols)")
        print("  - Example: ProxiDemo2026 or JudgeAccess42")
        sys.exit(1)
    
    username = sys.argv[1]
    new_password = sys.argv[2]
    
    # Find users.json
    users_file = find_users_file()
    
    if not users_file.exists():
        print(f"Error: {users_file} not found")
        print("Run the backend once first to create default users:")
        print("  docker compose up core -d")
        sys.exit(1)
    
    # Load users
    with open(users_file, 'r') as f:
        users = json.load(f)
    
    if username not in users:
        print(f"Error: User '{username}' not found")
        print(f"Available users: {', '.join(users.keys())}")
        sys.exit(1)
    
    # Update password hash
    users[username]["password_hash"] = hash_password(new_password)
    
    # Save users
    with open(users_file, 'w') as f:
        json.dump(users, f, indent=2)
    
    print(f"✅ Password updated for '{username}'")
    print(f"   New password: {new_password}")
    print("\n⚠️  Restart the backend for changes to take effect:")
    print("   docker compose restart core")

if __name__ == "__main__":
    main()
