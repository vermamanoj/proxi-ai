#!/usr/bin/env python3
"""Upgrade user passwords from SHA-256 to bcrypt format."""
import sys
sys.path.insert(0, '/app')

import bcrypt
from backend.auth.auth_service import AuthService

def main():
    auth = AuthService()
    
    # Upgrade all user passwords to bcrypt
    passwords = {
        'demo': 'demo123',
        'judge': 'judge2026',
        'admin': 'admin_secure_2026'
    }
    
    for username, password in passwords.items():
        if username in auth.users:
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            auth.users[username].password_hash = hashed.decode('utf-8')
            print(f"✓ Upgraded {username} to bcrypt")
    
    auth._save_users()
    print("\n✅ All passwords upgraded successfully!")
    
    # Verify the upgrade
    print("\n🔍 Verifying passwords...")
    for username, password in passwords.items():
        if auth.verify_password(username, password):
            print(f"✓ {username} login works")
        else:
            print(f"✗ {username} login FAILED")

if __name__ == "__main__":
    main()
