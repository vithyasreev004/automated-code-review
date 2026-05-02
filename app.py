import streamlit as st
from pathlib import Path
import json
import pandas as pd
from fpdf import FPDF
from sqlalchemy import create_engine

# -------------------------------
# SAFE IMPORTS (NO CRASH)
# -------------------------------
try:
    from app.main import analyze_sync
    from app.utils import (
        save_uploaded_file_temp,
        clone_github_repo_temp,
        get_python_files,
        chunk_code,
        get_redis_connection,
        get_pg_connection,
    )
except Exception as e:
    st.error(f"❌ Import error: {e}")
    st.stop()

# -------------------------------
# SAFE CONNECTIONS
# -------------------------------
def safe_redis():
    try:
        return get_redis_connection()
    except:
        return None

def safe_pg():
    try:
        return get_pg_connection()
    except:
        return None

# -------------------------------
# Page Config
# -------------------------------
st.set_page_config(
    page_title="Automated Code Review Assistant",
    layout="wide",
    page_icon="📊"
)

st.title("📊 Automated Code Review & Documentation Assistant")

# -------------------------------
# Upload / Repo Input
# -------------------------------
st.header("📂 Upload or Connect Repository")
uploaded_file = st.file_uploader("Upload a Python file", type=["py"])
repo_url = st.text_input("Or enter a GitHub repository URL")

# -------------------------------
# SAFE JSON PARSER
# -------------------------------
def safe_parse_json(raw_output):
    try:
        return json.loads(raw_output)
    except:
        return {}

# -------------------------------
# Display Results
# -------------------------------
def display_results(result, filename):
    st.markdown(f"### 📄 {filename}")

    col1, col2 = st.columns(2)
    col1.metric("Pre Confidence", result.get("pre_confidence", "N/A"))
    col2.metric("Post Confidence", result.get("post_confidence", "N/A"))

    review = result.get("llm_review", {})
    if review:
        st.subheader("📝 LLM Review")
        st.write(review.get("summary", "No summary"))

    if result.get("issues"):
        st.subheader("🚨 Issues")
        st.dataframe(pd.DataFrame(result["issues"]))

    if result.get("diff"):
        st.subheader("🔧 Diff")
        st.code(result["diff"], language="diff")

    if result.get("refactored_code"):
        with st.expander("✨ Refactored Code"):
            st.code(result["refactored_code"], language="python")

    if result.get("documented_code"):
        with st.expander("📖 Documented Code"):
            st.code(result["documented_code"], language="python")

# -------------------------------
# Repo Summary
# -------------------------------
def display_repo_summary(results, overall_pre):
    st.markdown("## 📊 Repository Summary")

    col1, col2 = st.columns(2)
    col1.metric("Overall Pre Confidence", overall_pre)
    col2.metric("Files Analyzed", len(results))

# -------------------------------
# Redis Cache Display
# -------------------------------
st.markdown("---")
st.subheader("🕒 Latest Session")

r = safe_redis()
if r:
    try:
        latest = r.get("latest_session")
        if latest:
            data = json.loads(latest)
            st.write(data)
    except:
        st.info("No cache available")
else:
    st.info("Redis not connected")

# -------------------------------
# MAIN LOGIC
# -------------------------------
if uploaded_file:
    try:
        file_path, _ = save_uploaded_file_temp(uploaded_file)
        result = analyze_sync(file_path)

        display_results(result, uploaded_file.name)
        display_repo_summary([result], result["pre_confidence"])

    except Exception as e:
        st.error(f"❌ Analysis failed: {e}")

# -------------------------------
# REPO LOGIC (UNCHANGED FLOW)
# -------------------------------
elif repo_url:
    try:
        repo_path, _ = clone_github_repo_temp(repo_url)

        subfolders = [f for f in repo_path.iterdir() if f.is_dir()]
        folder_names = [f.name for f in subfolders]

        chosen = st.multiselect("Select folders", folder_names)

        targets = [repo_path / f for f in chosen] if chosen else [repo_path]

        py_files = []
        for t in targets:
            py_files.extend(get_python_files(t))

        if not py_files:
            st.warning("No Python files found")
        else:
            results = []

            for py in py_files:
                try:
                    result = analyze_sync(py)
                    result["filename"] = py.name
                    results.append(result)

                    display_results(result, py.name)

                except Exception as e:
                    st.error(f"Error in {py.name}: {e}")

            overall_pre = sum(r["pre_confidence"] for r in results) / len(results)
            display_repo_summary(results, round(overall_pre, 2))

    except Exception as e:
        st.error(f"❌ Repo processing failed: {e}")
