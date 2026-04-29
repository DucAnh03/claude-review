"""
FastAPI backend for the Code Review system.

Run from project root:
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
"""

import sys
from pathlib import Path

# Make the existing top-level modules (db, review_core, pr_review, crypto)
# importable from anywhere within the backend package.
_PARENT = str(Path(__file__).parent.parent)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)
