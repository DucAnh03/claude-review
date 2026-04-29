#!/usr/bin/env python3
"""
DB module: quản lý repo mapping, devs, và review history bằng SQLite.
"""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import crypto

DB_PATH = Path(__file__).parent / "review_system.db"
VALID_VERDICTS = {"OK", "WARNING", "SERIOUS", "UNKNOWN"}

_initialized = False


# --- Init -------------------------------------------------------------

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    global _initialized
    if _initialized:
        return
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS repos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL UNIQUE,
            project_name  TEXT DEFAULT '',
            local_dir     TEXT NOT NULL,
            description   TEXT DEFAULT '',
            github_url    TEXT DEFAULT '',
            github_token  TEXT DEFAULT '',
            created_at    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS repo_skills (
            repo_name  TEXT NOT NULL,
            skill_name TEXT NOT NULL,
            PRIMARY KEY (repo_name, skill_name),
            FOREIGN KEY (repo_name) REFERENCES repos(name) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS repo_devs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_name       TEXT NOT NULL,
            dev_name        TEXT NOT NULL,
            slack_id        TEXT NOT NULL DEFAULT '',
            github_username TEXT DEFAULT '',
            github_token    TEXT DEFAULT '',
            created_at      TEXT NOT NULL,
            FOREIGN KEY (repo_name) REFERENCES repos(name) ON DELETE CASCADE,
            UNIQUE(repo_name, dev_name),
            UNIQUE(repo_name, slack_id)
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_name   TEXT NOT NULL,
            commit_hash TEXT NOT NULL,
            task_desc   TEXT DEFAULT '',
            dev_name    TEXT DEFAULT '',
            verdict     TEXT NOT NULL,
            report_path TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (repo_name) REFERENCES repos(name)
        );

        CREATE INDEX IF NOT EXISTS idx_reviews_repo    ON reviews(repo_name);
        CREATE INDEX IF NOT EXISTS idx_reviews_verdict ON reviews(verdict);
        CREATE INDEX IF NOT EXISTS idx_reviews_dev     ON reviews(dev_name);
        CREATE INDEX IF NOT EXISTS idx_devs_repo       ON repo_devs(repo_name);

        -- Migrate: add new columns to repos if upgrading from old schema
        """)
        # Safe migration: add columns if they don't exist
        for col, default in [("github_url", "''"), ("github_token", "''"),
                              ("project_name", "''")]:
            try:
                conn.execute(f"ALTER TABLE repos ADD COLUMN {col} TEXT DEFAULT {default}")
            except sqlite3.OperationalError:
                pass
        for col, default in [("github_token", "''"), ("slack_id", "''")]:
            try:
                conn.execute(f"ALTER TABLE repo_devs ADD COLUMN {col} TEXT DEFAULT {default}")
            except sqlite3.OperationalError:
                pass
    _initialized = True


# --- Repo CRUD --------------------------------------------------------

def add_repo(name: str, local_dir: str, project_name: str = "", desc: str = "",
             github_url: str = "", github_token: str = "") -> None:
    path = Path(local_dir)
    if not path.is_dir():
        raise ValueError(f"'{local_dir}' không phải thư mục hợp lệ.")
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO repos (name, project_name, local_dir, description, github_url, github_token, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, project_name, str(path.resolve()), desc, github_url, github_token, _now()),
        )


def update_repo(name: str, local_dir: str = None, project_name: str = None,
                desc: str = None, github_url: str = None, github_token: str = None) -> None:
    fields, params = [], []
    if local_dir is not None:
        fields.append("local_dir = ?"); params.append(local_dir)
    if project_name is not None:
        fields.append("project_name = ?"); params.append(project_name)
    if desc is not None:
        fields.append("description = ?"); params.append(desc)
    if github_url is not None:
        fields.append("github_url = ?"); params.append(github_url)
    if github_token is not None:
        fields.append("github_token = ?"); params.append(github_token)
    if not fields:
        return
    params.append(name)
    with get_conn() as conn:
        conn.execute(f"UPDATE repos SET {', '.join(fields)} WHERE name = ?", params)


def remove_repo(name: str) -> None:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM repos WHERE name = ?", (name,))
        if cur.rowcount == 0:
            raise ValueError(f"Repo '{name}' không tồn tại.")


def get_repo(name: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM repos WHERE name = ?", (name,)).fetchone()


def get_repo_dir(name: str) -> str:
    row = get_repo(name)
    if not row:
        raise SystemExit(f"ERROR: Repo '{name}' không có trong DB.")
    return row["local_dir"]


def get_all_repos() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM repos ORDER BY name").fetchall()


# --- Skills -----------------------------------------------------------

def get_repo_skills(repo_name: str) -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT skill_name FROM repo_skills WHERE repo_name = ? ORDER BY skill_name",
            (repo_name,)
        ).fetchall()
    return [r["skill_name"] for r in rows]


def set_repo_skills(repo_name: str, skills: list[str]) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM repo_skills WHERE repo_name = ?", (repo_name,))
        for skill in skills:
            conn.execute(
                "INSERT OR IGNORE INTO repo_skills (repo_name, skill_name) VALUES (?, ?)",
                (repo_name, skill)
            )


# --- Dev CRUD ---------------------------------------------------------

def add_dev(repo_name: str, dev_name: str, slack_id: str = "",
            github_username: str = "", github_token: str = "") -> None:
    if not slack_id.strip():
        raise ValueError("Slack ID không được để trống.")
    # Check unique slack_id per repo
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT dev_name FROM repo_devs WHERE repo_name = ? AND slack_id = ?",
            (repo_name, slack_id.strip())
        ).fetchone()
        if existing and existing["dev_name"] != dev_name:
            raise ValueError(f"Slack ID '{slack_id}' đã được dùng bởi '{existing['dev_name']}'.")
        encrypted = crypto.encrypt(github_token) if github_token else ""
        conn.execute(
            """INSERT OR REPLACE INTO repo_devs
               (repo_name, dev_name, slack_id, github_username, github_token, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (repo_name, dev_name, slack_id.strip(), github_username, encrypted, _now()),
        )


def update_dev_token(repo_name: str, dev_name: str, github_token: str) -> None:
    encrypted = crypto.encrypt(github_token) if github_token else ""
    with get_conn() as conn:
        conn.execute(
            "UPDATE repo_devs SET github_token = ? WHERE repo_name = ? AND dev_name = ?",
            (encrypted, repo_name, dev_name),
        )


def update_dev_slack_id(repo_name: str, dev_name: str, new_slack_id: str) -> None:
    if not new_slack_id.strip():
        raise ValueError("Slack ID không được để trống.")
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT dev_name FROM repo_devs WHERE repo_name = ? AND slack_id = ?",
            (repo_name, new_slack_id.strip())
        ).fetchone()
        if existing and existing["dev_name"] != dev_name:
            raise ValueError(f"Slack ID '{new_slack_id}' đã được dùng bởi '{existing['dev_name']}'.")
        conn.execute(
            "UPDATE repo_devs SET slack_id = ? WHERE repo_name = ? AND dev_name = ?",
            (new_slack_id.strip(), repo_name, dev_name),
        )


def get_dev_by_slack_id(repo_name: str, slack_id: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM repo_devs WHERE repo_name = ? AND slack_id = ?",
            (repo_name, slack_id)
        ).fetchone()


def get_dev_token(repo_name: str, dev_name: str) -> str:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT github_token FROM repo_devs WHERE repo_name = ? AND dev_name = ?",
            (repo_name, dev_name),
        ).fetchone()
    if not row or not row["github_token"]:
        return ""
    return crypto.decrypt(row["github_token"])


def remove_dev(repo_name: str, dev_name: str) -> None:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM repo_devs WHERE repo_name = ? AND dev_name = ?",
            (repo_name, dev_name),
        )
        if cur.rowcount == 0:
            raise ValueError(f"Dev '{dev_name}' không tồn tại trong repo '{repo_name}'.")


def get_devs(repo_name: str) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM repo_devs WHERE repo_name = ? ORDER BY dev_name",
            (repo_name,),
        ).fetchall()


# --- Review history ---------------------------------------------------

def add_review(repo_name: str, commit_hash: str, verdict: str, report_path: str,
               task_desc: str = "", dev_name: str = "") -> int:
    if verdict.upper() not in VALID_VERDICTS:
        raise ValueError(f"verdict phải là một trong {VALID_VERDICTS}")
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO reviews
               (repo_name, commit_hash, task_desc, dev_name, verdict, report_path, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (repo_name, commit_hash, task_desc, dev_name, verdict, report_path, _now()),
        )
        return cur.lastrowid


def get_reviews(repo_name: str | None = None, verdict: str | None = None,
                dev_name: str | None = None, limit: int = 50) -> list[sqlite3.Row]:
    query = "SELECT * FROM reviews WHERE 1=1"
    params: list = []
    if repo_name:
        query += " AND repo_name = ?"; params.append(repo_name)
    if verdict:
        query += " AND verdict = ?"; params.append(verdict)
    if dev_name:
        query += " AND dev_name = ?"; params.append(dev_name)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        return conn.execute(query, params).fetchall()


def get_stats() -> dict:
    with get_conn() as conn:
        total   = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        ok      = conn.execute("SELECT COUNT(*) FROM reviews WHERE verdict='OK'").fetchone()[0]
        warning = conn.execute("SELECT COUNT(*) FROM reviews WHERE verdict='WARNING'").fetchone()[0]
        serious = conn.execute("SELECT COUNT(*) FROM reviews WHERE verdict='SERIOUS'").fetchone()[0]
        by_repo = conn.execute(
            "SELECT repo_name, COUNT(*) as c FROM reviews GROUP BY repo_name ORDER BY c DESC"
        ).fetchall()
        by_dev  = conn.execute(
            "SELECT dev_name, COUNT(*) as c FROM reviews WHERE dev_name != '' GROUP BY dev_name ORDER BY c DESC LIMIT 10"
        ).fetchall()
        by_day  = conn.execute(
            "SELECT substr(created_at,1,10) as day, COUNT(*) as c FROM reviews GROUP BY day ORDER BY day DESC LIMIT 30"
        ).fetchall()
    return {
        "total": total, "ok": ok, "warning": warning, "serious": serious,
        "by_repo": [dict(r) for r in by_repo],
        "by_dev":  [dict(r) for r in by_dev],
        "by_day":  [dict(r) for r in by_day],
    }


# --- Helpers ----------------------------------------------------------

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# --- CLI --------------------------------------------------------------

def main():
    init_db()
    parser = argparse.ArgumentParser(description="Review System DB manager")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("add-repo")
    p.add_argument("name"); p.add_argument("local_dir")
    p.add_argument("--desc", default=""); p.add_argument("--github-url", default="")
    p.add_argument("--github-token", default="")

    p = sub.add_parser("remove-repo"); p.add_argument("name")
    sub.add_parser("list-repos")

    p = sub.add_parser("add-dev")
    p.add_argument("repo"); p.add_argument("dev_name")
    p.add_argument("--slack", default=""); p.add_argument("--github", default="")

    p = sub.add_parser("remove-dev"); p.add_argument("repo"); p.add_argument("dev_name")
    p = sub.add_parser("list-devs"); p.add_argument("repo")

    p = sub.add_parser("add-review")
    p.add_argument("repo"); p.add_argument("commit"); p.add_argument("verdict")
    p.add_argument("report_path"); p.add_argument("--task", default=""); p.add_argument("--dev", default="")

    p = sub.add_parser("list-reviews")
    p.add_argument("--repo", default=None); p.add_argument("--limit", type=int, default=20)

    sub.add_parser("stats")
    args = parser.parse_args()

    if args.cmd == "add-repo":
        add_repo(args.name, args.local_dir, args.desc, args.github_url, args.github_token)
        print(f"[db] Repo '{args.name}' đã thêm.")
    elif args.cmd == "remove-repo":
        remove_repo(args.name); print(f"[db] Repo '{args.name}' đã xóa.")
    elif args.cmd == "list-repos":
        for r in get_all_repos():
            print(f"{r['name']:<20} {r['local_dir']:<35} {r['github_url'] or '—'}")
    elif args.cmd == "add-dev":
        add_dev(args.repo, args.dev_name, args.slack, args.github)
        print(f"[db] Dev '{args.dev_name}' đã thêm vào '{args.repo}'.")
    elif args.cmd == "remove-dev":
        remove_dev(args.repo, args.dev_name); print(f"[db] Dev '{args.dev_name}' đã xóa.")
    elif args.cmd == "list-devs":
        for d in get_devs(args.repo):
            print(f"{d['dev_name']:<20} slack:{d['slack_id']:<15} github:{d['github_username']}")
    elif args.cmd == "add-review":
        rid = add_review(args.repo, args.commit, args.verdict, args.report_path, args.task, args.dev)
        print(f"[db] Review #{rid} đã lưu.")
    elif args.cmd == "list-reviews":
        for r in get_reviews(args.repo, limit=args.limit):
            print(f"#{r['id']} {r['repo_name']} {r['commit_hash'][:8]} {r['verdict']} {r['dev_name']} {r['created_at'][:16]}")
    elif args.cmd == "stats":
        s = get_stats()
        print(f"Total: {s['total']} | OK: {s['ok']} | Warning: {s['warning']} | Serious: {s['serious']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
