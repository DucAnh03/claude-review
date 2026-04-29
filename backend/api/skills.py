import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..core.auth import require_api_key
from ..core.config import SKILLS_DIR

router = APIRouter(prefix="/api/skills", tags=["skills"], dependencies=[Depends(require_api_key)])

_SAFE_FILENAME = re.compile(r"^[a-z0-9_\-]+\.md$")


class SkillBody(BaseModel):
    content: str = Field(..., description="Full markdown content of the skill file")


def _safe_path(filename: str):
    """Return the resolved path under SKILLS_DIR or raise 400."""
    if not _SAFE_FILENAME.match(filename):
        raise HTTPException(status_code=400, detail="Filename must match [a-z0-9_-]+.md")
    target = (SKILLS_DIR / filename).resolve()
    if SKILLS_DIR.resolve() not in target.parents and target.parent != SKILLS_DIR.resolve():
        raise HTTPException(status_code=400, detail="Path traversal detected")
    return target


@router.get("")
def list_skills():
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for p in sorted(SKILLS_DIR.glob("*.md")):
        items.append({
            "filename":  p.name,
            "size":      p.stat().st_size,
            "modified":  p.stat().st_mtime,
        })
    return items


@router.get("/{filename}")
def get_skill(filename: str):
    target = _safe_path(filename)
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Skill file '{filename}' not found")
    return {
        "filename": filename,
        "content":  target.read_text(encoding="utf-8"),
    }


@router.put("/{filename}")
def update_skill(filename: str, body: SkillBody):
    target = _safe_path(filename)
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    target.write_text(body.content, encoding="utf-8")
    return {
        "filename": filename,
        "size":     target.stat().st_size,
        "status":   "saved",
    }


@router.delete("/{filename}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(filename: str):
    target = _safe_path(filename)
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Skill file '{filename}' not found")
    target.unlink()
