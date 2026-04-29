from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

import db as database
import crypto
from ..core.auth import require_api_key

router = APIRouter(prefix="/api/repos", tags=["devs"], dependencies=[Depends(require_api_key)])


class DevCreate(BaseModel):
    dev_name:        str = Field(..., min_length=1)
    slack_id:        str = Field(..., min_length=1)
    github_username: str = ""
    github_token:    str = ""


class DevUpdate(BaseModel):
    slack_id:     Optional[str] = None
    github_token: Optional[str] = None


def _dev_row_to_dict(row) -> dict:
    if row is None:
        return None
    d = {k: row[k] for k in row.keys()}
    # Mask token before sending to client
    enc = d.pop("github_token", "")
    if enc:
        try:
            d["github_token_masked"] = crypto.mask(crypto.decrypt(enc))
            d["github_token_set"]    = True
        except Exception:
            d["github_token_masked"] = "—"
            d["github_token_set"]    = True
    else:
        d["github_token_masked"] = None
        d["github_token_set"]    = False
    return d


@router.get("/{repo_name}/devs")
def list_devs(repo_name: str):
    if not database.get_repo(repo_name):
        raise HTTPException(status_code=404, detail=f"Repo '{repo_name}' not found")
    rows = database.get_devs(repo_name)
    return [_dev_row_to_dict(r) for r in rows]


@router.post("/{repo_name}/devs", status_code=status.HTTP_201_CREATED)
def create_dev(repo_name: str, body: DevCreate):
    if not database.get_repo(repo_name):
        raise HTTPException(status_code=404, detail=f"Repo '{repo_name}' not found")
    try:
        database.add_dev(
            repo_name, body.dev_name.strip(), body.slack_id.strip(),
            body.github_username, body.github_token,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    devs = database.get_devs(repo_name)
    new_dev = next((d for d in devs if d["dev_name"] == body.dev_name.strip()), None)
    return _dev_row_to_dict(new_dev)


@router.patch("/{repo_name}/devs/{dev_name}")
def update_dev(repo_name: str, dev_name: str, body: DevUpdate):
    devs = database.get_devs(repo_name)
    if not any(d["dev_name"] == dev_name for d in devs):
        raise HTTPException(status_code=404, detail=f"Dev '{dev_name}' not found in repo '{repo_name}'")
    try:
        if body.slack_id is not None:
            database.update_dev_slack_id(repo_name, dev_name, body.slack_id)
        if body.github_token:
            database.update_dev_token(repo_name, dev_name, body.github_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    devs = database.get_devs(repo_name)
    return _dev_row_to_dict(next((d for d in devs if d["dev_name"] == dev_name), None))


@router.delete("/{repo_name}/devs/{dev_name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dev(repo_name: str, dev_name: str):
    try:
        database.remove_dev(repo_name, dev_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
