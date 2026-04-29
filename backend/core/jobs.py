"""
Background job system for review tasks.

Reviews run sequentially in a single worker thread to avoid git checkout conflicts
on the same repo (same pattern as slack_bot.py).
"""

import threading
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from queue import Queue

import db as database
import pr_review
from review_core import (
    git_fetch_checkout,
    run_claude_review,
    extract_verdict,
    build_markdown,
    save_report,
)


class JobManager:
    def __init__(self) -> None:
        self._queue: Queue[str] = Queue()
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None

    # --- Lifecycle ----------------------------------------------------

    def start(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._loop, daemon=True, name="review-worker")
        self._worker.start()

    def _loop(self) -> None:
        while True:
            job_id = self._queue.get()
            if job_id is None:
                break
            try:
                self._run(job_id)
            except Exception:
                traceback.print_exc()
            finally:
                self._queue.task_done()

    # --- Public API ---------------------------------------------------

    def submit_commit(self, repo: str, commit: str, task: str, dev_name: str) -> str:
        return self._submit("commit", {
            "repo": repo, "commit": commit, "task": task, "dev_name": dev_name,
        })

    def submit_pr(self, repo: str, pr_number: int, dev_name: str) -> str:
        return self._submit("pr", {
            "repo": repo, "pr_number": pr_number, "dev_name": dev_name,
        })

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def list_recent(self, limit: int = 20) -> list[dict]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda j: j["created_at"], reverse=True)
            return [dict(j) for j in jobs[:limit]]

    # --- Internals ----------------------------------------------------

    def _submit(self, job_type: str, params: dict) -> str:
        job_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "type": job_type,
                "status": "queued",
                "created_at": _now(),
                "started_at": None,
                "finished_at": None,
                "params": params,
                "result": None,
                "error": None,
            }
        self._queue.put(job_id)
        return job_id

    def _update(self, job_id: str, **fields) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(fields)

    def _run(self, job_id: str) -> None:
        job = self.get(job_id)
        if not job:
            return
        self._update(job_id, status="running", started_at=_now())
        try:
            if job["type"] == "commit":
                result = self._run_commit(job["params"])
            elif job["type"] == "pr":
                result = self._run_pr(job["params"])
            else:
                raise ValueError(f"unknown job type: {job['type']}")
            self._update(job_id, status="done", result=result, finished_at=_now())
        except Exception as e:
            self._update(job_id, status="failed", error=str(e), finished_at=_now())
            traceback.print_exc()

    def _run_commit(self, params: dict) -> dict:
        repo     = params["repo"]
        commit   = params["commit"]
        task     = params["task"]
        dev_name = params["dev_name"]

        repo_dir = Path(database.get_repo_dir(repo))
        git_fetch_checkout(repo_dir, commit)

        claude_output = run_claude_review(repo_dir, task, repo_name=repo)
        verdict       = extract_verdict(claude_output)

        md_content  = build_markdown(repo, commit, task, dev_name, claude_output, verdict)
        report_path = save_report(repo, commit, md_content)

        review_id = database.add_review(
            repo_name=repo, commit_hash=commit, verdict=verdict,
            report_path=str(report_path), task_desc=task, dev_name=dev_name,
        )
        return {
            "review_id":   review_id,
            "verdict":     verdict,
            "report_path": str(report_path),
        }

    def _run_pr(self, params: dict) -> dict:
        result = pr_review.review_pr(
            repo_name=params["repo"],
            pr_number=params["pr_number"],
            dev_name=params["dev_name"],
        )
        return {
            "verdict":     result["verdict"],
            "report_path": str(result["report_path"]),
            "pr_info":     result["pr_info"],
        }


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# Singleton
job_manager = JobManager()
