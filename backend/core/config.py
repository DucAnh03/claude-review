import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (one level up from backend/)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

API_KEY = os.getenv("API_KEY", "")
ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

SKILLS_DIR  = ROOT_DIR / "skills"
RULES_DIR   = ROOT_DIR / "rules"
REVIEWS_DIR = ROOT_DIR / "reviews"
