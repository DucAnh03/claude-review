# Migration Plan: Streamlit → Vercel + FastAPI + Cloudflare Tunnel

**Goal:** chuyển UI từ Streamlit (chỉ chạy local) sang Next.js trên Vercel (truy cập qua URL public từ bất kỳ đâu), giữ máy local làm backend chạy Claude Code CLI / git / SQLite.

---

## Architecture

```
┌─────────────────────┐
│  Dev's browser      │
│  (any network)      │
└──────────┬──────────┘
           │ HTTPS
           ▼
┌─────────────────────┐
│  Vercel             │  ← Next.js frontend (static + SSR)
│  app.vercel.app     │
└──────────┬──────────┘
           │ fetch() to API_URL
           ▼
┌─────────────────────┐
│  Cloudflare Tunnel  │  ← https://review-api.trycloudflare.com
│  (public endpoint)  │
└──────────┬──────────┘
           │ encrypted tunnel
           ▼
┌─────────────────────┐
│  FastAPI            │  ← localhost:8000 trên máy bạn
│  (backend)          │
└──────────┬──────────┘
           │
           ├──► claude.cmd --print
           ├──► git clone / fetch / checkout
           ├──► SQLite (review_system.db)
           └──► Slack Bot (vẫn chạy như cũ)
```

**Key decisions:**

- **Backend:** FastAPI — wrap lại toàn bộ logic trong `db.py`, `review_core.py`, `pr_review.py` thành REST endpoints.
- **Tunnel:** Cloudflare Tunnel (miễn phí, URL cố định, không cần port-forward router).
- **Frontend:** Next.js 14 App Router trên Vercel.
- **Auth:** Simple API key (Bearer token) trong header — đủ cho team nhỏ.
- **Async reviews:** giữ pattern queue hiện có. Endpoint trigger trả về `job_id`, frontend poll `/jobs/{id}` mỗi 2-3s.

---

## Phase 1 — FastAPI Backend

### 1.1 Setup project structure

```
backend/
├── main.py              # FastAPI app entrypoint
├── api/
│   ├── repos.py         # /api/repos endpoints
│   ├── devs.py          # /api/devs endpoints
│   ├── reviews.py       # /api/reviews + job triggers
│   ├── skills.py        # /api/skills (read/write .md files)
│   └── stats.py         # /api/stats
├── core/
│   ├── auth.py          # API key middleware
│   ├── jobs.py          # Job queue + status tracking
│   └── config.py        # env vars
└── requirements.txt
```

Existing modules (`db.py`, `review_core.py`, `pr_review.py`, `crypto.py`) **không sửa** — backend import và dùng.

### 1.2 API endpoints

**Repos:**
- `GET    /api/repos` — list all
- `POST   /api/repos` — create (manual local_dir)
- `POST   /api/repos/clone` — clone from GitHub URL → auto-create
- `GET    /api/repos/{name}` — detail
- `PATCH  /api/repos/{name}` — update
- `DELETE /api/repos/{name}` — delete
- `GET    /api/repos/{name}/skills` — list assigned skills
- `PUT    /api/repos/{name}/skills` — set assigned skills

**Devs:**
- `GET    /api/repos/{name}/devs` — list
- `POST   /api/repos/{name}/devs` — create
- `PATCH  /api/repos/{name}/devs/{dev_name}` — update slack_id / token
- `DELETE /api/repos/{name}/devs/{dev_name}` — delete

**Reviews:**
- `GET    /api/reviews?repo=&verdict=&dev=&limit=` — list with filters
- `GET    /api/reviews/{id}` — detail + report markdown content
- `POST   /api/reviews/commit` — trigger commit review → returns `{job_id}`
- `POST   /api/reviews/pr` — trigger PR review → returns `{job_id}`
- `GET    /api/jobs/{job_id}` — poll job status (queued/running/done/failed) + result

**Skills:**
- `GET    /api/skills` — list all skill files (name, path, has_content)
- `GET    /api/skills/{filename}` — get markdown content
- `PUT    /api/skills/{filename}` — update markdown content

**Stats:**
- `GET    /api/stats` — same shape as `db.get_stats()`

**Health:**
- `GET    /api/health` — `{status: "ok", claude: true, git: true}`

### 1.3 Auth (Bearer token)

```python
# .env trên máy local
API_KEY=<random-32-byte-hex>
```

Frontend gửi header `Authorization: Bearer <API_KEY>`. Middleware check key → 401 nếu sai.

### 1.4 CORS

Cho phép Vercel domain gọi API:
```python
app.add_middleware(CORSMiddleware,
    allow_origins=["https://your-app.vercel.app"],
    allow_methods=["*"], allow_headers=["*"])
```

### 1.5 Job queue (background tasks)

Giữ pattern hiện có (`queue.Queue` + worker thread). Endpoint trigger:
1. Gen `job_id` (uuid)
2. Lưu vào `jobs_dict[job_id] = {"status": "queued", ...}`
3. Push job vào queue
4. Worker pop → update status → run review → save result vào dict
5. Frontend poll `/api/jobs/{job_id}` để biết khi nào xong

### Phase 1 Checklist

- [ ] `backend/` folder created với structure trên
- [ ] FastAPI app starts on `localhost:8000`
- [ ] `/api/health` returns `{status: "ok"}`
- [ ] All Repo CRUD endpoints work (test với curl/Postman)
- [ ] All Dev CRUD endpoints work
- [ ] `/api/reviews/commit` queues a job, returns job_id
- [ ] `/api/jobs/{id}` returns correct status throughout lifecycle
- [ ] Review job actually runs `claude` and saves report to DB
- [ ] `/api/skills/{name}` GET reads file, PUT writes file
- [ ] API key auth blocks requests without correct Bearer token
- [ ] CORS configured (will test in Phase 3)

---

## Phase 2 — Cloudflare Tunnel

### 2.1 Install cloudflared

Windows:
```powershell
winget install --id Cloudflare.cloudflared
```

### 2.2 Quick tunnel (test trước)

```bash
cloudflared tunnel --url http://localhost:8000
# Output: https://random-words-xyz.trycloudflare.com
```

URL random này sẽ đổi mỗi lần restart — dùng để test.

### 2.3 Named tunnel (production)

Stable URL, free, không expire:

```bash
cloudflared tunnel login                   # mở browser, login Cloudflare
cloudflared tunnel create review-api       # tạo tunnel
cloudflared tunnel route dns review-api review-api.your-domain.com
cloudflared tunnel run review-api
```

(Nếu chưa có domain → dùng quick tunnel cho dev, named tunnel khi go live)

### 2.4 Run as Windows service

Để tunnel tự start khi máy bật:
```bash
cloudflared service install
```

### Phase 2 Checklist

- [ ] cloudflared installed
- [ ] Quick tunnel chạy được, gọi `https://xxx.trycloudflare.com/api/health` từ máy khác → 200 OK
- [ ] Named tunnel created (nếu có domain)
- [ ] Tunnel URL được copy vào `.env.local` của Next.js làm `NEXT_PUBLIC_API_URL`
- [ ] cloudflared chạy như Windows service (optional)

---

## Phase 3 — Next.js Frontend trên Vercel

### 3.1 Setup project

```bash
npx create-next-app@latest review-ui --typescript --tailwind --app
cd review-ui
npm install @tanstack/react-query lucide-react
npm install @uiw/react-md-editor   # markdown editor cho skill files
```

### 3.2 Pages structure

```
app/
├── layout.tsx              # nav, theme
├── page.tsx                # dashboard / stats
├── repos/
│   ├── page.tsx            # list + add/clone modal
│   └── [name]/
│       └── page.tsx        # detail: info, skills, devs
├── reviews/
│   ├── page.tsx            # list with filters
│   └── [id]/
│       └── page.tsx        # report viewer (render markdown)
├── skills/
│   └── page.tsx            # skill editor (markdown editor)
└── trigger/
    └── page.tsx            # manual review trigger form
```

### 3.3 API client

```typescript
// lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL!;
const API_KEY = process.env.NEXT_PUBLIC_API_KEY!;  // chấp nhận lộ — internal tool

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Authorization": `Bearer ${API_KEY}`,
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
```

> Nếu lo bảo mật API key bị lộ ở client → chuyển sang Next.js API route làm proxy, key chỉ ở server.

### 3.4 Environment variables (Vercel dashboard)

```
NEXT_PUBLIC_API_URL=https://review-api.trycloudflare.com
NEXT_PUBLIC_API_KEY=<same-as-backend>
```

### 3.5 Deploy

```bash
git push origin main         # Vercel auto-deploys
```

### Phase 3 Checklist

- [ ] Next.js project created
- [ ] All pages render với mock data
- [ ] API client wired to backend (test local first)
- [ ] Repos page: list, add, edit, delete, clone work end-to-end
- [ ] Devs page: CRUD work
- [ ] Reviews page: list with filters work, report viewer renders markdown
- [ ] Trigger page: submit commit/PR review → job_id received → polling shows progress
- [ ] Skills page: edit .md file → save → file actually updated trên máy local
- [ ] Stats page: charts render correctly
- [ ] Deploy to Vercel
- [ ] Env vars configured in Vercel dashboard
- [ ] Production URL accessible from another network (mobile data)

---

## Phase 4 — Integration Testing

### 4.1 End-to-end flows

| Flow | Steps |
|------|-------|
| Clone repo | UI → POST /clone → git clone runs → repo appears in list |
| Add dev | UI → POST /devs → dev appears under repo |
| Trigger commit review | UI form → POST /reviews/commit → poll job → report shows |
| Trigger PR review | Same nhưng PR number |
| Edit skill | Skills page → edit Python.md → save → next review uses new content |
| View report | Click review in list → markdown renders đúng format mới (Security/Error/Style/Skill) |

### 4.2 Failure cases

| Case | Expected behavior |
|------|-------------------|
| Backend down | Frontend shows "API unreachable" |
| Tunnel disconnects | Same |
| Wrong API key | 401, frontend shows "Unauthorized" |
| Git clone fails (404, auth) | Job status=failed, error message shown |
| Claude CLI fails | Same |
| Invalid commit hash | Job fails with git error |

### Phase 4 Checklist

- [ ] All 6 e2e flows pass
- [ ] All 6 failure cases handled gracefully
- [ ] No CORS errors in browser console
- [ ] Slack bot vẫn hoạt động song song (không bị break)

---

## Phase 5 — Cutover

### 5.1 Run cả 2 song song trong 1 tuần

- Streamlit (`localhost:8501`) vẫn chạy cho ai quen
- Next.js trên Vercel cho team thử

### 5.2 Migrate

- [ ] Document URL Vercel + cách dùng cho team
- [ ] Move Slack bot qua dùng FastAPI internally (optional — bot có thể tiếp tục import `db.py` trực tiếp)
- [ ] Sau 1 tuần: deprecate Streamlit (giữ file, không chạy nữa)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Cloudflare Tunnel rớt | Run as service + health check + auto-restart |
| Máy local tắt → API chết | Document rõ "cần máy bật để dùng" — đây là tradeoff khi backend là local |
| API key bị lộ qua client-side env | Dùng Next.js API routes làm proxy (key ở server) |
| Vercel cold start chậm | Không vấn đề, Next.js trên Vercel không cold-start cho client routes |
| SQLite locked khi nhiều request | Đã có WAL mode trong `db.py`, đủ cho team nhỏ |
| Job queue mất khi restart backend | Save jobs vào DB thay vì memory dict (Phase 6 enhancement) |

---

## Success Criteria (toàn bộ migration coi là DONE khi)

- [ ] Dev có thể truy cập UI từ điện thoại / mạng khác bằng URL Vercel
- [ ] Dev clone được repo mới qua UI mà không cần SSH vào máy local
- [ ] Dev edit được skill file qua UI, change ảnh hưởng review tiếp theo
- [ ] Dev trigger được review từ UI và xem progress real-time
- [ ] Slack bot vẫn hoạt động song song không bị ảnh hưởng
- [ ] Report markdown render đẹp trên Vercel UI (4 categories: Security, Error Handling, Code Style, Skill)
- [ ] API key auth bảo vệ backend khỏi public access
- [ ] Streamlit có thể tắt mà không mất tính năng nào

---

## Estimated effort

| Phase | Work | Time |
|-------|------|------|
| 1 — Backend | FastAPI wrap, auth, jobs | 1-2 ngày |
| 2 — Tunnel | Setup, test | 1-2 giờ |
| 3 — Frontend | Next.js app, all pages | 2-3 ngày |
| 4 — Testing | E2E + failure cases | 0.5-1 ngày |
| 5 — Cutover | Doc + parallel run | 1 tuần |
| **Total active dev time** | | **~5 ngày** |
