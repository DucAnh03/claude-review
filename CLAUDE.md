# Claude Flow Review — Project Guide

This is an automated code review system. Claude Code is the review engine.

## How reviews work

1. Slack bot receives `review [repo] [commit] [dev] | task` or `review-pr [repo] [PR#] [dev]`
2. `review_core.py` or `pr_review.py` builds a structured prompt and runs `claude --print`
3. Claude reads the persona, skill guidelines, and rule files, then analyses the diff
4. Output is saved as a `.md` report in `reviews/` and uploaded to Slack

## Prompt structure (5 steps)

Every review prompt follows this order:

| Step | What Claude reads |
|------|-------------------|
| Persona | `.claude/agents/code-reviewer.md` |
| Step 1 | Runs `git show HEAD` or gets PR diff |
| Step 2 | Skill files from `skills/` based on repo config in DB |
| Step 3 | Rule files: `rules/security.md` → `rules/error-handling.md` → `rules/code-style.md` |
| Step 4 | Analyses diff with full file reads + grep |
| Step 5 | Outputs Summary / Issues / Verdict / Recommendations |

## Key files

```
.claude/agents/code-reviewer.md   ← Claude persona and review mindset
rules/security.md                 ← BLOCKING rules (SEC-001..018)
rules/error-handling.md           ← SERIOUS rules (ERR-001..022)
rules/code-style.md               ← WARNING rules (STYLE-001..029)
skills/<lang>.md                  ← Per-language guidelines (loaded based on repo skills in DB)
review_core.py                    ← Commit review engine
pr_review.py                      ← PR review engine
slack_bot.py                      ← Slack Socket Mode bot
admin.py                          ← Streamlit admin UI
db.py                             ← SQLite (repos, devs, reviews, skills)
crypto.py                         ← Fernet encryption for GitHub tokens
```

## Per-repo CLAUDE.md support (free, no config needed)

If a repo being reviewed has its own `CLAUDE.md` or `.claude/CLAUDE.md`, Claude reads it
automatically because the review runs with `cwd` set to that repo's directory.

Use this to add project-specific conventions:
```
# tool_monitor/CLAUDE.md
This is a FastAPI + PostgreSQL service.
Always check that new endpoints have rate limiting.
Database migrations must be backward-compatible.
```

## Adding new rules or skills

- **New rule file**: drop a `.md` into `rules/` — it will NOT be auto-loaded.
  Add it to `_RULES_ORDER` in `review_core.py` and `pr_review.py` to include it in reviews.
- **New skill**: drop a `.md` into `skills/` — it will be auto-loaded once the skill
  is assigned to a repo via the Admin UI.

## Running locally

```bash
# Start admin UI
streamlit run admin.py

# Start Slack bot
python slack_bot.py

# Run a review manually
python review_core.py --repo tool_monitor --commit b58927b --task "Add CSV export" --dev "Duc Anh"
```
