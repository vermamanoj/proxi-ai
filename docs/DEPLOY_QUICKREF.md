# Proxi Deploy Quick Reference

**After code changes, use this guide to deploy.**

---

## 1. Production Server (proxi.audista.com)

```bash
# SSH to server
ssh ubuntu@proxi.audista.com

# Pull and rebuild
cd ~/proxi-ai
git pull
docker compose up -d --build

# Verify
./deploy.sh --status
```

**Full docs:** [DEPLOY_OPS.md](./DEPLOY_OPS.md)

---

## 2. Mobile App (Android APK)

```powershell
# From Windows dev machine (E:\data\proxi-ai\frontend)
$env:CAPACITOR_BUILD='true'; npm run build
npx cap sync android

# Build APK
cd android
$env:JAVA_HOME = "e:\Program Files\Android\Android Studio\jbr"
.\gradlew assembleDebug

# APK location
# E:\data\proxi-ai\frontend\android\app\build\outputs\apk\debug\app-debug.apk
```

**Full docs:** [deploy-mobile-app.md](./deploy-mobile-app.md)

---

## 3. Windows Dev Environment

```powershell
# From E:\data\proxi-ai
docker compose up -d --build

# Or use scripts
.\scripts\deploy-all.ps1 -Rebuild
```

**Full docs:** [DEPLOYMENT.md](./DEPLOYMENT.md)

---

## 4. Forensics Container (Optional)

```bash
# On production server
cd ~/proxi-ai/soc-forensics
docker build -t proxi-forensics:v2 .
docker-compose -f docker-compose.forensic.yml up -d

# Verify (port 5081)
curl http://localhost:5081/health
```

**Full docs:** [SOC_FORENSIC_SIMULATION.md](./SOC_FORENSIC_SIMULATION.md)

---

## Quick Health Checks

| Service | URL | Expected |
|---------|-----|----------|
| Core API | http://localhost:4000/api/health | `{"status":"ok"}` |
| Agent | http://localhost:4001/health | `{"status":"ok"}` |
| Frontend | http://localhost:4002 | UI loads |
| Forensics | http://localhost:5081/health | `{"status":"ok"}` |

---

## Common Issues

| Problem | Fix |
|---------|-----|
| Auth 500 error | `docker compose exec --user root core chown -R proxi:proxi /app/backend/auth/` |
| Permission denied after git pull | Restart container (entrypoint.sh auto-fixes) |
| Mobile voice not working | Ensure `frontend/.env` has `VITE_GEMINI_API_KEY` before build |
| Agent 401 | Check `PROXI_AGENT_KEY` in `.env` and rebuild |

---

*Last updated: 2026-01-29*
