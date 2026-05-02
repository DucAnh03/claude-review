#!/usr/bin/env python3
"""
Slack Review Bot — nhận lệnh review commit / PR từ developer.

.env:
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_APP_TOKEN=xapp-...
  SLACK_SIGNING_SECRET=...

Commands:
  review [repo] [commit] [slack_id] | task description
  review-pr [repo] [pr_number] [slack_id]
"""

import os
import re
import threading
from pathlib import Path
from queue import Queue

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import db as database
import pr_review as pr_module
from review_core import (
    git_fetch_checkout,
    run_claude_review,
    extract_verdict,
    build_markdown,
    save_report,
)

load_dotenv()

SLACK_BOT_TOKEN      = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN      = os.environ["SLACK_APP_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]

VERDICT_ICON = {"OK": "✅", "WARNING": "⚠️", "SERIOUS": "🚨"}

job_queue: Queue = Queue()
app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)


# ── Parsers ──────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    return re.sub(r"<@\w+>\s*", "", text).strip()


def parse_commit(text: str) -> dict | None:
    text = _clean(text)
    m = re.match(r"^review\s+(\S+)\s+(\S+)\s+(\S+)\s*\|\s*(.+)$", text, re.IGNORECASE)
    if not m:
        return None
    return {"type": "commit", "repo": m.group(1), "commit": m.group(2),
            "dev": m.group(3), "task": m.group(4).strip()}


def parse_pr(text: str) -> dict | None:
    text = _clean(text)
    m = re.match(r"^review-pr\s+(\S+)\s+(\d+)\s+(\S+)$", text, re.IGNORECASE)
    if not m:
        return None
    return {"type": "pr", "repo": m.group(1),
            "pr_number": int(m.group(2)), "dev": m.group(3)}


# ── Helpers ───────────────────────────────────────────────────────────────────

def post(client, channel: str, text: str, thread_ts: str | None = None):
    client.chat_postMessage(channel=channel, text=text, thread_ts=thread_ts)


def upload_report(client, channel: str, report_path: Path, verdict: str, thread_ts: str | None = None):
    icon = VERDICT_ICON.get(verdict, "❓")
    client.files_upload_v2(
        channel=channel,
        file=str(report_path),
        filename=report_path.name,
        title=f"{icon} Review Report — {report_path.name}",
        initial_comment=f"{icon} *[{verdict}]* Review complete!",
        thread_ts=thread_ts,
    )


def resolve_dev(repo: str, slack_id: str) -> str | None:
    """Return dev_name for slack_id, or slack_id if no devs configured. None if invalid."""
    devs = database.get_devs(repo)
    if not devs:
        return slack_id
    row = next((d for d in devs if d["slack_id"] == slack_id), None)
    return row["dev_name"] if row else None


# ── Job runners ───────────────────────────────────────────────────────────────

def run_commit_job(client, channel: str, thread_ts: str, job: dict):
    repo     = job["repo"]
    commit   = job["commit"]
    dev_name = job["dev_name"]
    task     = job["task"]
    try:
        repo_dir = Path(database.get_repo_dir(repo))
        post(client, channel, f"🔄 Fetching `{commit}`...", thread_ts)
        git_fetch_checkout(repo_dir, commit)
        post(client, channel, "🤖 Claude reviewing... (~1-3 min)", thread_ts)
        output  = run_claude_review(repo_dir, task, repo_name=repo)
        verdict = extract_verdict(output)
        md      = build_markdown(repo, commit, task, dev_name, output, verdict)
        path    = save_report(repo, commit, md)
        database.add_review(repo_name=repo, commit_hash=commit, verdict=verdict,
                            report_path=str(path), task_desc=task, dev_name=dev_name)
        upload_report(client, channel, path, verdict, thread_ts)
    except Exception as e:
        post(client, channel, f"❌ Error: {e}", thread_ts)


def run_pr_job(client, channel: str, thread_ts: str, job: dict):
    repo      = job["repo"]
    pr_number = job["pr_number"]
    dev_name  = job["dev_name"]
    try:
        post(client, channel, f"🔍 Fetching PR #{pr_number}...", thread_ts)
        result  = pr_module.review_pr(repo, pr_number, dev_name)
        info    = result["pr_info"]
        verdict = result["verdict"]
        icon    = VERDICT_ICON.get(verdict, "❓")
        upload_report(client, channel, result["report_path"], verdict, thread_ts)
        post(client, channel,
             f"{icon} *PR #{pr_number} — {info['title']}*\n"
             f"• Author: `{info['author']}` | `{info['base_branch']}` ← `{info['head_branch']}`\n"
             f"• Verdict: *{verdict}*", thread_ts)
    except Exception as e:
        post(client, channel, f"❌ Error: {e}", thread_ts)


# ── Worker ────────────────────────────────────────────────────────────────────

def worker(client):
    while True:
        job = job_queue.get()
        try:
            if job["type"] == "commit":
                run_commit_job(client, job["channel"], job["thread_ts"], job)
            elif job["type"] == "pr":
                run_pr_job(client, job["channel"], job["thread_ts"], job)
        finally:
            job_queue.task_done()


# ── Event handler ─────────────────────────────────────────────────────────────

@app.event("message")
def handle_message(event, say):
    if event.get("bot_id") or event.get("subtype"):
        return

    text      = event.get("text", "")
    channel   = event.get("channel")
    thread_ts = event.get("thread_ts") or event.get("ts")
    slack_id  = event.get("user", "")

    parsed = parse_commit(text) or parse_pr(text)
    if not parsed:
        return

    repo = parsed["repo"]
    if not database.get_repo(repo):
        say(text=f"❌ Repo `{repo}` not found. Clone it first with the smart bot.",
            thread_ts=thread_ts)
        return

    dev_name = resolve_dev(repo, slack_id)
    if dev_name is None:
        devs = database.get_devs(repo)
        valid = [d["slack_id"] for d in devs if d["slack_id"]]
        say(text=f"❌ Slack ID `{slack_id}` not in repo `{repo}`.\nValid: {', '.join(f'`{s}`' for s in valid)}",
            thread_ts=thread_ts)
        return

    if parsed["type"] == "commit":
        say(text=(f"📋 *Review queued*\n• Repo: `{repo}` • Commit: `{parsed['commit']}`\n"
                  f"• Dev: *{dev_name}* • Task: _{parsed['task']}_\n⏳"),
            thread_ts=thread_ts)
        job_queue.put({"type": "commit", "channel": channel, "thread_ts": thread_ts,
                       "repo": repo, "commit": parsed["commit"],
                       "task": parsed["task"], "dev_name": dev_name})
    else:
        say(text=(f"🔎 *PR review queued*\n• Repo: `{repo}` • PR: `#{parsed['pr_number']}`\n"
                  f"• Dev: *{dev_name}*\n⏳"),
            thread_ts=thread_ts)
        job_queue.put({"type": "pr", "channel": channel, "thread_ts": thread_ts,
                       "repo": repo, "pr_number": parsed["pr_number"], "dev_name": dev_name})


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    database.init_db()
    threading.Thread(target=worker, args=(app.client,), daemon=True).start()
    print("[review-bot] Started. Commands: review / review-pr")
    SocketModeHandler(app, SLACK_APP_TOKEN).start()


if __name__ == "__main__":
    main()
