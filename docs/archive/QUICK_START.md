# Proxi Quick Start Guide
## Deployment & Testing Instructions

---

## 1. CURRENT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────┐
│                     PRODUCTION SETUP                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ORACLE UBUNTU VM (proxi.audista.com)                               │
│  ─────────────────────────────────────                              │
│                                                                     │
│  ┌─────────────────┐     ┌─────────────────┐                        │
│  │ FRONTEND        │     │ BACKEND         │                        │
│  │ Container       │────▶│ Container       │                        │
│  │                 │     │                 │                        │
│  │ Port 4001       │     │ Port 4000       │                        │
│  │ (React + Vite)  │     │ (Python/FastAPI)│                        │
│  └─────────────────┘     └─────────────────┘                        │
│          │                       │                                  │
│          └───────┬───────────────┘                                  │
│                  │                                                  │
│            ┌─────▼─────┐                                            │
│            │  NGINX    │                                            │
│            │  Reverse  │                                            │
│            │  Proxy    │                                            │
│            └─────┬─────┘                                            │
│                  │                                                  │
│            Port 80/443                                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. LOGIN CREDENTIALS

| Username | Password | Role | Use For |
|----------|----------|------|---------|
| `demo` | *(auto-generated on first run)* | User | General testing |
| `judge` | *(auto-generated on first run)* | Judge | Hackathon judges |
| `admin` | *(auto-generated on first run)* | Admin | Admin functions |

> Passwords are generated on first run and saved to `backend/auth/INITIAL_CREDENTIALS.txt`. Delete that file after noting them.

---

## 3. DEPLOYMENT STEPS

### Step 1: SSH to Oracle Ubuntu
```bash
ssh ubuntu@<your-oracle-ip>
cd ~/proxi-ai
```

### Step 2: Pull Latest Code
```bash
git pull origin main
```

### Step 3: Set Environment Variables
```bash
# Create .env if not exists
cat > .env << EOF
GEMINI_API_KEY=your_gemini_api_key_here
RUNTIME_MODE=DEMO
EOF
```

### Step 4: Build and Start Containers
```bash
# Remove version warning - optional
sed -i '/^version:/d' docker-compose.yml

# Build and start
docker compose up -d --build

# Verify running
docker compose ps
```

Expected output:
```
NAME                  STATUS      PORTS
proxi-ai-backend-1    Up          0.0.0.0:4000->8000/tcp
proxi-ai-frontend-1   Up          0.0.0.0:4001->5173/tcp
```

### Step 5: Test Endpoints
```bash
# Health check
curl http://localhost:4000/api/health

# Workstations list
curl http://localhost:4000/api/workstations
```

---

## 4. NGINX CONFIGURATION (Optional - for HTTPS)

If using Nginx reverse proxy:

```bash
sudo tee /etc/nginx/sites-available/proxi << 'EOF'
server {
    listen 80;
    server_name proxi.audista.com;

    # Frontend
    location / {
        proxy_pass http://localhost:4001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:4000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/proxi /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## 5. TESTING CHECKLIST

### Basic Tests
```
□ Open browser to http://<server-ip>:4001
□ Login page displays
□ Login with demo/<YOUR_PASSWORD>
□ Workstation list shows (may show "offline" - that's OK)
□ Chat interface opens
□ Can type message and send
```

### API Tests (from server)
```bash
# Test login
curl -X POST http://localhost:4000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"<YOUR_PASSWORD>"}'

# Test workstations
curl http://localhost:4000/api/workstations

# Test health
curl http://localhost:4000/api/health
```

---

## 6. DEMO FLOW (The "Million Dollar Minute")

### Setup Before Demo
1. Have mock apps open (if available)
2. Open Proxi on phone or mobile browser
3. Login with `demo` / `<YOUR_PASSWORD>`

### Demo Commands to Try
1. **"What time is it?"** - Basic response test
2. **"Take a screenshot of the desktop"** - Tests screenshot capability
3. **"Open notepad"** - Tests app launching
4. **"Find PowerPoint files in Downloads from last week"** - Tests file search

### Fallback Phrases
If something doesn't work:
- "Let me try another approach..."
- "The desktop automation is connecting..."

---

## 7. TROUBLESHOOTING

### Containers Not Starting
```bash
# Check logs
docker compose logs backend
docker compose logs frontend

# Rebuild from scratch
docker compose down
docker compose up -d --build
```

### Port Already in Use
```bash
# Find what's using the port
sudo lsof -i :4000
sudo lsof -i :4001

# Kill if needed
sudo kill -9 <PID>
```

### Frontend Can't Reach Backend
```bash
# Check if backend is responding
curl http://localhost:4000/api/health

# Check container network
docker compose ps
docker network ls
```

### Workstations Show "Offline"
This is expected! The workstation registry has demo entries for Windows machines that aren't actually running. The Linux backend (this container) IS online.

---

## 8. KEY FILES

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Container orchestration |
| `.env` | API keys and config |
| `backend/registry/workstations.json` | Registered workstations |
| `backend/auth/users.json` | User credentials |
| `DEMO_SCRIPT.md` | Demo scenario script |
| `DEPLOYMENT.md` | Full deployment documentation |

---

## 9. QUICK COMMANDS

```bash
# Start containers
docker compose up -d

# Stop containers
docker compose down

# View logs
docker compose logs -f

# Rebuild after code changes
docker compose up -d --build

# Check status
docker compose ps

# Enter backend container
docker compose exec backend bash

# Enter frontend container
docker compose exec frontend sh
```

---

*Last Updated: January 2026*
