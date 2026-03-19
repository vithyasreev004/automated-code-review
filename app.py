import streamlit as st
from pathlib import Path
import json
import pandas as pd
from fpdf import FPDF
from sqlalchemy import create_engine
import psycopg2
from psycopg2.extras import Json

from app.main import analyze_sync
from app.utils import (
    save_uploaded_file_temp,
    clone_github_repo_temp,
    get_python_files,
    chunk_code,
    get_redis_connection,
    get_pg_connection,
)

# -------------------------------
# Page Config & Custom Styling
# -------------------------------
st.set_page_config(page_title="Automated Code Review Assistant", layout="wide", page_icon="📊")

st.markdown("""
    <style>
    /* History buttons */
    div[data-testid="stSidebar"] button[kind="secondary"] {
        background-color: #000000 !important;
        color: #ffffff !important;
        border-radius: 6px;
        padding: 0.3em 0.8em;
        font-weight: 500;
        text-align: left;
    }
    div[data-testid="stSidebar"] button[kind="secondary"]:hover {
        background-color: #333333 !important;
    }
    /* Trash buttons */
    div[data-testid="stSidebar"] button:has(span:contains("🗑️")) {
        background-color: transparent !important;
        color: #ff4b4b !important;
        font-size: 18px;
    }
    div[data-testid="stSidebar"] button:has(span:contains("🗑️")):hover {
        background-color: #ffcccc !important;
        color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)



# -------------------------------
# Safe JSON Parser for LLM Output
# -------------------------------
def safe_parse_json(raw_output, filename):
    try:
        return json.loads(raw_output)
    except Exception:
        st.warning(f"⚠️ Refactor failed for {filename}: invalid JSON")
        return {
            "issues": [],
            "diff": None,
            "refactored_code": None,
            "documented_code": None
        }


st.title("📊 Automated Code Review & Documentation Assistant")

# -------------------------------
# Upload / Repo Input
# -------------------------------
st.header("📂 Upload or Connect Repository")
uploaded_file = st.file_uploader("Upload a Python file", type=["py"])
repo_url = st.text_input("Or enter a GitHub repository URL")

# -------------------------------
# Export Functions
# -------------------------------
def export_markdown(results, overall_pre, overall_post):
    md = f"# Repository Report\n\nPre Confidence: {overall_pre}\nPost Confidence: {overall_post}\n\n"
    for r in results:
        md += f"## {r['filename']}\n"
        md += f"- Pre Confidence: {r['pre_confidence']}\n"
        md += f"- Post Confidence: {r['post_confidence']}\n"
        md += f"- Issues: {len(r.get('issues', []))}\n\n"
    return md

def export_pdf(results, overall_pre, overall_post):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Repository Report", ln=True)
    pdf.cell(200, 10, txt=f"Pre Confidence: {overall_pre}", ln=True)
    pdf.cell(200, 10, txt=f"Post Confidence: {overall_post}", ln=True)
    for r in results:
        pdf.cell(200, 10, txt=f"File: {r['filename']}", ln=True)
        pdf.cell(200, 10, txt=f"Pre: {r['pre_confidence']} Post: {r['post_confidence']}", ln=True)
    return pdf.output(dest="S").encode("latin-1")

# -------------------------------
# Display Functions
# -------------------------------
def display_results(result, filename: str):
    st.markdown(f"### 📄 Results for `{filename}`")
    col1, col2 = st.columns(2)
    col1.metric("Pre Confidence", result.get("pre_confidence", "N/A"))
    col2.metric("Post Confidence", result.get("post_confidence", "N/A"))

    review = result.get("llm_review", {})
    if review:
        summary_text = review.get("summary", "")
        if summary_text.startswith("LLM error"):
            st.error(f"❌ Review failed: {summary_text}")
        elif summary_text.strip() == "":
            st.warning("⚠️ No summary returned from LLM.")
        else:
            st.subheader("📝 LLM Review Summary")
            st.write(summary_text)
        st.metric("LLM Review Confidence", review.get("confidence", "N/A"))

    if result.get("issues"):
        st.subheader("🚨 Detected Issues")
        st.dataframe(pd.DataFrame([{
            "Category": i.get("category"),
            "Severity": i.get("severity"),
            "Line": i.get("line"),
            "Suggestion": i.get("suggestion"),
            "Source": i.get("source", "Unknown")
        } for i in result["issues"]]))
    else:
        st.info("No issues detected.")
    


    # ✅ Use safe JSON parsing for diffs/refactor outputs
    parsed = safe_parse_json(result.get("llm_output", "{}"), filename)

    if parsed.get("diff"):
        st.subheader("🔧 Suggested Changes (Diff)")
        st.code(parsed["diff"], language="diff")
    else:
        st.info("No valid diff available for this file.")

    if parsed.get("refactored_code"):
        with st.expander("✨ Refactored Code"):
            st.code(parsed["refactored_code"], language="python")

    if parsed.get("documented_code"):
        with st.expander("📖 Documented Code"):
            st.code(parsed["documented_code"], language="python")


    if result.get("diff"):
        st.subheader("🔧 Suggested Changes (Diff)")
        st.code(result["diff"], language="diff")

    if result.get("refactored_code"):
        with st.expander("✨ Refactored Code"):
            st.code(result["refactored_code"], language="python")

    if result.get("documented_code"):
        with st.expander("📖 Documented Code"):
            st.code(result["documented_code"], language="python")

def display_repo_summary(results: list, overall_pre: float, overall_post: float, readme: str):
    st.markdown("## 📊 Repository Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Overall Pre Confidence", overall_pre)
    col2.metric("Overall Post Confidence", overall_post)
    col3.metric("Files Analyzed", len(results))

    all_issues = []
    for r in results:
        all_issues.extend(r.get("issues", []))

    st.write(f"**Issues detected:** {len(all_issues)}")
    missing_docstrings = sum(1 for r in results if r["documented_code"].startswith('"""Stub'))
    st.write(f"**Files missing docstrings:** {missing_docstrings}")
    fallback_refactors = sum(1 for r in results if r["refactored_code"] == r.get("original_code"))
    st.write(f"**Files without refactor changes:** {fallback_refactors}")

    if readme:
        with st.expander("📘 Generated README.md"):
            st.code(readme, language="markdown")

    st.download_button("⬇️ Download Report (JSON)", json.dumps({"overall_pre":overall_pre,"overall_post":overall_post,"files":results}), "repo_report.json")
    st.download_button("⬇️ Download Report (Markdown)", export_markdown(results, overall_pre, overall_post), "repo_report.md")
    st.download_button("⬇️ Download Report (PDF)", export_pdf(results, overall_pre, overall_post), "repo_report.pdf")

# -------------------------------
# Latest Session from Redis
# -------------------------------
st.markdown("---")
st.subheader("🕒 Latest Session (Cached in Redis)")
r = get_redis_connection()
latest = r.get("latest_session")

if latest:
    try:
        decoded = latest.decode("utf-8").strip()
        if decoded:
            summary = json.loads(decoded)
            st.write(f"Repo: {summary['repo']}")
            st.write(f"Files analyzed: {summary['files']}")
            st.write(f"Pre-confidence: {summary['pre_conf']}")
            st.write(f"Post-confidence: {summary['post_conf']}")
        else:
            st.info("ℹ️ Cached session is empty. Run an analysis first.")
    except Exception as e:
        st.info("ℹ️ No valid cached session yet. Run an analysis to populate this panel.")
else:
    st.info("ℹ️ No cached session found. Run an analysis first.")

# -------------------------------
# Sidebar: History Panel
# -------------------------------
st.sidebar.title("🗂 History & Controls")

def load_history(limit=20):
    engine = create_engine("postgresql+psycopg2://postgres:admin123@localhost:5432/reviewdb")
    query = f"""
        SELECT id, repo, overall_pre_confidence, overall_post_confidence, created_at, results
        FROM public.analysis_runs
        ORDER BY created_at DESC
        LIMIT {limit}
    """
    return pd.read_sql(query, engine)

try:
    history = load_history()
    if not history.empty:
        for _, row in history.iterrows():
            # Short label: Run ID + truncated repo name
            label = f"{row['repo']} (Run {row['id']})"

            
            # Create two columns in the same row
            col1, col2 = st.sidebar.columns([6,1])
            
            with col1:
                if col1.button(label, key=f"run_{row['id']}", help=f"{row['created_at']:%Y-%m-%d %H:%M}"):
                    st.session_state["selected_run"] = row["id"]
            
            with col2:
                if col2.button("🗑️", key=f"del_{row['id']}", help="Delete this run"):
                    st.session_state["confirm_delete_id"] = row["id"]
    else:
        st.sidebar.info("No historical runs yet.")
except Exception as e:
    st.sidebar.error(f"⚠️ Could not load history: {e}")


if st.sidebar.button("➕ New Chat"):
    st.session_state.clear()
    st.rerun()

if st.sidebar.button("🗑️ Clear Chat History"):
    st.session_state.clear()
    st.sidebar.success("Chat cleared")
def insert_file_result(session_id, repo_name, result):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO public.file_results
            (session_id, timestamp, repo_name, files_analyzed, overall_pre_confidence, overall_post_confidence)
            VALUES (%s, NOW(), %s, %s, %s, %s)
            """,
            (
                session_id,
                repo_name,
                1,  # one file per insert
                result["pre_confidence"],
                result["post_confidence"]
            )
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()
def log_error(session_id, filename, error_message):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO public.errors
            (session_id, filename, error_message, created_at)
            VALUES (%s, %s, %s, NOW())
            """,
            (session_id, filename, error_message)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()

# -------------------------------
# Display Selected Run
# -------------------------------
if "selected_run" in st.session_state:
    st.markdown("---")
    st.subheader(f"📂 Viewing Run {st.session_state['selected_run']}")

    try:
        engine = create_engine("postgresql+psycopg2://postgres:admin123@localhost:5432/reviewdb")
        query = f"""
                        SELECT results, repo, overall_pre_confidence, overall_post_confidence, created_at
            FROM public.analysis_runs
            WHERE id = {st.session_state['selected_run']}
        """
        run = pd.read_sql(query, engine).iloc[0]

        st.markdown("## 📊 Run Overview")
        col1, col2, col3 = st.columns(3)
        col1.metric("Repo", run["repo"])
        col2.metric("Pre Confidence", run["overall_pre_confidence"])
        col3.metric("Post Confidence", run["overall_post_confidence"])
        st.info(f"Created At: {run['created_at']}")

        # ✅ Handle results safely (string vs dict)
        import json
        results = run["results"]
        if isinstance(results, str):
            results = json.loads(results)

        for r in results:
            with st.expander(f"📄 {r.get('file','unknown')}"):
                if r.get("issues"):
                    st.subheader("🚨 Issues")
                    st.dataframe(pd.DataFrame(r["issues"]))
                if r.get("diff"):
                    st.subheader("🔧 Diff")
                    st.code(r["diff"], language="diff")
                if r.get("documented_code"):
                    st.subheader("📖 Documented Code")
                    st.code(r["documented_code"], language="python")
                if r.get("refactored_code"):
                    st.subheader("✨ Refactored Code")
                    st.code(r["refactored_code"], language="python")

    except Exception as e:
        st.error(f"⚠️ Could not load run details: {e}")

# -------------------------------
# Confirm Delete Logic
# -------------------------------
if "confirm_delete_id" in st.session_state:
    st.warning(f"Are you sure you want to delete Run {st.session_state['confirm_delete_id']}? This action cannot be undone.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Yes, delete"):
            conn = get_pg_connection()
            cur = conn.cursor()
            try:
                cur.execute("DELETE FROM public.analysis_runs WHERE id = %s", (st.session_state["confirm_delete_id"],))
                conn.commit()
                st.success(f"Run {st.session_state['confirm_delete_id']} deleted.")
                # clear selection and reset confirmation
                if "selected_run" in st.session_state and st.session_state["selected_run"] == st.session_state["confirm_delete_id"]:
                    del st.session_state["selected_run"]
                del st.session_state["confirm_delete_id"]
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to delete run: {e}")
            finally:
                cur.close()
                conn.close()
    with col2:
        if st.button("❌ Cancel"):
            del st.session_state["confirm_delete_id"]

# -------------------------------
# Sidebar: Per-File Results Panel
# -------------------------------
st.sidebar.subheader("📄 Per-File Results")
try:
    engine = create_engine("postgresql+psycopg2://postgres:admin123@localhost:5432/reviewdb")
    file_df = pd.read_sql(
    "SELECT session_id, repo_name, overall_pre_confidence, overall_post_confidence, timestamp "
    "FROM public.file_results ORDER BY timestamp DESC LIMIT 1", engine
)

    for _, row in file_df.iterrows():
        with st.sidebar.container():
            st.sidebar.markdown(f"**Session {row['session_id']} — {row['repo_name']}**")
            col1, col2, col3 = st.sidebar.columns(3)
            col1.metric("Pre Confidence", row["overall_pre_confidence"])
            col2.metric("Post Confidence", row["overall_post_confidence"])
            col3.write(f"🕒 {row['timestamp']:%Y-%m-%d %H:%M}")
            st.sidebar.markdown("---")
except Exception as e:
    st.sidebar.error(f"⚠️ Could not load file results: {e}")

# -------------------------------
# Sidebar: Error Logs Panel
# -------------------------------
st.sidebar.subheader("🚨 Error Logs")
try:
    engine = create_engine("postgresql+psycopg2://postgres:admin123@localhost:5432/reviewdb")
    error_df = pd.read_sql(
    "SELECT session_id, filename, error_message, created_at "
    "FROM public.errors ORDER BY created_at DESC LIMIT 1", engine
)

    for _, row in error_df.iterrows():
        with st.sidebar.container():
            st.sidebar.markdown(f"**Session {row['session_id']} — File: {row['filename']}**")
            st.sidebar.error(f"{row['error_message']}")
            st.sidebar.caption(f"🕒 {row['created_at']:%Y-%m-%d %H:%M}")
            st.sidebar.markdown("---")
except Exception as e:
    st.sidebar.error(f"⚠️ Could not load error logs: {e}")


# -------------------------------
# Helper: Insert into PostgreSQL
# -------------------------------
def insert_run(repo, results, overall_pre, overall_post):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO public.analysis_runs
            (repo, files, overall_pre_confidence, overall_post_confidence, results)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                repo,
                len(results),
                round(overall_pre, 2),
                round(overall_post, 2),
                Json(results)
            )
        )
        conn.commit()
        st.success("✅ Run inserted into PostgreSQL")
    except Exception as e:
        st.error(f"❌ Failed to insert into PostgreSQL: {e}")
    finally:
        cur.close()
        conn.close()
def cache_latest_session(repo, files, pre_conf, post_conf):
    r = get_redis_connection()
    summary = {
        "repo": repo,
        "files": files,
        "pre_conf": pre_conf,
        "post_conf": post_conf
    }
    try:
        r.set("latest_session", json.dumps(summary))
        st.success("✅ Latest session cached in Redis")
    except Exception as e:
        st.error(f"❌ Failed to cache session: {e}")
def insert_session(repo_name, files_analyzed, pre_conf, post_conf):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO public.sessions
            (repo_name, timestamp, files_analyzed, overall_pre_confidence, overall_post_confidence)
            VALUES (%s, NOW(), %s, %s, %s)
            RETURNING session_id
            """,
            (repo_name, files_analyzed, pre_conf, post_conf)
        )
        session_id = cur.fetchone()[0]
        conn.commit()
        return session_id
    finally:
        cur.close()
        conn.close()

# -------------------------------
# Main Logic
# -------------------------------
if uploaded_file:
    file_path, _ = save_uploaded_file_temp(uploaded_file)
    content = file_path.read_text(encoding="utf-8")
    chunks = chunk_code(content)
    if len(chunks) > 1:
        st.warning(f"File split into {len(chunks)} chunks for analysis due to size.")

    try:
        result = analyze_sync(file_path)
        result["filename"] = uploaded_file.name
        result["original_code"] = content
        display_results(result, uploaded_file.name)
        display_repo_summary([result], result["pre_confidence"], result["post_confidence"], None)

        # ✅ Insert into PostgreSQL
        session_id = insert_session("uploaded_files", 1, result["pre_confidence"], result["post_confidence"])
        insert_file_result(session_id, "uploaded_files", result)
        insert_run("uploaded_files", [result], result["pre_confidence"], result["post_confidence"])
        cache_latest_session("uploaded_files", 1, result["pre_confidence"], result["post_confidence"])

    except Exception as e:
        session_id = insert_session("uploaded_files", 1, 0, 0)
        log_error(session_id, uploaded_file.name, str(e))
        st.error(f"❌ Analysis failed for {uploaded_file.name}: {e}")

elif repo_url:
    repo_path, _ = clone_github_repo_temp(repo_url)
    subfolders = [f for f in repo_path.iterdir() if f.is_dir()]
    folder_names = [f.name for f in subfolders]

    chosen_names = st.multiselect("Choose one or more folders to review", folder_names, default=[])
    target_paths = [repo_path / name for name in chosen_names] if chosen_names else [repo_path]

    py_files = []
    for path in target_paths:
        py_files.extend(get_python_files(path))

    if py_files:
        st.subheader("📂 Repository Analysis")
        results = []
        session_id = insert_session(repo_url if repo_url else "uploaded_repo", len(py_files), 0, 0)

        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                chunks = chunk_code(content)
                if len(chunks) > 1:
                    st.warning(f"{py_file.name} split into {len(chunks)} chunks for analysis due to size.")
                result = analyze_sync(py_file)
                result["filename"] = f"{py_file.parent.name}/{py_file.name}"
                result["original_code"] = content
                results.append(result)
                display_results(result, result["filename"])
                insert_file_result(session_id, repo_url, result)
            except Exception as e:
                log_error(session_id, py_file.name, str(e))
                st.error(f"❌ Analysis failed for {py_file.name}: {e}")

        if results:
            overall_pre = sum(r["pre_confidence"] for r in results) / len(results)
            overall_post = sum(r["post_confidence"] for r in results) / len(results)

            # 🔹 Generate README using readme_llm
            readme = None
            try:
                from app.llm.readme_llm import run_llm_readme
                readme = run_llm_readme(results, overall_pre, overall_post)
            except Exception as e:
                st.warning(f"README generation failed: {e}")

            # ✅ Pass readme into display_repo_summary
            display_repo_summary(results, round(overall_pre, 2), round(overall_post, 2), readme)

            # ✅ Insert into PostgreSQL for repo runs
            insert_run(repo_url if repo_url else "uploaded_repo", results, overall_pre, overall_post)
            cache_latest_session(repo_url, len(results), overall_pre, overall_post)

    else:
        st.warning("No Python files found in the selected folders/repo.")
