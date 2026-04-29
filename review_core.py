#!/usr/bin/env python3
"""
Core review script: checkout a commit and run Claude Code review.
Usage: python review_core.py --repo <repo-name> --commit <hash> [--task "..."] [--dev "name"]
Repo paths are stored in review_system.db (managed by db.py).
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import db as _db

OUTPUT_DIR = Path(__file__).parent / "reviews"
AGENTS_DIR = Path(__file__).parent / ".claude" / "agents"
RULES_DIR  = Path(__file__).parent / "rules"
SKILLS_DIR = Path(__file__).parent / "skills"

# Rule files applied in this order — order matters (security overrides everything)
_RULES_ORDER = [
    ("security.md",       "BLOCKING, no exceptions"),
    ("error-handling.md", "SERIOUS if missing"),
    ("code-style.md",     "WARNING if violated"),
]

VERDICT_LABELS = {
    "OK":      "✅ OK",
    "WARNING": "⚠️ Warning",
    "SERIOUS": "🚨 Serious",
}


def _build_skill_section(repo_name: str) -> str:
    if not repo_name:
        return "Detect the main language(s) from the diff and apply relevant best practices."
    skills = _db.get_repo_skills(repo_name)
    if not skills:
        return "Detect the main language(s) from the diff and apply relevant best practices."
    read_lines = []
    for skill in skills:
        filename = skill.lower().replace("/", "").replace(" ", "_") + ".md"
        p = SKILLS_DIR / filename
        if p.exists():
            read_lines.append(f'- Read "{p}"')
    skill_list = ", ".join(skills)
    if read_lines:
        return f"This repo uses: {skill_list}. Read the skill guideline files:\n" + "\n".join(read_lines)
    return f"This repo uses: {skill_list}. Apply relevant best practices for these technologies."


def _build_rules_section() -> str:
    lines = []
    for i, (filename, note) in enumerate(_RULES_ORDER, 1):
        p = RULES_DIR / filename
        if p.exists():
            lines.append(f'{i}. Read "{p}" — {note}')
    return "\n".join(lines)


def _skill_names(repo_name: str) -> str:
    if not repo_name:
        return "detected language"
    skills = _db.get_repo_skills(repo_name)
    return ", ".join(skills) if skills else "detected language"


def _build_commit_prompt(task_desc: str, repo_name: str) -> str:
    agent_path = AGENTS_DIR / "code-reviewer.md"
    return f"""\
Read "{agent_path}" and adopt that role completely.

## Step 1 — Get the diff
Run: git show HEAD --stat
Run: git show HEAD

## Step 2 — Load skill guidelines
{_build_skill_section(repo_name)}

## Step 3 — Apply rules (read ALL in this order before reviewing)
{_build_rules_section()}

## Step 4 — Analyse
Task context from developer: {task_desc or "(no description provided)"}

For each changed file, read the full file to understand context.
Grep for any changed function or class to find other callers.

## Step 5 — Output format (STRICT)
Output EXACTLY these four sections, nothing else:

## Summary
One paragraph describing what this commit changes.

## Issues
REQUIRED: write all four blocks below. Never skip a block, even if the result is [OK] or [N/A].

**Security** *(from security.md)*
- **[OK/WARNING/SERIOUS]** ...

**Error Handling** *(from error-handling.md)*
- **[OK/WARNING/SERIOUS]** ...

**Code Style** *(from code-style.md)*
- **[OK/WARNING/SERIOUS]** ...

**Skill: {_skill_names(repo_name)}** *(from skill guideline file)*
Only apply rules relevant to the actual code in this diff — skip framework rules not present (e.g. FastAPI rules don't apply to a CLI tool). State which rules you checked and whether they passed.
- **[OK]** List the rule IDs you checked and found clean (e.g. PY-003, PY-005, PY-008). Note any rules skipped as N/A with a reason.
OR findings:
- **[WARNING]** `file:line` — description (rule ID)

Use **[OK]** when a category has no issues. Use **[WARNING]** or **[SERIOUS]** for findings.

## Verdict
Exactly one word on its own line: OK or WARNING or SERIOUS

## Recommendations
Concrete, actionable suggestions to fix or improve the code. Omit this section if there is nothing to recommend.
"""


# --- Helpers ----------------------------------------------------------

def run(cmd: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=check)


def resolve_repo_dir(repo_name: str) -> Path:
    """Look up repo path from DB; fallback to literal path if it exists."""
    try:
        return Path(_db.get_repo_dir(repo_name))
    except SystemExit:
        p = Path(repo_name)
        if p.is_dir():
            return p
        raise SystemExit(
            f"ERROR: repo '{repo_name}' not in DB and is not a valid path.\n"
            f"Run: python db.py add-repo {repo_name} <local_dir>"
        )


def git_fetch_checkout(repo_dir: Path, commit: str) -> None:
    print(f"[git] Fetching in {repo_dir} …")
    run(["git", "fetch", "--all", "--quiet"], cwd=str(repo_dir))
    print(f"[git] Checking out {commit} …")
    run(["git", "checkout", commit], cwd=str(repo_dir))


def _claude_cmd() -> list[str]:
    return ["claude.cmd"] if sys.platform == "win32" else ["claude"]


SKILLS_DIR = Path(__file__).parent / "skills"
RULES_DIR  = Path(__file__).parent / "rules"


def _log_review_plan(repo_name: str) -> None:
    agent_path = AGENTS_DIR / "code-reviewer.md"
    print(f"[review] Persona   : {agent_path}" + (" [OK]" if agent_path.exists() else " [NOT FOUND]"))

    skills = _db.get_repo_skills(repo_name) if repo_name else []
    if skills:
        for skill in skills:
            filename = skill.lower().replace("/", "").replace(" ", "_") + ".md"
            p = SKILLS_DIR / filename
            mark = "[OK]" if p.exists() else "[NOT FOUND]"
            print(f"[review] Skill     : {skill} -> {p.name} {mark}")
    else:
        print("[review] Skill     : (none configured - auto-detect from diff)")

    print("[review] Rules     :")
    for filename, note in _RULES_ORDER:
        p = RULES_DIR / filename
        mark = "[OK]" if p.exists() else "[SKIP - file not found]"
        print(f"[review]   {filename:<22} [{note}]  {mark}")


def run_claude_review(repo_dir: Path, task_desc: str, repo_name: str = "") -> str:
    prompt = _build_commit_prompt(task_desc, repo_name)
    _log_review_plan(repo_name)
    print("[claude] Running review (this may take a minute) …")
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False,
                                     encoding="utf-8") as tmp:
        tmp.write(prompt)
        tmp_path = tmp.name

    try:
        allowed = "Read,Write,Edit,Bash,Glob,Grep"
        if sys.platform == "win32":
            # PowerShell pipes file content to claude — avoids cmd.exe 8191-char limit
            ps_cmd = (
                f"Get-Content -Path '{tmp_path}' -Raw -Encoding UTF8 | "
                f"& claude.cmd --print --allowedTools '{allowed}'"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                cwd=str(repo_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        else:
            with open(tmp_path, encoding="utf-8") as f:
                result = subprocess.run(
                    ["claude", "--print", "--allowedTools", allowed],
                    stdin=f,
                    cwd=str(repo_dir),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    if result.returncode != 0:
        err = (result.stderr or "").strip()[:500]
        print(f"[claude] stderr: {err}", file=sys.stderr)
        raise SystemExit(f"ERROR: claude exit code {result.returncode}\n{err}")
    return result.stdout


def extract_verdict(output: str) -> str:
    match = re.search(r"##\s*Verdict\s*\n+(.+)", output, re.IGNORECASE)
    if not match:
        return "UNKNOWN"
    line = match.group(1).strip().upper()
    for label in ("SERIOUS", "WARNING", "OK"):
        if label in line:
            return label
    return "UNKNOWN"


def build_markdown(repo_name: str, commit: str, task_desc: str, dev_name: str,
                   claude_output: str, verdict: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    label = VERDICT_LABELS.get(verdict, verdict)
    header = (
        f"# Code Review Report\n\n"
        f"| Field | Value |\n"
        f"|-------|-------|\n"
        f"| **Repo** | `{repo_name}` |\n"
        f"| **Commit** | `{commit}` |\n"
        f"| **Developer** | {dev_name or '—'} |\n"
        f"| **Task** | {task_desc or '—'} |\n"
        f"| **Verdict** | {label} |\n"
        f"| **Generated** | {ts} |\n\n"
        f"---\n\n"
    )
    return header + claude_output.strip() + "\n"


def save_report(repo_name: str, commit: str, content: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_repo = re.sub(r"[^\w-]", "_", repo_name)
    short_hash = commit[:8]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"{ts}_{safe_repo}_{short_hash}.md"
    out_path.write_text(content, encoding="utf-8")
    return out_path


def build_slack_payload(report_path: Path, repo_name: str, commit: str,
                        verdict: str, dev_name: str) -> dict:
    return {
        "repo": repo_name,
        "commit": commit,
        "dev": dev_name,
        "verdict": verdict,
        "verdict_label": VERDICT_LABELS.get(verdict, verdict),
        "report_file": str(report_path),
    }


# --- Entry point ------------------------------------------------------

def main():
    _db.init_db()

    parser = argparse.ArgumentParser(description="Run a Claude Code review on a commit.")
    parser.add_argument("--repo",   required=True, help="Repo name (in DB) or full path")
    parser.add_argument("--commit", required=True, help="Git commit hash to review")
    parser.add_argument("--task",   default="",    help="Task description from the developer")
    parser.add_argument("--dev",    default="",    help="Developer name / Slack handle")
    parser.add_argument("--json",   action="store_true", help="Print Slack payload as JSON")
    args = parser.parse_args()

    repo_dir = resolve_repo_dir(args.repo)

    git_fetch_checkout(repo_dir, args.commit)

    claude_output = run_claude_review(repo_dir, args.task, repo_name=args.repo)

    verdict = extract_verdict(claude_output)
    print(f"[review] Verdict: {VERDICT_LABELS.get(verdict, verdict)}")

    md_content = build_markdown(args.repo, args.commit, args.task, args.dev, claude_output, verdict)
    report_path = save_report(args.repo, args.commit, md_content)
    print(f"[review] Report saved → {report_path}")

    # Auto-save to DB
    rid = _db.add_review(
        repo_name=args.repo,
        commit_hash=args.commit,
        verdict=verdict,
        report_path=str(report_path),
        task_desc=args.task,
        dev_name=args.dev,
    )
    print(f"[db]     Review #{rid} saved to DB")

    payload = build_slack_payload(report_path, args.repo, args.commit, verdict, args.dev)

    if args.json:
        print(json.dumps(payload, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
