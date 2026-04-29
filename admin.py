#!/usr/bin/env python3
"""
Streamlit Admin UI — Code Review System
Run: streamlit run admin.py
"""

import subprocess
import streamlit as st
import pandas as pd
from pathlib import Path
import db
import crypto

db.init_db()

SKILLS_DIR = Path(__file__).parent / "skills"

SKILL_GROUPS = {
    "Frontend":  ["JavaScript", "TypeScript", "ReactJS", "VueJS", "NextJS", "HTML/CSS"],
    "Backend":   ["Python", "NodeJS", "Go", "Java", "FastAPI", "Django", "Spring Boot"],
    "Database":  ["PostgreSQL", "MySQL", "MongoDB", "Redis"],
    "DevOps":    ["Docker", "Kubernetes", "CI/CD"],
    "Mobile":    ["React Native", "Flutter"],
}
ALL_SKILLS = [s for group in SKILL_GROUPS.values() for s in group]


def skill_to_filename(skill: str) -> str:
    return skill.lower().replace("/", "").replace(" ", "_") + ".md"


def render_skill_checkboxes(current: list[str], key_prefix: str) -> list[str]:
    selected = []
    for group, skills in SKILL_GROUPS.items():
        st.caption(f"**{group}**")
        cols = st.columns(3)
        for i, skill in enumerate(skills):
            filename = skill_to_filename(skill)
            has_file = (SKILLS_DIR / filename).exists()
            label = skill if has_file else f"{skill} *(no .md)*"
            if cols[i % 3].checkbox(label, value=skill in current,
                                     key=f"{key_prefix}_{skill}"):
                selected.append(skill)
    return selected

st.set_page_config(page_title="Code Review Admin", page_icon="🔍", layout="wide")
st.title("🔍 Code Review Admin")

tab_repos, tab_devs, tab_reviews, tab_stats, tab_skills = st.tabs(["📁 Repos", "👥 Devs", "📋 Reviews", "📊 Stats", "🛠️ Skills"])


# ── MODALS ────────────────────────────────────────────────────────────

@st.dialog("➕ Thêm Repo", width="large")
def modal_add_repo():
    col1, col2 = st.columns(2)
    r_name    = col1.text_input("Tên repo *", placeholder="tool_monitor")
    r_project = col2.text_input("Tên project", placeholder="Tool Monitor")

    # Clone or manual dir
    clone_mode = st.toggle("Clone từ GitHub về máy")

    if clone_mode:
        r_gh_url  = st.text_input("GitHub URL *", placeholder="https://github.com/org/repo")
        r_token   = st.text_input("GitHub Token (nếu private)", type="password", placeholder="ghp_...")
        r_parent  = st.text_input("Clone vào thư mục *", placeholder="D:/Projects",
                                   help="Repo sẽ được clone vào thư mục con bên trong đây")

        if st.button("📥 Clone ngay", use_container_width=True):
            if not r_gh_url.strip() or not r_parent.strip():
                st.error("Cần nhập GitHub URL và thư mục đích.")
            else:
                parent = Path(r_parent.strip())
                if not parent.is_dir():
                    st.error(f"Thư mục '{r_parent}' không tồn tại.")
                else:
                    repo_name = r_gh_url.rstrip("/").split("/")[-1].removesuffix(".git")
                    clone_url = r_gh_url.strip()
                    if r_token:
                        # Embed token into URL for private repos
                        clone_url = clone_url.replace("https://", f"https://oauth2:{r_token}@")
                    target_dir = parent / (r_name.strip() or repo_name)
                    with st.spinner(f"Đang clone vào {target_dir} ..."):
                        result = subprocess.run(
                            ["git", "clone", clone_url, str(target_dir)],
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                        )
                    if result.returncode == 0:
                        st.success(f"Clone thành công → {target_dir}")
                        st.session_state["cloned_dir"] = str(target_dir)
                        st.session_state["cloned_url"] = r_gh_url.strip()
                    else:
                        st.error(f"Clone thất bại:\n{result.stderr[:500]}")

        r_dir    = st.session_state.get("cloned_dir", "")
        r_gh_url_final = st.session_state.get("cloned_url", r_gh_url if "r_gh_url" in dir() else "")
        st.text_input("Local dir (tự điền sau clone)", value=r_dir, disabled=True)
    else:
        r_dir         = st.text_input("Local dir *", placeholder="D:/Projects/tool_monitor")
        r_gh_url_final = st.text_input("GitHub URL", placeholder="https://github.com/org/repo")
        r_token       = st.text_input("GitHub Token", type="password", placeholder="ghp_...")

    r_desc = st.text_input("Mô tả", placeholder="Monitor tool project")

    st.markdown("**Skills**")
    skills = render_skill_checkboxes([], key_prefix="add")

    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("Thêm repo", type="primary", use_container_width=True):
        local_dir = r_dir.strip() if not clone_mode else st.session_state.get("cloned_dir", "")
        if not r_name.strip() or not local_dir:
            st.error("Tên repo và Local dir không được để trống." if not clone_mode
                     else "Chưa clone thành công hoặc chưa nhập tên repo.")
        else:
            try:
                gh_url = r_gh_url_final if clone_mode else (r_gh_url_final or "")
                tok    = "" if clone_mode else (r_token or "")
                db.add_repo(r_name.strip(), local_dir, r_project, r_desc, gh_url, tok)
                db.set_repo_skills(r_name.strip(), skills)
                st.session_state.pop("cloned_dir", None)
                st.session_state.pop("cloned_url", None)
                st.success(f"Đã thêm repo '{r_name}'")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    if c2.button("Hủy", use_container_width=True):
        st.session_state.pop("cloned_dir", None)
        st.session_state.pop("cloned_url", None)
        st.rerun()


@st.dialog("✏️ Sửa Repo", width="large")
def modal_edit_repo(repo_name: str):
    cur = db.get_repo(repo_name)
    if not cur:
        st.error("Repo không tồn tại."); return

    col1, col2 = st.columns(2)
    e_project = col1.text_input("Tên project", value=cur["project_name"] or "")
    e_dir     = col2.text_input("Local dir",   value=cur["local_dir"])
    e_desc    = st.text_input("Mô tả",         value=cur["description"] or "")
    e_gh_url  = st.text_input("GitHub URL",    value=cur["github_url"] or "")
    e_token   = st.text_input("GitHub Token",  type="password",
                               placeholder="Để trống = giữ nguyên")

    st.markdown("**Skills**")
    current_skills = db.get_repo_skills(repo_name)
    skills = render_skill_checkboxes(current_skills, key_prefix=f"edit_{repo_name}")

    st.divider()
    col1, col2, col3 = st.columns(3)
    if col1.button("Lưu", type="primary", use_container_width=True):
        try:
            db.update_repo(repo_name, local_dir=e_dir or None, project_name=e_project,
                           desc=e_desc, github_url=e_gh_url, github_token=e_token or None)
            db.set_repo_skills(repo_name, skills)
            st.success("Đã lưu!"); st.rerun()
        except Exception as e:
            st.error(str(e))
    if col2.button("Hủy", use_container_width=True):
        st.rerun()
    st.divider()
    st.warning(f"⚠️ Xóa repo `{repo_name}` sẽ xóa luôn toàn bộ devs.")
    if col3.button("🗑️ Xóa repo", use_container_width=True):
        try:
            db.remove_repo(repo_name); st.rerun()
        except Exception as e:
            st.error(str(e))


# ── REPOS ─────────────────────────────────────────────────────────────

with tab_repos:
    col_title, col_btn = st.columns([6, 1])
    col_title.subheader("Danh sách Repos")
    if col_btn.button("➕ Thêm Repo", type="primary", use_container_width=True):
        modal_add_repo()

    repos = db.get_all_repos()
    if not repos:
        st.info("Chưa có repo nào. Bấm '➕ Thêm Repo' để bắt đầu.")
    else:
        # Header
        h = st.columns([2, 2, 3, 2, 2, 1, 1])
        for col, label in zip(h, ["Tên repo", "Project", "Local Dir", "GitHub URL", "Skills", "Token", ""]):
            col.markdown(f"**{label}**")
        st.divider()

        for r in repos:
            token_display = crypto.mask(r["github_token"]) if r["github_token"] else "—"
            skills = db.get_repo_skills(r["name"])
            skills_display = ", ".join(skills) if skills else "—"
            c = st.columns([2, 2, 3, 2, 2, 1, 1])
            c[0].write(r["name"])
            c[1].write(r["project_name"] or "—")
            c[2].write(r["local_dir"])
            c[3].write(r["github_url"] or "—")
            c[4].write(skills_display)
            c[5].write(token_display)
            if c[6].button("✏️", key=f"edit_repo_{r['name']}", help="Sửa repo"):
                modal_edit_repo(r["name"])
            st.divider()


# ── DEVS ──────────────────────────────────────────────────────────────

@st.dialog("➕ Thêm Dev")
def modal_add_dev(repo_name: str):
    d_name    = st.text_input("Tên dev *", placeholder="Duc Anh")
    d_slack   = st.text_input("Slack ID *", placeholder="anh",
                               help="Tên ngắn dùng trong Slack command, phải unique trong repo")
    st.caption("Ví dụ: `review tool_monitor abc123 **anh** | task`")
    d_github  = st.text_input("GitHub username", placeholder="DucAnh03")
    d_token   = st.text_input("GitHub Token", type="password", placeholder="ghp_...")
    st.caption("🔒 Token được mã hóa trước khi lưu vào DB.")
    col1, col2 = st.columns(2)
    if col1.button("Thêm", type="primary", use_container_width=True):
        if not d_name.strip():
            st.error("Tên dev không được để trống.")
        elif not d_slack.strip():
            st.error("Slack ID không được để trống.")
        else:
            try:
                db.add_dev(repo_name, d_name.strip(), d_slack.strip(), d_github, d_token)
                st.success(f"Đã thêm '{d_name}' với Slack ID `{d_slack}`"); st.rerun()
            except Exception as e:
                st.error(str(e))
    if col2.button("Hủy", use_container_width=True):
        st.rerun()


@st.dialog("✏️ Sửa Dev")
def modal_edit_dev(repo_name: str, dev_name: str):
    st.markdown(f"Dev: **{dev_name}** — Repo: `{repo_name}`")

    devs = db.get_devs(repo_name)
    cur = next((d for d in devs if d["dev_name"] == dev_name), None)
    cur_slack_id = cur["slack_id"] if cur else ""

    new_slack_id = st.text_input("Slack ID", value=cur_slack_id,
                                  help="Tên ngắn dùng trong Slack command, phải unique trong repo")
    new_token = st.text_input("GitHub Token mới", type="password", placeholder="ghp_...")
    st.caption("🔒 Để trống = giữ nguyên token cũ.")

    col1, col2, col3 = st.columns(3)
    if col1.button("Lưu", type="primary", use_container_width=True):
        try:
            if new_slack_id.strip() != cur_slack_id:
                db.update_dev_slack_id(repo_name, dev_name, new_slack_id)
            if new_token:
                db.update_dev_token(repo_name, dev_name, new_token)
            st.success("Đã lưu!"); st.rerun()
        except Exception as e:
            st.error(str(e))
    if col2.button("Hủy", use_container_width=True):
        st.rerun()
    st.divider()
    if col3.button("🗑️ Xóa dev", use_container_width=True):
        try:
            db.remove_dev(repo_name, dev_name); st.rerun()
        except Exception as e:
            st.error(str(e))


with tab_devs:
    repos = db.get_all_repos()
    repo_names = [r["name"] for r in repos]

    if not repo_names:
        st.info("Thêm repo trước.")
    else:
        col_sel, col_btn2 = st.columns([4, 1])
        sel_repo = col_sel.selectbox("Chọn repo", ["— chọn repo —"] + repo_names,
                                      key="devs_repo_sel", label_visibility="collapsed")

        if sel_repo == "— chọn repo —":
            st.info("Chọn một repo để quản lý devs.")
        else:
            if col_btn2.button("➕ Thêm Dev", type="primary", use_container_width=True):
                modal_add_dev(sel_repo)

            devs = db.get_devs(sel_repo)
            st.subheader(f"Devs trong `{sel_repo}`")

            if not devs:
                st.info(f"Repo `{sel_repo}` chưa có dev nào.")
            else:
                h = st.columns([2, 2, 2, 2, 1])
                for col, label in zip(h, ["Tên", "Slack ID", "GitHub", "Token", ""]):
                    col.markdown(f"**{label}**")
                st.divider()
                for d in devs:
                    token_masked = crypto.mask(crypto.decrypt(d["github_token"])) \
                                   if d["github_token"] else "—"
                    c = st.columns([2, 2, 2, 2, 1])
                    c[0].write(d["dev_name"])
                    c[1].write(d["slack_id"] if d["slack_id"] else "—")
                    c[2].write(d["github_username"] or "—")
                    c[3].write(token_masked)
                    if c[4].button("✏️", key=f"edit_dev_{d['dev_name']}", help="Sửa / Xóa"):
                        modal_edit_dev(sel_repo, d["dev_name"])
                    st.divider()


# ── REVIEWS ───────────────────────────────────────────────────────────

with tab_reviews:
    st.subheader("Lịch sử Review")

    repos = db.get_all_repos()
    repo_names = ["(Tất cả)"] + [r["name"] for r in repos]

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        f_repo    = st.selectbox("Repo", repo_names)
    with col_f2:
        f_verdict = st.selectbox("Verdict", ["(Tất cả)", "OK", "WARNING", "SERIOUS", "UNKNOWN"])
    with col_f3:
        f_dev     = st.text_input("Dev", placeholder="Tìm theo tên dev")
    with col_f4:
        f_limit   = st.number_input("Giới hạn", min_value=10, max_value=200, value=50, step=10)

    reviews = db.get_reviews(
        repo_name=None if f_repo == "(Tất cả)" else f_repo,
        verdict=None if f_verdict == "(Tất cả)" else f_verdict,
        dev_name=f_dev or None,
        limit=int(f_limit),
    )

    VERDICT_ICON = {"OK": "✅", "WARNING": "⚠️", "SERIOUS": "🚨", "UNKNOWN": "❓"}

    if reviews:
        df_rv = pd.DataFrame([dict(r) for r in reviews])
        df_rv["verdict"]     = df_rv["verdict"].apply(lambda v: f"{VERDICT_ICON.get(v,'')} {v}")
        df_rv["commit_hash"] = df_rv["commit_hash"].apply(lambda h: h[:8])
        st.dataframe(
            df_rv[["id", "repo_name", "commit_hash", "dev_name", "verdict", "task_desc", "created_at"]],
            use_container_width=True, hide_index=True,
        )

        st.divider()
        st.markdown("**📄 Xem nội dung report**")
        rev_options = {f"#{r['id']} — {r['repo_name']} {r['commit_hash'][:8]} ({r['verdict']})": r
                       for r in reviews}
        sel_rev = st.selectbox("Chọn review", list(rev_options.keys()))
        if sel_rev:
            rv = rev_options[sel_rev]
            rp = Path(rv["report_path"])
            if rp.exists():
                with st.expander("Nội dung report", expanded=True):
                    st.markdown(rp.read_text(encoding="utf-8"))
            else:
                st.warning(f"File không tìm thấy: {rp}")
    else:
        st.info("Không có review nào khớp filter.")


# ── STATS ─────────────────────────────────────────────────────────────

with tab_stats:
    st.subheader("Thống kê")

    s = db.get_stats()

    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    col_s1.metric("Tổng reviews", s["total"])
    col_s2.metric("✅ OK",        s["ok"])
    col_s3.metric("⚠️ Warning",   s["warning"])
    col_s4.metric("🚨 Serious",   s["serious"])

    st.divider()
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        st.markdown("**Reviews theo Repo**")
        if s["by_repo"]:
            df_repo = pd.DataFrame(s["by_repo"]).rename(columns={"repo_name": "Repo", "c": "Reviews"})
            st.bar_chart(df_repo.set_index("Repo"))
        else:
            st.info("Chưa có dữ liệu.")

    with col_c2:
        st.markdown("**Reviews theo Dev**")
        if s["by_dev"]:
            df_dev = pd.DataFrame(s["by_dev"]).rename(columns={"dev_name": "Dev", "c": "Reviews"})
            st.bar_chart(df_dev.set_index("Dev"))
        else:
            st.info("Chưa có dữ liệu.")

    st.markdown("**Reviews theo ngày (30 ngày gần nhất)**")
    if s["by_day"]:
        df_day = pd.DataFrame(s["by_day"]).rename(columns={"day": "Ngày", "c": "Reviews"})
        st.line_chart(df_day.set_index("Ngày"))
    else:
        st.info("Chưa có dữ liệu.")
