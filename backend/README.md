# Backend — FastAPI for Code Review System

REST API wrapping `db.py`, `review_core.py`, `pr_review.py`, `crypto.py`. Designed to sit behind Cloudflare Tunnel and be called from the Vercel frontend.

## Setup

```bash
# 1. Install deps (from project root)
pip install -r backend/requirements.txt

# 2. Generate API key and add to project-root .env
python -c "import secrets; print('API_KEY=' + secrets.token_hex(32))" >> .env
echo "ALLOWED_ORIGINS=http://localhost:3000,https://your-app.vercel.app" >> .env

# 3. Start backend (from project root)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000/docs` for interactive Swagger UI.

## API overview

All endpoints except `/api/health` require header: `Authorization: Bearer <API_KEY>`

| Method | Path | Description |
|---|---|---|
| GET    | `/api/health` | Public — checks claude/git availability |
| GET    | `/api/repos` | List repos |
| POST   | `/api/repos` | Create repo (manual local_dir) |
| POST   | `/api/repos/clone` | Clone from GitHub URL → auto-create |
| GET    | `/api/repos/{name}` | Repo detail |
| PATCH  | `/api/repos/{name}` | Update fields |
| DELETE | `/api/repos/{name}` | Delete repo (cascades devs) |
| GET    | `/api/repos/{name}/skills` | List assigned skill names |
| PUT    | `/api/repos/{name}/skills` | Set assigned skills |
| GET    | `/api/repos/{name}/devs` | List devs |
| POST   | `/api/repos/{name}/devs` | Create dev |
| PATCH  | `/api/repos/{name}/devs/{dev_name}` | Update slack_id / token |
| DELETE | `/api/repos/{name}/devs/{dev_name}` | Delete dev |
| GET    | `/api/reviews` | List reviews (filter by repo/verdict/dev) |
| GET    | `/api/reviews/{id}` | Detail + report markdown content |
| POST   | `/api/reviews/commit` | Trigger commit review → returns `{job_id}` |
| POST   | `/api/reviews/pr` | Trigger PR review → returns `{job_id}` |
| GET    | `/api/jobs/{job_id}` | Poll job status |
| GET    | `/api/jobs` | List recent jobs |
| GET    | `/api/skills` | List skill .md files |
| GET    | `/api/skills/{filename}` | Read skill markdown |
| PUT    | `/api/skills/{filename}` | Write skill markdown |
| DELETE | `/api/skills/{filename}` | Delete skill file |
| GET    | `/api/stats` | Aggregated stats |

## Async review jobs

`POST /api/reviews/commit` and `POST /api/reviews/pr` return `202 Accepted` with a `job_id`. The job runs in a background worker thread (single worker, jobs run sequentially to avoid git checkout conflicts).

Frontend polls `GET /api/jobs/{job_id}` every 2-3 seconds to see progress:

```json
{
  "job_id": "a1b2c3d4e5f6",
  "type": "commit",
  "status": "running" | "queued" | "done" | "failed",
  "result": {
    "review_id": 123,
    "verdict": "WARNING",
    "report_path": "..."
  },
  "error": null
}
```

## Test from terminal

```bash
# Health (no auth)
curl http://localhost:8000/api/health

# List repos (auth)
curl -H "Authorization: Bearer $API_KEY" http://localhost:8000/api/repos

# Trigger a commit review
curl -X POST http://localhost:8000/api/reviews/commit \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"repo":"tool_monitor","commit":"b58927b","task":"test","slack_id":"anh"}'
```
