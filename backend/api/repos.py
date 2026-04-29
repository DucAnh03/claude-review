import subprocess
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

import db as database
from ..core.auth import require_api_key

router = APIRouter(prefix="/api/repos", tags=["repos"], dependencies=[Depends(require_api_key)])


# --- Pydantic models ----------------------------------------------------

class RepoCreate(BaseModel):
    name:         str = Field(..., min_length=1)
    local_dir:    str = Field(..., min_length=1)
    project_name: str = ""
    description:  str = ""
    github_url:   str = ""
    github_token: str = ""


class RepoUpdate(BaseModel):
    local_dir:    Optional[str] = None
    project_name: Optional[str] = None
    description:  Optional[str] = None
    github_url:   Optional[str] = None
    github_token: Optional[str] = None


class RepoClone(BaseModel):
    github_url:  str = Field(..., min_length=1)
    parent_dir:  str = Field(..., min_length=1, description="Folder to clone INTO (a subfolder will be created)")
    name:        Optional[str] = Field(None, description="Repo name in DB; defaults to GitHub repo name")
    project_name: str = ""
    description: str = ""
    github_token: str = ""


class SkillsBody(BaseModel):
    skills: list[str]


def _row_to_dict(row) -> dict:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


# --- Endpoints ---------------------------------------------------------

@router.get("")
def list_repos():
    rows = database.get_all_repos()
    return [_row_to_dict(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_repo(body: RepoCreate):
    try:
        database.add_repo(
            body.name.strip(), body.local_dir.strip(),
            body.project_name, body.description, body.github_url, body.github_token,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _row_to_dict(database.get_repo(body.name.strip()))


@router.post("/clone", status_code=status.HTTP_201_CREATED)
def clone_repo(body: RepoClone):
    parent = Path(body.parent_dir.strip())
    if not parent.is_dir():
        raise HTTPException(status_code=400, detail=f"parent_dir '{parent}' does not exist")

    # Derive repo name from URL if not given
    derived = body.github_url.rstrip("/").split("/")[-1].removesuffix(".git")
    repo_name = (body.name or derived).strip()
    target = parent / repo_name

    if target.exists():
        raise HTTPException(status_code=409, detail=f"Target dir already exists: {target}")

    # Embed token into URL for private repos
    clone_url = body.github_url.strip()
    if body.github_token and clone_url.startswith("https://"):
        clone_url = clone_url.replace("https://", f"https://oauth2:{body.github_token}@", 1)

    result = subprocess.run(
        ["git", "clone", clone_url, str(target)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise HTTPException(status_code=502, detail=f"git clone failed: {result.stderr.strip()[:500]}")

    try:
        database.add_repo(
            repo_name, str(target.resolve()),
            body.project_name, body.description, body.github_url, body.github_token,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "ok", "repo": _row_to_dict(database.get_repo(repo_name)), "cloned_to": str(target)}


@router.get("/{name}")
def get_repo(name: str):
    row = database.get_repo(name)
    if not row:
        raise HTTPException(status_code=404, detail=f"Repo '{name}' not found")
    return _row_to_dict(row)


@router.patch("/{name}")
def update_repo(name: str, body: RepoUpdate):
    if not database.get_repo(name):
        raise HTTPException(status_code=404, detail=f"Repo '{name}' not found")
    database.update_repo(
        name,
        local_dir    = body.local_dir,
        project_name = body.project_name,
        desc         = body.description,
        github_url   = body.github_url,
        github_token = body.github_token,
    )
    return _row_to_dict(database.get_repo(name))


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repo(name: str):
    try:
        database.remove_repo(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{name}/skills")
def get_skills(name: str):
    if not database.get_repo(name):
        raise HTTPException(status_code=404, detail=f"Repo '{name}' not found")
    return {"skills": database.get_repo_skills(name)}


@router.put("/{name}/skills")
def set_skills(name: str, body: SkillsBody):
    if not database.get_repo(name):
        raise HTTPException(status_code=404, detail=f"Repo '{name}' not found")
    database.set_repo_skills(name, body.skills)
    return {"skills": database.get_repo_skills(name)}
