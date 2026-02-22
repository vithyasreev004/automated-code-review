import streamlit as st
from pathlib import Path

from app.main import analyze_sync
from app.utils import save_uploaded_file_temp, clone_github_repo_temp, get_python_files


st.title("Automated Code Review & Documentation Assistant")

uploaded_file = st.file_uploader("Upload a Python file", type=["py"])
repo_url = st.text_input("Or enter a GitHub repository URL")

if uploaded_file:
    file_path, _ = save_uploaded_file_temp(uploaded_file)
    result = analyze_sync(file_path)

    st.subheader("Pre Confidence Score")
    st.metric("Pre", result["pre_confidence"])

    st.subheader("LLM Review")
    st.json(result["llm_review"])

    st.subheader("Refactored Code")
    st.code(result["refactored_code"], language="python")

    st.subheader("Documented Code")
    st.code(result["documented_code"], language="python")

    st.subheader("Post Confidence Score")
    st.metric("Post", result["post_confidence"])

elif repo_url:
    repo_path, _ = clone_github_repo_temp(repo_url)
    py_files = get_python_files(repo_path)
    if py_files:
        result = analyze_sync(py_files[0])  # demo: analyze first file
        st.subheader("Pre Confidence Score")
        st.metric("Pre", result["pre_confidence"])
        st.subheader("LLM Review")
        st.json(result["llm_review"])
        st.subheader("Refactored Code")
        st.code(result["refactored_code"], language="python")
        st.subheader("Documented Code")
        st.code(result["documented_code"], language="python")
        st.subheader("Post Confidence Score")
        st.metric("Post", result["post_confidence"])
