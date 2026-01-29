#!/bin/bash
# Proxi Core Entrypoint - Fixes permissions before starting
# This runs as root, fixes ownership, then switches to proxi user

# Fix ownership of mounted volumes (runs as root)
# These directories contain runtime data that may be created by host user (git pull)
chown -R proxi:proxi /app/data 2>/dev/null || true
chown proxi:proxi /app/.env 2>/dev/null || true

# Fix auth directory - sessions.json, users.json are written at runtime
chown -R proxi:proxi /app/backend/auth 2>/dev/null || true

# Fix registry directory - workstations.json is written at runtime
chown -R proxi:proxi /app/backend/registry 2>/dev/null || true

# Ensure data directory exists and is writable
mkdir -p /app/data
chmod 755 /app/data

# Switch to proxi user and run the app
exec gosu proxi uvicorn backend.main:app --host 0.0.0.0 --port 8000
