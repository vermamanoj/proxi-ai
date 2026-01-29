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
import bcrypt
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


@dataclass
class MagicLink:
    token: str
    username: str
    role: str
    created_at: datetime
    expires_at: datetime
    uses_remaining: int = 1  # Single use by default
    label: str = ""  # e.g., "Judge 1", "Hackathon Demo"
    
    def is_valid(self) -> bool:
        return datetime.utcnow() < self.expires_at and self.uses_remaining > 0


class AuthService:
    """
    Simple authentication service with local user storage.
    """
    
    def __init__(self, users_file: str = None, session_timeout_minutes: int = 360):
        self.users_file = users_file or self._default_users_file()
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.sessions: Dict[str, Session] = {}
        self.magic_links: Dict[str, MagicLink] = {}
        self._load_users()
        self._load_magic_links()
        self._load_sessions()
    
    def _default_users_file(self) -> str:
        """Get default path for users file."""
        backend_dir = Path(__file__).parent.parent
        return str(backend_dir / "auth" / "users.json")
    
    def _magic_links_file(self) -> str:
        """Get path for magic links file."""
        return str(Path(self.users_file).parent / "magic_links.json")
    
    def _sessions_file(self) -> str:
        """Get path for sessions file."""
        return str(Path(self.users_file).parent / "sessions.json")
    
    def _load_sessions(self):
        """Load sessions from JSON file."""
        sessions_file = self._sessions_file()
        if os.path.exists(sessions_file):
            try:
                with open(sessions_file, 'r') as f:
                    data = json.load(f)
                    for session_id, session_data in data.items():
                        session = Session(
                            session_id=session_data["session_id"],
                            username=session_data["username"],
                            created_at=datetime.fromisoformat(session_data["created_at"]),
                            expires_at=datetime.fromisoformat(session_data["expires_at"]),
                            ip_address=session_data.get("ip_address", ""),
                            user_agent=session_data.get("user_agent", "")
                        )
                        # Only load if not expired
                        if session.is_valid():
                            self.sessions[session_id] = session
                print(f"[AUTH] Loaded {len(self.sessions)} valid sessions")
            except Exception as e:
                print(f"[AUTH] Error loading sessions: {e}")
    
    def _save_sessions(self):
        """Save sessions to JSON file."""
        sessions_file = self._sessions_file()
        os.makedirs(os.path.dirname(sessions_file), exist_ok=True)
        data = {}
        for session_id, session in self.sessions.items():
            if session.is_valid():  # Only save valid sessions
                data[session_id] = {
                    "session_id": session.session_id,
                    "username": session.username,
                    "created_at": session.created_at.isoformat(),
                    "expires_at": session.expires_at.isoformat(),
                    "ip_address": session.ip_address,
                    "user_agent": session.user_agent
                }
        with open(sessions_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_magic_links(self):
        """Load magic links from JSON file."""
        links_file = self._magic_links_file()
        if os.path.exists(links_file):
            try:
                with open(links_file, 'r') as f:
                    data = json.load(f)
                    for token, link_data in data.items():
                        self.magic_links[token] = MagicLink(
                            token=link_data["token"],
                            username=link_data["username"],
                            role=link_data["role"],
                            created_at=datetime.fromisoformat(link_data["created_at"]),
                            expires_at=datetime.fromisoformat(link_data["expires_at"]),
                            uses_remaining=link_data.get("uses_remaining", 1),
                            label=link_data.get("label", "")
                        )
            except Exception as e:
                print(f"[AUTH] Error loading magic links: {e}")
    
    def _save_magic_links(self):
        """Save magic links to JSON file."""
        links_file = self._magic_links_file()
        os.makedirs(os.path.dirname(links_file), exist_ok=True)
        data = {}
        for token, link in self.magic_links.items():
            data[token] = {
                "token": link.token,
                "username": link.username,
                "role": link.role,
                "created_at": link.created_at.isoformat(),
                "expires_at": link.expires_at.isoformat(),
                "uses_remaining": link.uses_remaining,
                "label": link.label
            }
        with open(links_file, 'w') as f:
            json.dump(data, f, indent=2)
    
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
        """Hash password using bcrypt (12 rounds)."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash. Supports legacy SHA-256 hashes for migration."""
        # Detect legacy SHA-256 hash (64 hex chars)
        if len(hashed) == 64 and all(c in '0123456789abcdef' for c in hashed):
            # Legacy SHA-256 hash - verify using old method
            salt = "proxi_hackathon_salt_2026"
            legacy_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
            return legacy_hash == hashed
        
        # Modern bcrypt hash
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False
    
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
        """Authenticate a user by username and password. Upgrades legacy hashes on successful login."""
        user = self.users.get(username)
        if not user:
            return None
        
        if not self._verify_password(password, user.password_hash):
            return None
        
        # If using legacy hash, upgrade to bcrypt
        if len(user.password_hash) == 64:
            user.password_hash = self._hash_password(password)
            self._save_users()
            print(f"[AUTH] Upgraded password hash for user: {username}")
        
        return user
    
    def create_session(self, username: str, ip_address: str = "", user_agent: str = "", remember_me: bool = False) -> Session:
        """Create a new session for a user. If remember_me is True, session lasts 24 hours."""
        session_id = self._generate_session_id()
        now = datetime.utcnow()
        timeout = timedelta(hours=24) if remember_me else self.session_timeout
        
        session = Session(
            session_id=session_id,
            username=username,
            created_at=now,
            expires_at=now + timeout,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.sessions[session_id] = session
        self._save_sessions()  # Persist to disk
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
        self._save_sessions()  # Persist refreshed session
        return session
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate (logout) a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_sessions()  # Persist removal
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Remove all expired sessions."""
        now = datetime.utcnow()
        expired = [sid for sid, s in self.sessions.items() if s.expires_at < now]
        for sid in expired:
            del self.sessions[sid]
        return len(expired)
    
    # --- Magic Link Methods ---
    
    def create_magic_link(
        self, 
        role: str = "judge",
        label: str = "",
        expires_hours: int = 72,
        uses: int = 10
    ) -> MagicLink:
        """
        Create a magic link for passwordless access.
        Default: 72 hours validity, 10 uses (for multiple judges sharing link).
        """
        token = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        
        # Generate a pseudo-username for this magic link
        username = f"magic_{token[:8]}"
        
        link = MagicLink(
            token=token,
            username=username,
            role=role,
            created_at=now,
            expires_at=now + timedelta(hours=expires_hours),
            uses_remaining=uses,
            label=label
        )
        
        self.magic_links[token] = link
        self._save_magic_links()
        
        print(f"[AUTH] Created magic link: {label or 'unnamed'} (role={role}, uses={uses}, expires={expires_hours}h)")
        return link
    
    def validate_magic_link(self, token: str) -> Optional[MagicLink]:
        """Validate a magic link token."""
        link = self.magic_links.get(token)
        if not link:
            return None
        
        if not link.is_valid():
            return None
        
        return link
    
    def redeem_magic_link(self, token: str) -> Optional[Session]:
        """
        Redeem a magic link and create a session.
        Decrements uses_remaining.
        """
        link = self.validate_magic_link(token)
        if not link:
            return None
        
        # Decrement uses
        link.uses_remaining -= 1
        self._save_magic_links()
        
        # Create a session for this magic link user
        session = self.create_session(link.username)
        
        # Store role info in a special way (we'll create a virtual user)
        if link.username not in self.users:
            self.users[link.username] = User(
                username=link.username,
                password_hash="",  # No password for magic link users
                display_name=link.label or f"Guest ({link.role.title()})",
                role=link.role,
                created_at=datetime.utcnow().isoformat()
            )
        
        print(f"[AUTH] Magic link redeemed: {link.label or link.username} ({link.uses_remaining} uses left)")
        return session
    
    def list_magic_links(self) -> list:
        """List all magic links with their status."""
        result = []
        for token, link in self.magic_links.items():
            result.append({
                "token": token,
                "label": link.label,
                "role": link.role,
                "uses_remaining": link.uses_remaining,
                "expires_at": link.expires_at.isoformat(),
                "is_valid": link.is_valid(),
                "created_at": link.created_at.isoformat()
            })
        return result
    
    def revoke_magic_link(self, token: str) -> bool:
        """Revoke a magic link."""
        if token in self.magic_links:
            del self.magic_links[token]
            self._save_magic_links()
            return True
        return False


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
