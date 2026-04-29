#!/usr/bin/env python3
"""
PR Review module: fetch GitHub PR info + run Claude review on net diff.
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

import db as _db

_BASE        = Path(__file__).parent
AGENTS_DIR   = _BASE / ".claude" / "agents"
RULES_DIR    = _BASE / "rules"
SKILLS_DIR   = _BASE / "skills"

_RULES_ORDER = [
    ("security.md",       "BLOCKING, no exceptions"),
    ("error-handling.md", "SERIOUS if missing"),
    ("code-style.md",     "WARNING if violated"),
]

VERDICT_LABELS = {"OK": "✅ OK", "WARNING": "⚠️ Warning", "SERIOUS": "🚨 Serious"}


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


def _build_pr_prompt(pr_info: dict, diff: str, repo_name: str) -> str:
    agent_path = AGENTS_DIR / "code-reviewer.md"
    skill_label = _skill_names(repo_name)
    return f"""\
Read "{agent_path}" and adopt that role completely.

## Step 1 — Pull Request context
Title       : {pr_info['title']}
Author      : {pr_info['author']}
Base branch : {pr_info['base_branch']}
Head branch : {pr_info['head_branch']}
PR URL      : {pr_info['pr_url']}

PR Description:
{pr_info['body']}

Net diff (base...head):
{diff or "(no diff)"}

## Step 2 — Load skill guidelines
{_build_skill_section(repo_name)}

## Step 3 — Apply rules (read ALL in this order before reviewing)
{_build_rules_section()}

## Step 4 — Analyse
- Read the PR description carefully — it defines the intent.
- For each changed file, read the full file in the repo for context.
- Grep for any changed function or class to find other callers.
- Check if tests cover the changes.

## Step 5 — Output format (STRICT)
Output EXACTLY these four sections, nothing else:

## Summary
One paragraph: what this PR does and whether it achieves the stated goal.

## Issues
REQUIRED: write all four blocks below. Never skip a block, even if the result is [OK] or [N/A].

**Security** *(from security.md)*
- **[OK/WARNING/SERIOUS]** ...

**Error Handling** *(from error-handling.md)*
- **[OK/WARNING/SERIOUS]** ...

**Code Style** *(from code-style.md)*
- **[OK/WARNING/SERIOUS]** ...

**Skill: {skill_label}** *(from skill guideline file)*
Only apply rules relevant to the actual code in this diff — skip framework rules not present (e.g. FastAPI rules don't apply to a CLI tool). State which rules you checked and whether they passed.
- **[OK]** List the rule IDs you checked and found clean (e.g. PY-003, PY-005, PY-008). Note any rules skipped as N/A with a reason.
OR findings:
- **[WARNING]** `file:line` — description (rule ID)

Use **[OK]** when a category has no issues. Use **[WARNING]** or **[SERIOUS]** for findings.

## Verdict
Exactly one word on its own line: OK or WARNING or SERIOUS

## Recommendations
Concrete, actionable suggestions. Reference specific files and line numbers where possible. Omit this section if there is nothing to recommend.
"""


# --- GitHub API -------------------------------------------------------

def _parse_github_owner_repo(github_url: str) -> tuple[str, str]:
    """Extract owner/repo from https://github.com/owner/repo URL."""
    m = re.search(r"github\.com[/:]([^/]+)/([^/\.]+)", github_url)
    if not m:
        raise ValueError(f"Không parse được GitHub URL: {github_url}")
    return m.group(1), m.group(2)


def fetch_pr_info(github_url: str, pr_number: int, token: str = "") -> dict:
    try:
        import urllib.request, json
    except ImportError:
        raise RuntimeError("urllib không available")

    owner, repo = _parse_github_owner_repo(github_url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

    req = urllib.request.Request(api_url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"PR #{pr_number} không tìm thấy trong {owner}/{repo}")
        if e.code == 401:
            raise ValueError("GitHub token không hợp lệ hoặc thiếu quyền truy cập repo private.")
        raise ValueError(f"GitHub API lỗi: HTTP {e.code}")

    return {
        "number":      data["number"],
        "title":       data["title"],
        "body":        data.get("body") or "(Không có mô tả)",
        "author":      data["user"]["login"],
        "base_branch": data["base"]["ref"],
        "head_branch": data["head"]["ref"],
        "head_sha":    data["head"]["sha"],
        "pr_url":      data["html_url"],
        "state":       data["state"],
        "owner":       owner,
        "repo":        repo,
    }


# --- Git diff ---------------------------------------------------------

def _run(cmd: list[str], cwd: str) -> str:
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    return result.stdout


MAX_DIFF_CHARS = 25_000


def get_pr_diff(repo_dir: Path, base_branch: str, head_sha: str) -> str:
    cwd = str(repo_dir)
    # Fetch all remote branches
    subprocess.run(["git", "fetch", "--all", "--quiet"], cwd=cwd)

    diff = _run(["git", "diff", f"origin/{base_branch}...{head_sha}"], cwd=cwd)
    if not diff:
        # Fallback: already checked out head
        diff = _run(["git", "diff", f"origin/{base_branch}...HEAD"], cwd=cwd)

    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + f"\n\n... [diff truncated at {MAX_DIFF_CHARS} chars]"

    return diff.strip()


# --- Claude -----------------------------------------------------------

def _claude_cmd() -> list[str]:
    return ["claude.cmd"] if sys.platform == "win32" else ["claude"]


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


def run_pr_review(repo_dir: Path, pr_info: dict, diff: str, repo_name: str = "") -> str:
    _log_review_plan(repo_name)
    prompt = _build_pr_prompt(pr_info, diff, repo_name)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False,
                                     encoding="utf-8") as tmp:
        tmp.write(prompt)
        tmp_path = tmp.name

    try:
        allowed = "Read,Write,Edit,Bash,Glob,Grep"
        if sys.platform == "win32":
            ps_cmd = f"Get-Content -Path '{tmp_path}' -Raw -Encoding UTF8 | & claude.cmd --print --allowedTools '{allowed}'"
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                cwd=str(repo_dir), capture_output=True,
                text=True, encoding="utf-8", errors="replace",
            )
        else:
            with open(tmp_path, encoding="utf-8") as f:
                result = subprocess.run(
                    ["claude", "--print", "--allowedTools", allowed], stdin=f,
                    cwd=str(repo_dir), capture_output=True,
                    text=True, encoding="utf-8", errors="replace",
                )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if result.returncode != 0:
        err = (result.stderr or "").strip()[:500]
        raise RuntimeError(f"claude exit code {result.returncode}\n{err}")

    return result.stdout


def extract_verdict(output: str) -> str:
    import re
    m = re.search(r"##\s*Verdict\s*\n+(.+)", output, re.IGNORECASE)
    if not m:
        return "UNKNOWN"
    line = m.group(1).strip().upper()
    for label in ("SERIOUS", "WARNING", "OK"):
        if label in line:
            return label
    return "UNKNOWN"


def build_pr_markdown(pr_info: dict, dev_name: str, claude_output: str, verdict: str) -> str:
    from datetime import datetime
    ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    label = VERDICT_LABELS.get(verdict, verdict)
    header = (
        f"# PR Review Report\n\n"
        f"| Field | Value |\n"
        f"|-------|-------|\n"
        f"| **PR** | [{pr_info['title']}]({pr_info['pr_url']}) |\n"
        f"| **PR #** | {pr_info['number']} |\n"
        f"| **Author** | {pr_info['author']} |\n"
        f"| **Reviewer** | {dev_name or '—'} |\n"
        f"| **Base** | `{pr_info['base_branch']}` |\n"
        f"| **Head** | `{pr_info['head_branch']}` |\n"
        f"| **Verdict** | {label} |\n"
        f"| **Generated** | {ts} |\n\n"
        f"---\n\n"
    )
    return header + claude_output.strip() + "\n"


def save_pr_report(repo_name: str, pr_number: int, content: str) -> Path:
    from datetime import datetime
    import re
    output_dir = Path(__file__).parent / "reviews"
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_repo = re.sub(r"[^\w-]", "_", repo_name)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = output_dir / f"{ts}_{safe_repo}_PR{pr_number}.md"
    out_path.write_text(content, encoding="utf-8")
    return out_path


# --- Main entry point (called from slack_bot) -------------------------

def review_pr(repo_name: str, pr_number: int, dev_name: str, token_override: str = "") -> dict:
    """
    Full PR review flow. Returns dict with verdict + report_path.
    """
    repo = _db.get_repo(repo_name)
    if not repo:
        raise ValueError(f"Repo '{repo_name}' không có trong DB.")

    github_url = repo["github_url"]
    if not github_url:
        raise ValueError(f"Repo '{repo_name}' chưa có GitHub URL. Vào Admin UI để cập nhật.")

    # Per-dev token takes priority → fallback repo token → fallback override
    token = _db.get_dev_token(repo_name, dev_name) or token_override or repo["github_token"] or ""
    repo_dir = Path(repo["local_dir"])

    pr_info = fetch_pr_info(github_url, pr_number, token)
    diff    = get_pr_diff(repo_dir, pr_info["base_branch"], pr_info["head_sha"])

    # Checkout head commit để Claude đọc codebase đúng state
    subprocess.run(["git", "checkout", pr_info["head_sha"]],
                   cwd=str(repo_dir), capture_output=True)

    claude_output = run_pr_review(repo_dir, pr_info, diff, repo_name=repo_name)
    verdict       = extract_verdict(claude_output)

    md_content  = build_pr_markdown(pr_info, dev_name, claude_output, verdict)
    report_path = save_pr_report(repo_name, pr_number, md_content)

    _db.add_review(
        repo_name   = repo_name,
        commit_hash = pr_info["head_sha"],
        verdict     = verdict,
        report_path = str(report_path),
        task_desc   = f"PR #{pr_number}: {pr_info['title']}",
        dev_name    = dev_name,
    )

    return {
        "pr_info":     pr_info,
        "verdict":     verdict,
        "report_path": report_path,
    }
