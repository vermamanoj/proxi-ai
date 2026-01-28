#!/usr/bin/env python3
"""
Set custom passwords for Proxi users.
Run: python set_password.py <username> <new_password>

Examples:
  python set_password.py demo MyDemo2026!
  python set_password.py admin SecureAdmin#99
  python set_password.py judge JudgePass$42
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

def main():
    if len(sys.argv) < 3:
        print("Usage: python set_password.py <username> <new_password>")
        print("\nAvailable users: demo, judge, admin")
        print("\nTip: Use passwords that are:")
        print("  - 8+ characters")
        print("  - Easy to type on mobile (avoid complex symbols)")
        print("  - Example: ProxiDemo2026 or JudgeAccess42")
        sys.exit(1)
    
    username = sys.argv[1]
    new_password = sys.argv[2]
    
    # Find users.json
    script_dir = Path(__file__).parent
    users_file = script_dir / "users.json"
    
    if not users_file.exists():
        print(f"Error: {users_file} not found")
        print("Run the backend once first to create default users")
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
