# Cloudflare Tunnel — Setup & Operation

Public URL exposing the local FastAPI backend (`localhost:8000`) so the Vercel frontend can reach it.

## Install (Windows)

```powershell
winget install --id Cloudflare.cloudflared
```

Binary lands at `C:\Program Files (x86)\cloudflared\cloudflared.exe`. After install, **open a new terminal** so PATH is refreshed (or just call the full path).

---

## Mode 1: Quick tunnel (dev / testing)

Random URL, no Cloudflare account needed. URL changes every restart.

```bash
cloudflared tunnel --url http://localhost:8000
```

Output looks like:
```
| https://expansion-regardless-fares-owns.trycloudflare.com |
```

Copy that URL → use as `NEXT_PUBLIC_API_URL` on Vercel.

**One-shot start (backend + tunnel):**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_all.ps1
```

---

## Mode 2: Named tunnel (production / stable URL)

Stable URL forever, free, requires Cloudflare account + a domain on Cloudflare.

### 2.1 Login (opens browser)

```bash
cloudflared tunnel login
```

Pick the domain to use → cert is saved at `~/.cloudflared/cert.pem`.

### 2.2 Create tunnel

```bash
cloudflared tunnel create review-api
# → Tunnel UUID is printed; credentials saved at ~/.cloudflared/<UUID>.json
```

### 2.3 Map a DNS subdomain

```bash
cloudflared tunnel route dns review-api review-api.your-domain.com
```

### 2.4 Create config file

`~/.cloudflared/config.yml`:
```yaml
tunnel: <UUID>
credentials-file: C:\Users\<you>\.cloudflared\<UUID>.json

ingress:
  - hostname: review-api.your-domain.com
    service: http://localhost:8000
  - service: http_status:404
```

### 2.5 Run

```bash
cloudflared tunnel run review-api
```

Now `https://review-api.your-domain.com` always points to your local `:8000`.

### 2.6 Run as Windows service (auto-start at boot)

```powershell
# Run elevated PowerShell
cloudflared service install
```

Stop / start:
```powershell
sc.exe stop  cloudflared
sc.exe start cloudflared
```

---

## CORS reminder

After getting your tunnel URL, the backend **only accepts requests from origins listed in `ALLOWED_ORIGINS`** (set in `.env`).

When you deploy the Vercel frontend, append its URL:
```
ALLOWED_ORIGINS=http://localhost:3000,https://your-app.vercel.app
```
Then restart the backend (uvicorn auto-reload picks it up).

---

## Test the tunnel

```bash
# Replace with your actual tunnel URL + API key
URL=https://abc-xyz.trycloudflare.com
KEY=$(grep ^API_KEY .env | cut -d= -f2)

# Public health check
curl $URL/api/health

# Auth-protected endpoint
curl -H "Authorization: Bearer $KEY" $URL/api/repos
```

Expected:
- `/api/health` → 200 with `{"status":"ok",...}`
- `/api/repos` → 200 with repo list (or 401 without the Bearer header)
- Latency: 100-300ms typical from same region

---

## Troubleshooting

| Symptom | Cause / Fix |
|---|---|
| `cloudflared: command not found` | New terminal needed after install, or use full path `"C:\Program Files (x86)\cloudflared\cloudflared.exe"` |
| Tunnel URL works but returns 502 | Backend not running on `:8000`. Start uvicorn first. |
| 401 on every request | Missing `Authorization: Bearer <key>` header, or wrong key |
| CORS error in browser console | Vercel domain not in `ALLOWED_ORIGINS`; restart backend after editing `.env` |
| Quick tunnel disappears after a while | Quick tunnels have no uptime guarantee — use named tunnel for production |
| Named tunnel won't start | `cloudflared tunnel info <name>` and check `~/.cloudflared/config.yml` paths |
