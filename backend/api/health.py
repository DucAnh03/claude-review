import shutil
import sys

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])  # NO auth — public for tunnel checks


@router.get("/health")
def health():
    claude_bin = "claude.cmd" if sys.platform == "win32" else "claude"
    return {
        "status": "ok",
        "claude": shutil.which(claude_bin) is not None,
        "git":    shutil.which("git") is not None,
        "platform": sys.platform,
    }
