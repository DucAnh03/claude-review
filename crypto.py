#!/usr/bin/env python3
"""
Token encryption using Fernet symmetric encryption.
Master key loaded from MASTER_KEY in .env — never stored in DB.
"""

import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

load_dotenv()

_DB_PATH = Path(__file__).parent / ".env"


def get_master_key() -> bytes:
    key = os.environ.get("MASTER_KEY", "")
    if not key:
        raise RuntimeError(
            "MASTER_KEY chưa có trong .env.\n"
            "Chạy: python crypto.py generate-key  để tạo key mới."
        )
    return key.encode()


def encrypt(plaintext: str) -> str:
    """Encrypt a token string. Returns base64 ciphertext string."""
    if not plaintext:
        return ""
    f = Fernet(get_master_key())
    return f.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a ciphertext string. Returns plaintext token."""
    if not ciphertext:
        return ""
    try:
        f = Fernet(get_master_key())
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        raise ValueError("Không decrypt được token — MASTER_KEY có thể đã thay đổi.")


def generate_key() -> str:
    """Generate a new Fernet key (base64 url-safe, 32 bytes)."""
    return Fernet.generate_key().decode()


def mask(token: str) -> str:
    """Return masked token for display: ghp_xxxx...xxxx"""
    if not token or len(token) < 8:
        return "—"
    return f"{token[:6]}...{token[-4:]}"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "generate-key":
        key = generate_key()
        print(f"\nThêm dòng này vào .env:\n\nMASTER_KEY={key}\n")
    else:
        print("Usage: python crypto.py generate-key")
