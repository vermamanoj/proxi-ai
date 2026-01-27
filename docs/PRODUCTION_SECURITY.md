# Proxi Production Security Checklist

## For deployment to proxi.audista.com

---

## ✅ Pre-Deployment Checklist

### 1. Authentication & Authorization

- [ ] **Change default credentials** - Delete `users.json` and `INITIAL_CREDENTIALS.txt` after noting new passwords
- [ ] **Use strong passwords** - Minimum 16 characters, mixed case, numbers, symbols
- [ ] **Review user roles** - Ensure only necessary users have admin/judge roles
- [ ] **JWT secret** - Set a strong `JWT_SECRET` in `.env` (min 32 random characters)

```bash
# Generate secure JWT secret
openssl rand -base64 32
```

### 2. Environment Variables

- [ ] **Never commit `.env`** - Already in `.gitignore`
- [ ] **Rotate API keys** - Generate fresh `GEMINI_API_KEY` for production
- [ ] **Set production values**:

```env
# .env for production
GEMINI_API_KEY=your_production_key
JWT_SECRET=your_32_char_random_secret
CORS_ORIGINS=https://proxi.audista.com
```

### 3. Network Security

- [ ] **HTTPS only** - Use reverse proxy (nginx/Caddy) with SSL
- [ ] **Restrict CORS** - Update `CORS_ORIGINS` to only allow your domain
- [ ] **Firewall rules** - Only expose ports 80/443 externally
- [ ] **Internal ports** - Keep 4000 (API), 5173 (frontend dev) internal only

### 4. Docker Security

- [x] **Updated base images** - node:22-alpine, python:3.12-slim
- [x] **Updated dependencies** - Fixed critical CVEs (Jan 2026)
- [ ] **Run as non-root** - Add `USER` directive to Dockerfiles
- [ ] **Read-only filesystem** - Consider `read_only: true` for containers
- [ ] **Resource limits** - Add memory/CPU limits to docker-compose

```yaml
# docker-compose.yml additions
services:
  core:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
```

### 5. Data Protection

- [x] **Persistent volumes** - Database in `./data/` survives rebuilds
- [ ] **Backup strategy** - Regular backups of `./data/proxi_memory.db`
- [ ] **Log rotation** - Implement log rotation for `proxi_debug.log`
- [ ] **Sensitive data** - Never log API keys or passwords

### 6. Agent Security

- [ ] **Command guard enabled** - Review `backend/tools/command_guard.py`
- [ ] **Blocked commands** - Verify dangerous commands are blocked
- [ ] **Approval workflow** - Sensitive commands require user approval
- [ ] **Agent isolation** - Agents run in separate containers

---

## 🔒 Recommended Production Setup

### Reverse Proxy (Caddy example)

```Caddyfile
proxi.audista.com {
    # Frontend
    handle /* {
        reverse_proxy localhost:4002
    }
    
    # API
    handle /api/* {
        reverse_proxy localhost:4000
    }
    
    # WebSocket for Gemini Live
    handle /ws/* {
        reverse_proxy localhost:4000
    }
}
```

### Nginx Alternative

```nginx
server {
    listen 443 ssl http2;
    server_name proxi.audista.com;
    
    ssl_certificate /etc/ssl/certs/proxi.crt;
    ssl_certificate_key /etc/ssl/private/proxi.key;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    location / {
        proxy_pass http://localhost:4002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }
    
    location /api/ {
        proxy_pass http://localhost:4000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /ws/ {
        proxy_pass http://localhost:4000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 🚨 Security Vulnerabilities Fixed

| Date | Image | Issue | Fix |
|------|-------|-------|-----|
| 2026-01-27 | proxi-core | starlette CVE-2024-47874 | Updated to >=0.41.0 |
| 2026-01-27 | proxi-core | aiohttp CVE-2024-23334 | Updated to >=3.11.0 |
| 2026-01-27 | proxi-core | python-multipart CVE-2024-24789 | Updated to >=0.0.18 |
| 2026-01-27 | proxi-ai-frontend | golang/stdlib CVE-2024-24790 | Updated to node:22-alpine |

---

## 📋 Post-Deployment Verification

```bash
# 1. Check containers are running
docker compose ps

# 2. Verify health endpoint
curl https://proxi.audista.com/api/health

# 3. Test authentication
curl -X POST https://proxi.audista.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"YOUR_PASSWORD"}'

# 4. Check SSL certificate
openssl s_client -connect proxi.audista.com:443 -servername proxi.audista.com

# 5. Run Docker Scout scan
docker scout cves proxi-core:latest
docker scout cves proxi-ai-frontend:latest
```

---

## 🔄 Ongoing Maintenance

1. **Weekly**: Check for dependency updates (`docker scout recommendations`)
2. **Monthly**: Rotate JWT secret and API keys
3. **Quarterly**: Full security audit of command_guard patterns
4. **On CVE**: Immediately update affected packages and rebuild

---

## ⚠️ Known Limitations

1. **SQLite** - Single-file database, not suitable for high concurrency
2. **Session storage** - Consider Redis for horizontal scaling
3. **Agent registration** - Currently manual, plan for certificate-based auth

---

*Last updated: 2026-01-27*
