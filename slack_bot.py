#!/usr/bin/env python3
"""
Slack Bot - Code Review System
Socket Mode: không cần public URL hay ngrok.

Setup .env:
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_APP_TOKEN=xapp-...
  SLACK_SIGNING_SECRET=...

Usage dev trong channel #code-review:
  review [repo-name] [commit-hash] [dev-name] | mô tả task
  review tool_monitor b58927b duc | Thêm feature đọc CSV
"""

import os
import re
import threading
from pathlib import Path
from queue import Queue

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Import các module đã build
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

# --- Config -----------------------------------------------------------
SLACK_BOT_TOKEN      = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN      = os.environ["SLACK_APP_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
REVIEW_CHANNEL       = os.getenv("REVIEW_CHANNEL", "code-review")

VERDICT_ICON = {
    "OK":      "✅",
    "WARNING": "⚠️",
    "SERIOUS": "🚨",
}

# Job queue — xử lý tuần tự, tránh conflict git checkout
job_queue: Queue = Queue()

# --- Slack App --------------------------------------------------------
app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)


def _clean(text: str) -> str:
    return re.sub(r"<@\w+>\s*", "", text).strip()


def parse_message(text: str) -> dict | None:
    """review [repo] [commit] [dev] | task"""
    text = _clean(text)
    m = re.match(r"^review\s+(\S+)\s+(\S+)\s+(\S+)\s*\|\s*(.+)$", text, re.IGNORECASE)
    if not m:
        return None
    return {"type": "commit", "repo": m.group(1), "commit": m.group(2),
            "dev": m.group(3), "task": m.group(4).strip()}


def parse_pr_message(text: str) -> dict | None:
    """review-pr [repo] [pr_number] [dev]"""
    text = _clean(text)
    m = re.match(r"^review-pr\s+(\S+)\s+(\d+)\s+(\S+)$", text, re.IGNORECASE)
    if not m:
        return None
    return {"type": "pr", "repo": m.group(1),
            "pr_number": int(m.group(2)), "dev": m.group(3)}


def post_message(client, channel: str, text: str, thread_ts: str | None = None):
    client.chat_postMessage(
        channel=channel,
        text=text,
        thread_ts=thread_ts,
    )


def upload_report(client, channel: str, report_path: Path, verdict: str, thread_ts: str | None = None):
    icon  = VERDICT_ICON.get(verdict, "❓")
    title = f"{icon} Review Report — {report_path.name}"
    client.files_upload_v2(
        channel=channel,
        file=str(report_path),
        filename=report_path.name,
        title=title,
        initial_comment=f"{icon} *[{verdict}]* Review hoàn tất! Xem file đính kèm để biết chi tiết.",
        thread_ts=thread_ts,
    )


def _validate_repo_dev(client, channel: str, thread_ts: str,
                        repo: str, slack_id: str) -> bool:
    repo_row = database.get_repo(repo)
    print(f"[validate] repo='{repo}' found={repo_row is not None}")
    if not repo_row:
        post_message(client, channel,
            f"❌ Repo `{repo}` không tồn tại trong DB.\n"
            f"Vào Admin UI để thêm repo trước.", thread_ts)
        return False
    devs = database.get_devs(repo)
    print(f"[validate] slack_id='{slack_id}' devs_in_db={[d['slack_id'] for d in devs]}")
    if devs and not any(d["slack_id"] == slack_id for d in devs):
        slack_ids = [d["slack_id"] for d in devs if d["slack_id"]]
        post_message(client, channel,
            f"❌ Slack ID `{slack_id}` không có trong repo `{repo}`.\n"
            f"Danh sách Slack ID: {', '.join(f'`{s}`' for s in slack_ids)}", thread_ts)
        return False
    return True


def run_review_job(client, channel: str, thread_ts: str, parsed: dict):
    repo     = parsed["repo"]
    commit   = parsed["commit"]
    slack_id = parsed["dev"]
    dev_name = parsed.get("dev_name", slack_id)
    task     = parsed["task"]

    if not _validate_repo_dev(client, channel, thread_ts, repo, slack_id):
        return

    try:
        repo_dir = Path(database.get_repo_dir(repo))

        post_message(client, channel, f"🔄 Đang fetch & checkout `{commit}` cho repo `{repo}`...", thread_ts)
        git_fetch_checkout(repo_dir, commit)

        post_message(client, channel, "🤖 Claude đang review code... (~1-3 phút)", thread_ts)
        claude_output = run_claude_review(repo_dir, task, repo_name=repo)

        verdict = extract_verdict(claude_output)

        md_content  = build_markdown(repo, commit, task, dev_name, claude_output, verdict)
        report_path = save_report(repo, commit, md_content)

        database.add_review(
            repo_name=repo,
            commit_hash=commit,
            verdict=verdict,
            report_path=str(report_path),
            task_desc=task,
            dev_name=dev_name,
        )

        upload_report(client, channel, report_path, verdict, thread_ts)

    except SystemExit as e:
        post_message(client, channel, f"❌ Lỗi: {e}", thread_ts)
    except Exception as e:
        post_message(client, channel, f"❌ Unexpected error: {e}", thread_ts)


def run_pr_review_job(client, channel: str, thread_ts: str, parsed: dict):
    repo      = parsed["repo"]
    pr_number = parsed["pr_number"]
    slack_id  = parsed["dev"]
    dev_name  = parsed.get("dev_name", slack_id)

    if not _validate_repo_dev(client, channel, thread_ts, repo, slack_id):
        return

    try:
        post_message(client, channel, f"🔍 Đang fetch PR #{pr_number} từ GitHub...", thread_ts)
        result = pr_module.review_pr(repo, pr_number, dev_name)

        pr_info = result["pr_info"]
        verdict = result["verdict"]
        icon    = VERDICT_ICON.get(verdict, "❓")

        upload_report(client, channel, result["report_path"], verdict, thread_ts)
        post_message(
            client, channel,
            f"{icon} *PR #{pr_number} — {pr_info['title']}*\n"
            f"• Author: `{pr_info['author']}` | `{pr_info['base_branch']}` ← `{pr_info['head_branch']}`\n"
            f"• Verdict: *{verdict}*",
            thread_ts,
        )
    except (ValueError, RuntimeError) as e:
        post_message(client, channel, f"❌ Lỗi: {e}", thread_ts)
    except Exception as e:
        post_message(client, channel, f"❌ Unexpected error: {e}", thread_ts)


# --- Worker thread ----------------------------------------------------

def worker(client):
    while True:
        job = job_queue.get()
        if job is None:
            break
        try:
            parsed = job["parsed"]
            if parsed["type"] == "pr":
                run_pr_review_job(client, job["channel"], job["thread_ts"], parsed)
            else:
                run_review_job(client, job["channel"], job["thread_ts"], parsed)
        finally:
            job_queue.task_done()


# --- Event handler ----------------------------------------------------

@app.event("message")
def handle_message(event, say):
    # Bỏ qua bot message và edited message
    if event.get("bot_id") or event.get("subtype"):
        return

    text       = event.get("text", "")
    channel    = event.get("channel")
    thread_ts  = event.get("thread_ts") or event.get("ts")

    parsed = parse_message(text) or parse_pr_message(text)
    if not parsed:
        return

    repo     = parsed["repo"]
    slack_id = parsed["dev"]

    # Validate repo exists
    repo_row = database.get_repo(repo)
    if not repo_row:
        say(text=f"❌ Repo `{repo}` không tồn tại trong DB. Vào Admin UI để thêm.",
            thread_ts=thread_ts)
        return

    # Validate slack_id and resolve dev_name
    devs = database.get_devs(repo)
    dev_row = next((d for d in devs if d["slack_id"] == slack_id), None)
    if devs and dev_row is None:
        slack_ids = [d["slack_id"] for d in devs if d["slack_id"]]
        say(text=(f"❌ Slack ID `{slack_id}` không có trong repo `{repo}`.\n"
                  f"Danh sách Slack ID: {', '.join(f'`{s}`' for s in slack_ids)}"),
            thread_ts=thread_ts)
        return

    dev_name = dev_row["dev_name"] if dev_row else slack_id
    parsed = {**parsed, "dev_name": dev_name}

    if parsed["type"] == "commit":
        say(
            text=(
                f"📋 *Review request nhận được!*\n"
                f"• Repo: `{repo}`\n"
                f"• Commit: `{parsed['commit']}`\n"
                f"• Dev: *{dev_name}*\n"
                f"• Task: _{parsed['task']}_\n"
                f"⏳ Đang xếp vào queue..."
            ),
            thread_ts=thread_ts,
        )
    else:
        say(
            text=(
                f"🔎 *PR Review request nhận được!*\n"
                f"• Repo: `{repo}`\n"
                f"• PR: `#{parsed['pr_number']}`\n"
                f"• Dev: *{dev_name}*\n"
                f"⏳ Đang xếp vào queue..."
            ),
            thread_ts=thread_ts,
        )

    job_queue.put({
        "channel":   channel,
        "thread_ts": thread_ts,
        "parsed":    parsed,
    })


# --- Main -------------------------------------------------------------

def main():
    database.init_db()

    # Khởi động worker thread
    t = threading.Thread(target=worker, args=(app.client,), daemon=True)
    t.start()

    print("[bot] Starting Slack bot (Socket Mode)...")
    print(f"[bot] Listening in #{REVIEW_CHANNEL}")
    print("[bot] Format: review [repo] [commit] [dev] | mô tả task")

    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()


if __name__ == "__main__":
    main()