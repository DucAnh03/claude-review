#!/usr/bin/env python3
"""
Slack Smart Bot — clone repos and deep AI-powered PR reviews.

.env:
  SLACK_BOT_TOKEN2=xoxb-...
  SLACK_APP_TOKEN2=xapp-...
  SLACK_SIGNING_SECRET2=...
  CLONE_DIR=D:\\projects    (default: ~/projects)

Commands:
  clone <github-url> [name] [token=ghp_xxx]

Auto-detect:
  https://github.com/owner/repo/pull/123  → deep AI review
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from queue import Queue

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import db as database

load_dotenv()

SLACK_BOT_TOKEN      = os.environ.get("SLACK_BOT_TOKEN2") or os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN      = os.environ.get("SLACK_APP_TOKEN2") or os.environ["SLACK_APP_TOKEN"]
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET2") or os.environ["SLACK_SIGNING_SECRET"]
CLONE_DIR            = Path(os.getenv("CLONE_DIR", str(Path.home() / "projects")))
REVIEWS_DIR          = Path(__file__).parent / "reviews"

job_queue: Queue = Queue()
app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)


# ── GitHub API ────────────────────────────────────────────────────────────────

def _gh_get(path: str, token: str | None) -> dict | list:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"GitHub API {e.code}: {body[:300]}")


def _gh_get_text(path: str, token: str | None, accept: str) -> str:
    """Fetch raw text (diff / patch)."""
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", accept)
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub API {e.code}")


def fetch_pr_context(owner: str, repo: str, pr_number: int, token: str | None) -> dict:
    """Fetch everything needed for a deep review."""
    pr      = _gh_get(f"/repos/{owner}/{repo}/pulls/{pr_number}", token)
    files   = _gh_get(f"/repos/{owner}/{repo}/pulls/{pr_number}/files?per_page=100", token)
    commits = _gh_get(f"/repos/{owner}/{repo}/pulls/{pr_number}/commits?per_page=100", token)

    # Full unified diff
    try:
        diff = _gh_get_text(
            f"/repos/{owner}/{repo}/pulls/{pr_number}",
            token,
            "application/vnd.github.diff",
        )
    except Exception:
        diff = "\n".join(
            f"### {f['filename']} (+{f['additions']} -{f['deletions']})\n{f.get('patch','(binary)')}"
            for f in files
        )

    return {
        "pr":      pr,
        "files":   files,
        "commits": commits,
        "diff":    diff,
    }


# ── Claude runner ─────────────────────────────────────────────────────────────

def _run_claude(prompt: str, cwd: Path) -> str:
    allowed = "Read,Write,Edit,Bash,Glob,Grep"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md",
                                     encoding="utf-8", delete=False) as f:
        f.write(prompt)
        tmp = f.name
    try:
        if sys.platform == "win32":
            ps = (
                f"Get-Content -Path '{tmp}' -Raw -Encoding UTF8 | "
                f"& claude.cmd --print --allowedTools '{allowed}'"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                cwd=str(cwd), capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=600,
            )
        else:
            with open(tmp, encoding="utf-8") as f2:
                result = subprocess.run(
                    ["claude", "--print", "--allowedTools", allowed],
                    stdin=f2, cwd=str(cwd),
                    capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=600,
                )
    finally:
        Path(tmp).unlink(missing_ok=True)

    if result.returncode != 0 and not result.stdout.strip():
        raise RuntimeError(result.stderr.strip()[:500])
    return result.stdout.strip()


# ── Prompt builder ────────────────────────────────────────────────────────────

def build_review_prompt(ctx: dict, repo_name: str, dev_name: str) -> str:
    pr      = ctx["pr"]
    files   = ctx["files"]
    commits = ctx["commits"]
    diff    = ctx["diff"]

    # Repo skills
    skills = database.get_repo_skills(repo_name)
    skills_str = ", ".join(s.replace(".md", "") for s in skills) if skills else "auto-detect from code"

    # Commit messages
    commit_msgs = "\n".join(
        f"- {c['sha'][:7]} {c['commit']['message'].splitlines()[0]}"
        for c in commits[:20]
    )

    # File summary
    file_summary = "\n".join(
        f"- `{f['filename']}` +{f['additions']} -{f['deletions']} ({f['status']})"
        for f in files[:50]
    )

    return f"""You are a world-class senior software engineer and security architect.
You are doing a thorough, honest, and insightful code review for a pull request.

---

## Pull Request Info

**Title:** {pr['title']}
**Author:** {pr['user']['login']}
**Branch:** `{pr['head']['ref']}` → `{pr['base']['ref']}`
**Developer (requester):** {dev_name}
**Repository:** {pr['base']['repo']['full_name']}
**Tech stack / skills:** {skills_str}

**PR Description:**
{pr.get('body') or '_(no description provided)_'}

**Commits ({len(commits)}):**
{commit_msgs}

**Files changed ({pr['changed_files']}) | +{pr['additions']} -{pr['deletions']}:**
{file_summary}

---

## Full Diff

```diff
{diff[:30000]}
```

---

## Your Task

Conduct a **deep, senior-level code review**. Go far beyond surface-level style issues.

Think hard about:

1. **Correctness** — Does the code do what the PR description says? Any logic bugs, off-by-one errors, race conditions, or edge cases the author missed?

2. **Security** — Injection attacks, authentication/authorization flaws, sensitive data exposure, insecure defaults, SSRF, path traversal, dependency risks?

3. **Architecture & Design** — Is this the right approach? Are there design smells, violations of SOLID/DRY, tight coupling, wrong abstractions? What would a better design look like?

4. **Error Handling** — Are errors handled properly? Are there unhandled exceptions, silent failures, or cases where the system degrades ungracefully?

5. **Performance** — N+1 queries, unnecessary loops, missing indexes, blocking I/O in async contexts, memory leaks?

6. **Testing** — What edge cases aren't tested? What could break in production that tests don't cover?

7. **Hidden risks** — What could go wrong in production that's not obvious from the diff? Think about: concurrency, state, external dependencies, config drift, deployment ordering.

---

## Report Format

Write a professional, detailed markdown report. Structure it however makes most sense for THIS specific PR — don't follow a rigid template.

**Requirements:**
- Be brutally specific. Reference exact file paths, function names, and line numbers where relevant.
- For every issue, explain WHY it's a problem — not just that it is one.
- For significant issues, provide a concrete fix with a code example.
- Use a tone like a respected senior engineer giving a real code review — honest, constructive, never condescending.
- If something is well done, say so (briefly). Don't be a negativity machine.
- End with a clear **Verdict** section:
  - ✅ **APPROVE** — safe to merge
  - ⚠️ **REQUEST CHANGES** — fixable issues that must be addressed first
  - 🚨 **BLOCK** — serious issues (security, data loss, correctness) that cannot be merged

The developer reading this should feel they received genuine expert insight, not an automated checklist.
"""


# ── Smart review runner ───────────────────────────────────────────────────────

def extract_verdict(text: str) -> str:
    if "🚨" in text and "BLOCK" in text.upper():
        return "SERIOUS"
    if "⚠️" in text or "REQUEST CHANGES" in text.upper():
        return "WARNING"
    if "✅" in text and "APPROVE" in text.upper():
        return "OK"
    return "WARNING"


def run_smart_pr_review(client, channel: str, thread_ts: str, job: dict):
    repo_name = job["repo"]
    pr_number = job["pr_number"]
    dev_name  = job["dev_name"]
    owner     = job["owner"]
    repo_slug = job["repo_slug"]

    repo_row  = database.get_repo(repo_name)
    token     = repo_row["github_token"] if repo_row else None

    VERDICT_ICON = {"OK": "✅", "WARNING": "⚠️", "SERIOUS": "🚨"}

    try:
        post(client, channel, f"🔍 Fetching PR #{pr_number} from GitHub...", thread_ts)
        ctx = fetch_pr_context(owner, repo_slug, pr_number, token)
    except RuntimeError as e:
        err = str(e)
        if "404" in err:
            post(client, channel,
                 f"❌ *PR not found or access denied.*\n"
                 f"> `{owner}/{repo_slug}` PR #{pr_number}\n"
                 f"> If the repo is private, make sure a valid token was saved during clone.", thread_ts)
        elif "401" in err or "403" in err:
            post(client, channel,
                 f"❌ *GitHub authentication failed.*\n"
                 f"> Token stored for `{repo_name}` is invalid or expired.\n"
                 f"> Re-clone with a fresh token: `clone https://github.com/{owner}/{repo_slug} token=ghp_xxx`", thread_ts)
        else:
            post(client, channel, f"❌ *GitHub API error:* {err}", thread_ts)
        return

    pr = ctx["pr"]
    post(client, channel,
         f"🤖 *Claude is reviewing PR #{pr_number}...*\n"
         f"> _{pr['title']}_\n"
         f"> {len(ctx['files'])} files · +{pr['additions']} -{pr['deletions']}\n"
         f"_(this may take 2-5 minutes)_", thread_ts)

    repo_dir = Path(repo_row["local_dir"]) if repo_row else Path.cwd()
    prompt   = build_review_prompt(ctx, repo_name, dev_name)

    try:
        review_text = _run_claude(prompt, repo_dir)
    except Exception as e:
        post(client, channel, f"❌ *Claude failed:* {e}", thread_ts)
        return

    verdict = extract_verdict(review_text)

    # Build final markdown report
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_{repo_name}_PR{pr_number}_smart.md"
    REVIEWS_DIR.mkdir(exist_ok=True)
    report_path = REVIEWS_DIR / filename

    header = f"""# PR Review — {pr['title']}

| Field | Value |
|---|---|
| **Repo** | `{owner}/{repo_slug}` |
| **PR** | [#{pr_number}]({pr['html_url']}) |
| **Author** | {pr['user']['login']} |
| **Reviewer** | Claude (AI) |
| **Developer** | {dev_name} |
| **Branch** | `{pr['head']['ref']}` → `{pr['base']['ref']}` |
| **Files** | {pr['changed_files']} changed · +{pr['additions']} -{pr['deletions']} |
| **Date** | {datetime.now().strftime('%Y-%m-%d %H:%M')} |

---

"""
    report_path.write_text(header + review_text, encoding="utf-8")

    # Save to DB
    try:
        database.add_review(
            repo_name=repo_name,
            commit_hash=pr["head"]["sha"],
            verdict=verdict,
            report_path=str(report_path),
            task_desc=f"PR #{pr_number}: {pr['title']}",
            dev_name=dev_name,
        )
    except Exception:
        pass

    icon = VERDICT_ICON.get(verdict, "❓")
    client.files_upload_v2(
        channel=channel,
        file=str(report_path),
        filename=filename,
        title=f"{icon} PR #{pr_number} Review — {pr['title']}",
        initial_comment=(
            f"{icon} *[{verdict}]* PR #{pr_number} reviewed!\n"
            f"*{pr['title']}* by `{pr['user']['login']}`\n"
            f"See the attached report for the full analysis."
        ),
        thread_ts=thread_ts,
    )


# ── Clone ─────────────────────────────────────────────────────────────────────

def diagnose_clone_error(stderr: str, url: str, token: str | None) -> str:
    s = stderr.lower()
    if "repository not found" in s or "not found" in s:
        if token:
            return (f"❌ *Repo not found* — token may not have access.\n> URL: `{url}`\n"
                    "> Check: `repo` scope on the token and that the repo exists.")
        return (f"❌ *Repo not found* — wrong URL or private (needs token).\n> URL: `{url}`\n"
                "> Add: `clone <url> token=ghp_xxx`")
    if "authentication failed" in s or "could not read username" in s:
        if token:
            return ("❌ *Auth failed* — token wrong or expired.\n"
                    "> Generate a new one: https://github.com/settings/tokens (scope: `repo`)")
        return ("❌ *Private repo* — token required.\n"
                "> Syntax: `clone <url> token=ghp_xxx`")
    if "could not resolve host" in s:
        return (f"❌ *Cannot connect* — check URL/network.\n> `{url}`")
    return f"❌ *Clone failed*\n```{stderr.strip()[:400]}```"


def run_clone(client, channel: str, thread_ts: str, job: dict):
    url       = job["url"]
    repo_name = job["name"]
    token     = job["token"]
    slack_id  = job["slack_id"]
    target    = CLONE_DIR / repo_name
    dev_name  = get_display_name(client, slack_id)

    if not re.match(r"^https?://", url):
        post(client, channel, "❌ Invalid URL — must start with `https://`.", thread_ts)
        return

    if database.get_repo(repo_name):
        post(client, channel,
             f"⚠️ `{repo_name}` already in DB.\n> Use a different name: `clone {url} <other-name>`",
             thread_ts)
        return

    clone_url = url
    if token and url.startswith("https://"):
        clone_url = url.replace("https://", f"https://oauth2:{token}@", 1)

    CLONE_DIR.mkdir(parents=True, exist_ok=True)
    if target.exists():
        post(client, channel,
             f"⚠️ `{target}` already exists — registering in DB only.", thread_ts)
    else:
        r = subprocess.run(
            ["git", "clone", clone_url, str(target)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120,
        )
        if r.returncode != 0:
            post(client, channel, diagnose_clone_error(r.stderr, url, token), thread_ts)
            return

    try:
        database.add_repo(name=repo_name, local_dir=str(target.resolve()),
                          project_name="", desc="", github_url=url, github_token=token or "")
    except ValueError as e:
        post(client, channel, f"❌ DB error: {e}", thread_ts)
        return

    devs = database.get_devs(repo_name)
    if not any(d["slack_id"] == slack_id for d in devs):
        database.add_dev(repo_name, dev_name=dev_name, slack_id=slack_id)

    post(client, channel,
         f"✅ *Cloned!*\n• Repo: `{repo_name}`\n• Path: `{target}`\n"
         f"• Dev: *{dev_name}*\n• Token: {'✓ saved' if token else '✗ public repo'}\n\n"
         f"Paste a PR URL to review it automatically.", thread_ts)


# ── Helpers ───────────────────────────────────────────────────────────────────

def post(client, channel: str, text: str, thread_ts: str | None = None):
    client.chat_postMessage(channel=channel, text=text, thread_ts=thread_ts)


def get_display_name(client, slack_id: str) -> str:
    try:
        info    = client.users_info(user=slack_id)
        profile = info["user"]["profile"]
        return profile.get("display_name") or profile.get("real_name") or slack_id
    except Exception:
        return slack_id


def find_repo(github_url: str, repo_slug: str) -> dict | None:
    candidate = github_url.rstrip("/").lower()
    for r in database.get_all_repos():
        gh = (r["github_url"] or "").rstrip("/").lower()
        if gh in (candidate, candidate + ".git"):
            return r
        if r["name"].lower() == repo_slug.lower():
            return r
    return None


# ── Parsers ───────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    text = re.sub(r"<@\w+>\s*", "", text)
    text = re.sub(r"<(https?://[^>]+)>", r"\1", text)
    return text.strip()


def parse_pr_url(text: str) -> dict | None:
    text = _clean(text)
    m = re.match(r"^https://github\.com/([^/\s]+)/([^/\s]+)/pull/(\d+)/?$",
                 text, re.IGNORECASE)
    if not m:
        return None
    owner, slug = m.group(1), m.group(2).removesuffix(".git")
    return {"owner": owner, "repo_slug": slug, "pr_number": int(m.group(3)),
            "github_url": f"https://github.com/{owner}/{slug}"}


def parse_clone(text: str) -> dict | None:
    text = _clean(text)
    # Accept both "clone ..." and "git clone ..."
    text = re.sub(r"^git\s+clone\s+", "clone ", text, flags=re.IGNORECASE)
    if not re.match(r"^clone\s+", text, re.IGNORECASE):
        return None
    parts = text.split()
    if len(parts) < 2:
        return None
    raw_url = parts[1].rstrip("/")

    # Strip embedded credentials: https://user:token@github.com/... → clean URL + extract token
    cred_match = re.match(r"^(https?)://[^:@]+:([^@]+)@(.+)$", raw_url)
    if cred_match:
        embedded_token = cred_match.group(2)
        raw_url = f"{cred_match.group(1)}://{cred_match.group(3)}"
    else:
        embedded_token = None

    url, name, token = raw_url, None, embedded_token
    i = 2
    while i < len(parts):
        p = parts[i]
        if p.lower().startswith("token="):
            token = p[6:]
        elif p.lower() == "--token" and i + 1 < len(parts):
            i += 1; token = parts[i]
        elif not p.startswith("-"):
            name = p
        i += 1
    if not name:
        name = url.rstrip("/").split("/")[-1].removesuffix(".git")
    return {"url": url, "name": name, "token": token}


# ── Worker ────────────────────────────────────────────────────────────────────

def worker(client):
    while True:
        job = job_queue.get()
        try:
            if job["type"] == "clone":
                run_clone(client, job["channel"], job["thread_ts"], job)
            elif job["type"] == "pr":
                run_smart_pr_review(client, job["channel"], job["thread_ts"], job)
        finally:
            job_queue.task_done()


# ── Event handler ─────────────────────────────────────────────────────────────

@app.event("message")
def handle_message(event, say):
    print(f"[smart-bot] event received: subtype={event.get('subtype')} bot_id={event.get('bot_id')} text={str(event.get('text',''))[:80]}")
    if event.get("bot_id") or event.get("subtype"):
        return

    text      = event.get("text", "")
    channel   = event.get("channel")
    thread_ts = event.get("thread_ts") or event.get("ts")
    slack_id  = event.get("user", "")

    # ── PR URL ─────────────────────────────────────────────────────────
    pr_url = parse_pr_url(text)
    if pr_url:
        owner, repo_slug = pr_url["owner"], pr_url["repo_slug"]
        pr_number        = pr_url["pr_number"]
        github_url       = pr_url["github_url"]

        matched = find_repo(github_url, repo_slug)
        if not matched:
            say(text=(
                    f"❌ *`{owner}/{repo_slug}` is not cloned yet.*\n"
                    f"Clone it first:\n"
                    f"`clone https://github.com/{owner}/{repo_slug}`\n"
                    f"_(add `token=ghp_xxx` for private repos)_"
                ), thread_ts=thread_ts)
            return

        repo_name = matched["name"]
        devs      = database.get_devs(repo_name)
        dev_row   = next((d for d in devs if d["slack_id"] == slack_id), None)

        if not dev_row:
            dev_name = get_display_name(app.client, slack_id)
            database.add_dev(repo_name, dev_name=dev_name, slack_id=slack_id)
            if devs:
                say(text=f"ℹ️ Added *{dev_name}* to `{repo_name}` automatically.",
                    thread_ts=thread_ts)
        else:
            dev_name = dev_row["dev_name"]

        say(text=(f"🔎 *Deep AI review queued*\n"
                  f"• `{owner}/{repo_slug}` · PR #{pr_number}\n"
                  f"• Dev: *{dev_name}*\n⏳"),
            thread_ts=thread_ts)

        job_queue.put({"type": "pr", "channel": channel, "thread_ts": thread_ts,
                       "repo": repo_name, "pr_number": pr_number,
                       "owner": owner, "repo_slug": repo_slug, "dev_name": dev_name})
        return

    # ── clone ──────────────────────────────────────────────────────────
    clone = parse_clone(text)
    if clone:
        say(text=(f"📦 *Clone queued*\n• `{clone['url']}`\n• Name: `{clone['name']}`"
                  + (" • Token: provided" if clone["token"] else "") + "\n⏳"),
            thread_ts=thread_ts)
        job_queue.put({"type": "clone", "channel": channel, "thread_ts": thread_ts,
                       "slack_id": slack_id, **clone})
        return

    # ── Fallback: detect likely mistakes and guide the user ────────────
    cleaned = _clean(text)

    # GitHub URL but not a PR URL
    if re.search(r"https://github\.com/", cleaned, re.IGNORECASE):
        if re.search(r"/pull/\d+", cleaned):
            say(text=(
                "❌ *PR URL không đúng format.*\n"
                "Chỉ paste URL dạng:\n"
                "`https://github.com/owner/repo/pull/123`\n"
                "_(không có gì thêm vào trước hoặc sau)_"
            ), thread_ts=thread_ts)
        else:
            say(text=(
                "ℹ️ Trông như một GitHub URL.\n\n"
                "*Để clone repo:*\n"
                "`clone https://github.com/owner/repo`\n"
                "`clone https://github.com/owner/repo token=ghp_xxx` ← private repo\n\n"
                "*Để review PR:*\n"
                "`https://github.com/owner/repo/pull/123` ← paste thẳng link PR"
            ), thread_ts=thread_ts)
        return

    # Looks like a clone attempt but wrong format
    if re.match(r"^(git\s+)?clone\s+", cleaned, re.IGNORECASE):
        say(text=(
            "❌ *Format clone không đúng.*\n\n"
            "*Cú pháp:*\n"
            "`clone <github-url>`\n"
            "`clone <github-url> <tên-repo>`\n"
            "`clone <github-url> token=ghp_xxx` ← repo private\n\n"
            "*Ví dụ:*\n"
            "`clone https://github.com/DucAnh03/tool_monitor`\n"
            "`clone https://github.com/org/private-repo token=ghp_abc123`"
        ), thread_ts=thread_ts)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    database.init_db()
    threading.Thread(target=worker, args=(app.client,), daemon=True).start()
    print("[smart-bot] Started.")
    print(f"[smart-bot] Clone dir: {CLONE_DIR}")
    print("[smart-bot] Paste a GitHub PR URL to trigger deep AI review.")
    SocketModeHandler(app, SLACK_APP_TOKEN).start()


if __name__ == "__main__":
    main()
