# Hackathon Judge Access Guide

## For Gemini 3 Hackathon (Feb 10-27, 2026)

---

## 🔗 Magic Links (Recommended)

Magic links provide **passwordless access** for judges - no login required, no OTP friction.

### How It Works

1. Admin generates a magic link with specific permissions
2. Link is shared with judges via email/chat
3. Judges click the link → automatically authenticated
4. No passwords, no email verification, no device verification

### Judge Access URL Format

```
https://proxi.audista.com?magic=<TOKEN>
```

### Link Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| `role` | `judge` | Permission level (judge, user, admin) |
| `label` | - | Display name shown in UI |
| `expires_hours` | 72 | Link validity period |
| `uses` | 10 | Max redemptions (multiple judges can share) |

### Recommended Settings for Hackathon

```json
{
  "role": "judge",
  "label": "Gemini3 Hackathon Judge",
  "expires_hours": 408,  // 17 days (Feb 10-27)
  "uses": 50             // Allow multiple judges + retries
}
```

---

## 🛠️ Creating Magic Links

### Option 1: Admin UI (Recommended)

1. Login as `admin` at https://proxi.audista.com
2. Click the **Settings** (gear) icon
3. Navigate to **Admin** section
4. Click **Generate Magic Link**
5. Configure and copy the link

### Option 2: API

```bash
# First, get admin session cookie by logging in
curl -X POST https://proxi.audista.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "YOUR_ADMIN_PASSWORD"}' \
  -c cookies.txt

# Create magic link
curl -X POST https://proxi.audista.com/api/auth/magic-link \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "role": "judge",
    "label": "Gemini3 Hackathon Judge",
    "expires_hours": 408,
    "uses": 50
  }'
```

Response:
```json
{
  "token": "abc123...",
  "label": "Gemini3 Hackathon Judge",
  "role": "judge",
  "expires_at": "2026-02-27T00:00:00",
  "uses_remaining": 50,
  "url": "/magic/abc123..."
}
```

---

## 📋 Managing Links

### List All Links (Admin)

```bash
curl https://proxi.audista.com/api/auth/magic-links \
  -b cookies.txt
```

### Revoke a Link

```bash
curl -X DELETE https://proxi.audista.com/api/auth/magic-link/<TOKEN> \
  -b cookies.txt
```

### Check Link Status

```bash
curl https://proxi.audista.com/api/auth/magic-link/<TOKEN>
```

---

## 🎯 Demo Script for Judges

### Quick Demo (2 minutes)

1. **Open**: Click the magic link provided
2. **Voice**: Click microphone, say "Check system health"
3. **Watch**: See the AI analyze CPU, memory, disk
4. **Text**: Type "Show me running processes"
5. **Remote**: Select a Windows agent, run a command

### Full Demo (5 minutes)

1. Start with voice: "Hello Proxi"
2. Ask: "What can you do?"
3. System task: "Check if there are any large files in temp"
4. Creative: "Create a PowerPoint about AI agents"
5. Show approval flow: "Install a package" (will ask for approval)

---

## 🔐 Security Notes

- Magic links are stored in `backend/auth/magic_links.json`
- Links auto-expire after configured time
- Uses decrement with each redemption
- Admin can revoke links at any time
- Session expires after 30 minutes of inactivity

---

## 📞 Troubleshooting

### "Invalid or Expired Link"

- Link has been used max times
- Link has expired
- Link was revoked by admin

**Solution**: Generate a new magic link

### Judge Can't Connect

1. Check backend is running: `docker ps`
2. Check logs: `docker compose logs core`
3. Verify domain DNS is correct

### Multiple Judges Sharing Link

This is supported! Set `uses` to a high number (50+) so multiple judges can use the same link.

---

*Last updated: 2026-01-27*
