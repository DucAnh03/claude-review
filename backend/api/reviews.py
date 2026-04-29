from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

import db as database
from ..core.auth import require_api_key
from ..core.jobs import job_manager

router = APIRouter(prefix="/api", tags=["reviews"], dependencies=[Depends(require_api_key)])


class CommitReviewRequest(BaseModel):
    repo:     str = Field(..., min_length=1)
    commit:   str = Field(..., min_length=1)
    task:     str = ""
    slack_id: str = Field(..., min_length=1, description="Dev's Slack ID (short identifier)")


class PRReviewRequest(BaseModel):
    repo:      str = Field(..., min_length=1)
    pr_number: int = Field(..., gt=0)
    slack_id:  str = Field(..., min_length=1)


def _row_to_dict(row) -> dict:
    return {k: row[k] for k in row.keys()}


def _resolve_dev_name(repo: str, slack_id: str) -> str:
    """Look up a dev by slack_id; return dev_name. If no devs configured, allow any slack_id."""
    devs = database.get_devs(repo)
    if not devs:
        return slack_id  # No devs configured → allow free-form
    match = next((d for d in devs if d["slack_id"] == slack_id), None)
    if not match:
        valid = [d["slack_id"] for d in devs if d["slack_id"]]
        raise HTTPException(
            status_code=400,
            detail=f"Slack ID '{slack_id}' not found in repo '{repo}'. Valid: {valid}",
        )
    return match["dev_name"]


# --- Review history --------------------------------------------------

@router.get("/reviews")
def list_reviews(
    repo:    Optional[str] = Query(None),
    verdict: Optional[str] = Query(None),
    dev:     Optional[str] = Query(None, description="Dev name (not slack_id)"),
    limit:   int           = Query(50, ge=1, le=500),
):
    rows = database.get_reviews(repo_name=repo, verdict=verdict, dev_name=dev, limit=limit)
    return [_row_to_dict(r) for r in rows]


@router.get("/reviews/{review_id}")
def get_review(review_id: int):
    rows = database.get_reviews(limit=500)
    row = next((r for r in rows if r["id"] == review_id), None)
    if not row:
        raise HTTPException(status_code=404, detail=f"Review #{review_id} not found")
    data = _row_to_dict(row)
    report = Path(data["report_path"])
    if report.exists():
        data["content"] = report.read_text(encoding="utf-8")
    else:
        data["content"] = None
        data["content_error"] = f"Report file not found: {report}"
    return data


# --- Trigger reviews -------------------------------------------------

@router.post("/reviews/commit", status_code=status.HTTP_202_ACCEPTED)
def trigger_commit_review(body: CommitReviewRequest):
    if not database.get_repo(body.repo):
        raise HTTPException(status_code=404, detail=f"Repo '{body.repo}' not found")
    dev_name = _resolve_dev_name(body.repo, body.slack_id)
    job_id = job_manager.submit_commit(body.repo, body.commit, body.task, dev_name)
    return {"job_id": job_id, "type": "commit", "status": "queued", "dev_name": dev_name}


@router.post("/reviews/pr", status_code=status.HTTP_202_ACCEPTED)
def trigger_pr_review(body: PRReviewRequest):
    if not database.get_repo(body.repo):
        raise HTTPException(status_code=404, detail=f"Repo '{body.repo}' not found")
    dev_name = _resolve_dev_name(body.repo, body.slack_id)
    job_id = job_manager.submit_pr(body.repo, body.pr_number, dev_name)
    return {"job_id": job_id, "type": "pr", "status": "queued", "dev_name": dev_name}


# --- Job status ------------------------------------------------------

@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job


@router.get("/jobs")
def list_jobs(limit: int = Query(20, ge=1, le=100)):
    return job_manager.list_recent(limit=limit)
