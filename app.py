import streamlit as st
from pathlib import Path
import json
import pandas as pd
from fpdf import FPDF
from sqlalchemy import create_engine

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
# SAFE CONNECTION HELPERS
# -------------------------------
def safe_redis():
    try:
        return get_redis_connection()
    except Exception:
        return None

def safe_pg():
    try:
        return get_pg_connection()
    except Exception:
        return None

# -------------------------------
# Page Config
# -------------------------------
st.set_page_config(page_title="Automated Code Review Assistant", layout="wide", page_icon="📊")

st.title("📊 Automated Code Review & Documentation Assistant")

# -------------------------------
# Upload / Repo Input
# -------------------------------
uploaded_file = st.file_uploader("Upload a Python file", type=["py"])
repo_url = st.text_input("Or enter a GitHub repository URL")

# -------------------------------
# Redis Latest Session
# -------------------------------
st.subheader("🕒 Latest Session (Cached in Redis)")
r = safe_redis()
latest = None

if r:
    try:
        latest = r.get("latest_session")
    except Exception:
        latest = None

if latest:
    try:
        summary = json.loads(latest.decode())
        st.write(summary)
    except:
        st.info("No valid cached session")
else:
    st.info("No cached session")

# -------------------------------
# DB Functions (SAFE)
# -------------------------------
def insert_run(repo, results, overall_pre, overall_post):
    conn = safe_pg()
    if not conn:
        return
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO public.analysis_runs
            (repo, files, overall_pre_confidence, overall_post_confidence, results)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (repo, len(results), overall_pre, overall_post, json.dumps(results))
        )
        conn.commit()
    except:
        pass
    finally:
        cur.close()
        conn.close()

# -------------------------------
# File Upload Flow
# -------------------------------
if uploaded_file:
    file_path, _ = save_uploaded_file_temp(uploaded_file)

    try:
        result = analyze_sync(file_path)

        st.success("Analysis complete")
        st.json(result)

    except Exception as e:
        st.error(f"Error: {e}")

# -------------------------------
# Repo Flow (SAFE + SAME UI)
# -------------------------------
elif repo_url:

    try:
        repo_path, _ = clone_github_repo_temp(repo_url)
    except Exception as e:
        st.error(f"❌ Failed to clone repo: {e}")
        st.stop()

    # 👇 SAME FUNCTIONALITY (unchanged)
    subfolders = [f for f in repo_path.iterdir() if f.is_dir()]
    folder_names = [f.name for f in subfolders]

    chosen_names = st.multiselect(
        "Choose one or more folders to review",
        folder_names,
        default=[]
    )

    target_paths = [repo_path / name for name in chosen_names] if chosen_names else [repo_path]

    py_files = []
    for path in target_paths:
        py_files.extend(get_python_files(path))

    # ✅ SAFE CHECK
    if not py_files:
        st.warning("No Python files found in the selected folders/repo.")
        st.stop()

    results = []

    for py_file in py_files:
        try:
            result = analyze_sync(py_file)
            results.append(result)

            st.markdown(f"### {py_file.name}")
            st.json(result)

        except Exception as e:
            st.error(f"{py_file.name}: {e}")

    if results:
        overall_pre = sum(r["pre_confidence"] for r in results) / len(results)
        overall_post = sum(r["post_confidence"] for r in results) / len(results)

        st.subheader("Summary")
        st.write({
            "pre": overall_pre,
            "post": overall_post,
            "files": len(results)
        })

        insert_run(repo_url, results, overall_pre, overall_post)
