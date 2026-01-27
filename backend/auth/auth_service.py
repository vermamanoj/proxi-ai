"""
Authentication Service for Proxi

Provides simple session-based authentication for hackathon demo.
NOT suitable for production - use proper IAM/OAuth in production.
"""

import hashlib
import secrets
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class User:
    username: str
    password_hash: str
    display_name: str
    role: str = "user"  # user, admin, judge
    created_at: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Session:
    session_id: str
    username: str
    created_at: datetime
    expires_at: datetime
    ip_address: str = ""
    user_agent: str = ""
    
    def is_valid(self) -> bool:
        return datetime.utcnow() < self.expires_at


class AuthService:
    """
    Simple authentication service with local user storage.
    """
    
    def __init__(self, users_file: str = None, session_timeout_minutes: int = 30):
        self.users_file = users_file or self._default_users_file()
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.sessions: Dict[str, Session] = {}
        self._load_users()
    
    def _default_users_file(self) -> str:
        """Get default path for users file."""
        backend_dir = Path(__file__).parent.parent
        return str(backend_dir / "auth" / "users.json")
    
    def _load_users(self):
        """Load users from JSON file."""
        self.users: Dict[str, User] = {}
        
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as f:
                    data = json.load(f)
                    for username, user_data in data.items():
                        self.users[username] = User(**user_data)
            except Exception as e:
                print(f"[AUTH] Error loading users: {e}")
        else:
            # Create default demo users
            self._create_default_users()
    
    def _save_users(self):
        """Save users to JSON file."""
        os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
        data = {username: user.to_dict() for username, user in self.users.items()}
        with open(self.users_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _generate_secure_password(self, length: int = 16) -> str:
        """Generate a cryptographically secure random password."""
        import string
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def _create_default_users(self):
        """Create default demo users with random passwords on first run."""
        default_users = [
            ("demo", "Demo User", "user"),
            ("judge", "Hackathon Judge", "judge"),
            ("admin", "Administrator", "admin"),
        ]
        
        print("\n" + "="*60)
        print("  🔐 PROXI FIRST RUN - DEFAULT CREDENTIALS")
        print("="*60)
        print("  Save these passwords! They are shown only once.")
        print("-"*60)
        
        generated_creds = []
        for username, display_name, role in default_users:
            password = self._generate_secure_password()
            self.create_user(username, password, display_name, role)
            generated_creds.append((username, password))
            print(f"  {username:10} | {password}")
        
        print("-"*60)
        print(f"  Stored in: {self.users_file}")
        print("  To reset: delete users.json and restart")
        print("="*60 + "\n")
        sys.stdout.flush()
        
        # Write credentials file for Docker environments (stdout may not be visible)
        creds_file = os.path.join(os.path.dirname(self.users_file), "INITIAL_CREDENTIALS.txt")
        with open(creds_file, 'w') as f:
            f.write("PROXI INITIAL CREDENTIALS\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}\n")
            f.write("DELETE THIS FILE after noting passwords!\n")
            f.write("-" * 40 + "\n")
            for username, password in generated_creds:
                f.write(f"{username:10} | {password}\n")
            f.write("-" * 40 + "\n")
        print(f"  Credentials also saved to: {creds_file}")
        sys.stdout.flush()
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256 with salt."""
        # In production, use bcrypt or argon2
        salt = "proxi_hackathon_salt_2026"
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    
    def _generate_session_id(self) -> str:
        """Generate a secure random session ID."""
        return secrets.token_hex(32)
    
    def create_user(self, username: str, password: str, display_name: str, role: str = "user") -> User:
        """Create a new user."""
        user = User(
            username=username,
            password_hash=self._hash_password(password),
            display_name=display_name,
            role=role,
            created_at=datetime.utcnow().isoformat()
        )
        self.users[username] = user
        self._save_users()
        return user
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user by username and password."""
        user = self.users.get(username)
        if not user:
            return None
        
        if user.password_hash != self._hash_password(password):
            return None
        
        return user
    
    def create_session(self, username: str, ip_address: str = "", user_agent: str = "") -> Session:
        """Create a new session for a user."""
        session_id = self._generate_session_id()
        now = datetime.utcnow()
        
        session = Session(
            session_id=session_id,
            username=username,
            created_at=now,
            expires_at=now + self.session_timeout,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.sessions[session_id] = session
        return session
    
    def validate_session(self, session_id: str) -> Optional[Session]:
        """Validate a session ID and return the session if valid."""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        if not session.is_valid():
            # Session expired, remove it
            del self.sessions[session_id]
            return None
        
        return session
    
    def get_user_for_session(self, session_id: str) -> Optional[User]:
        """Get the user associated with a session."""
        session = self.validate_session(session_id)
        if not session:
            return None
        
        return self.users.get(session.username)
    
    def refresh_session(self, session_id: str) -> Optional[Session]:
        """Refresh a session's expiration time."""
        session = self.validate_session(session_id)
        if not session:
            return None
        
        session.expires_at = datetime.utcnow() + self.session_timeout
        return session
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate (logout) a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Remove all expired sessions."""
        now = datetime.utcnow()
        expired = [sid for sid, s in self.sessions.items() if s.expires_at < now]
        for sid in expired:
            del self.sessions[sid]
        return len(expired)


# Singleton instance
_auth_service: AuthService = None


def get_auth_service() -> AuthService:
    """Get the singleton AuthService instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


# FastAPI integration helpers
def login(username: str, password: str, ip_address: str = "", user_agent: str = "") -> Optional[Dict]:
    """
    Authenticate user and create session.
    Returns session info dict or None if auth fails.
    """
    auth = get_auth_service()
    user = auth.authenticate(username, password)
    
    if not user:
        return None
    
    session = auth.create_session(username, ip_address, user_agent)
    
    return {
        "session_id": session.session_id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "expires_at": session.expires_at.isoformat()
    }


def validate_session(session_id: str) -> Optional[Dict]:
    """
    Validate session and return user info.
    Returns user info dict or None if session invalid.
    """
    auth = get_auth_service()
    user = auth.get_user_for_session(session_id)
    
    if not user:
        return None
    
    # Refresh session on validation
    session = auth.refresh_session(session_id)
    
    return {
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "expires_at": session.expires_at.isoformat() if session else None
    }


def logout(session_id: str) -> bool:
    """Invalidate a session."""
    return get_auth_service().invalidate_session(session_id)
