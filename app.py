import streamlit as st
from pathlib import Path
import io
from fpdf import FPDF

from app.main import analyze_sync
from app.utils import save_uploaded_file_temp, clone_github_repo_temp, get_python_files, chunk_code

st.title("Automated Code Review & Documentation Assistant")

uploaded_file = st.file_uploader("Upload a Python file", type=["py"])
repo_url = st.text_input("Or enter a GitHub repository URL")

# -------------------------------
# Export Functions
# -------------------------------
def export_markdown(results, overall_pre, overall_post):
    md = f"# Repository Report\n\nPre Confidence: {overall_pre}\nPost Confidence: {overall_post}\n\n"
    for r in results:
        md += f"## {r['file']}\n"
        md += f"- Pre Confidence: {r['pre_confidence']}\n"
        md += f"- Post Confidence: {r['post_confidence']}\n"
        md += f"- Issues: {len(r['llm_review'].get('issues', []))}\n\n"
    return md

def export_pdf(results, overall_pre, overall_post):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Repository Report", ln=True)
    pdf.cell(200, 10, txt=f"Pre Confidence: {overall_pre}", ln=True)
    pdf.cell(200, 10, txt=f"Post Confidence: {overall_post}", ln=True)
    for r in results:
        pdf.cell(200, 10, txt=f"File: {r['file']}", ln=True)
        pdf.cell(200, 10, txt=f"Pre: {r['pre_confidence']} Post: {r['post_confidence']}", ln=True)
    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()

# -------------------------------
# Display Functions
# -------------------------------
def display_results(result, filename: str):
    st.markdown(f"## Results for {filename}")
    st.metric("Pre Confidence Score", result.get("pre_confidence", "N/A"))

    if "llm_review" in result:
        review = result["llm_review"]

        if review.get("summary") == "LLM rate limit exceeded":
            st.warning("⚠️ Review skipped due to API rate limit. Try again later.")
        elif review.get("summary", "").startswith("LLM error"):
            st.error(f"❌ Review failed: {review.get('summary')}")
        else:
            if "summary" in review and review["summary"]:
                st.subheader("LLM Review Summary")
                st.write(review["summary"])

            if "confidence" in review:
                st.metric("LLM Review Confidence", review.get("confidence", "N/A"))

            issues = review.get("issues", [])
            if issues:
                st.subheader("Detected Issues")
                st.table([{
                    "Category": i.get("category"),
                    "Severity": i.get("severity"),
                    "Line": i.get("line"),
                    "Suggestion": i.get("suggestion")
                } for i in issues])
            else:
                st.info("No issues detected.")

    if "diff" in result and result["diff"]:
        st.subheader("Suggested Changes (Diff)")
        st.code(result["diff"], language="diff")

    if "refactored_code" in result:
        with st.expander("Refactored Code"):
            if result.get("refactored_code") == result.get("original_code"):
                st.info("ℹ️ Original code used as fallback (no refactor generated).")
            st.code(result["refactored_code"], language="python")

    if "documented_code" in result:
        with st.expander("Documented Code"):
            if result.get("documented_code", "").startswith('"""Auto-generated documentation stub."""'):
                st.info("ℹ️ Stub documentation added (no docstrings generated).")
            st.code(result["documented_code"], language="python")

    st.metric("Post Confidence Score", result.get("post_confidence", "N/A"))

def display_repo_summary(results: list, overall_pre: float, overall_post: float, readme: str):
    st.markdown("## Repository Summary")
    st.metric("Overall Pre Confidence", overall_pre)
    st.metric("Overall Post Confidence", overall_post)
    st.write(f"Files analyzed: {len(results)}")

    # 🔹 Repo-level insights
    all_issues = []
    for r in results:
        all_issues.extend(r["llm_review"].get("issues", []))

    total_issues = len(all_issues)
    st.write(f"Issues detected: {total_issues}")

    if total_issues > 0:
        st.subheader("Repo-Level Insights")

        category_counts = {}
        for issue in all_issues:
            cat = issue.get("category", "Uncategorized")
            category_counts[cat] = category_counts.get(cat, 0) + 1
        st.write("**Issues by Category:**")
        st.table([{"Category": k, "Count": v} for k, v in category_counts.items()])

        severity_counts = {}
        for issue in all_issues:
            sev = issue.get("severity", "Unknown")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        st.write("**Issues by Severity:**")
        st.table([{"Severity": k, "Count": v} for k, v in severity_counts.items()])

    # 🔹 Aggregated patterns
    missing_docstrings = sum(1 for r in results if r["documented_code"].startswith('"""Auto-generated documentation stub."""'))
    st.write(f"Files missing docstrings: {missing_docstrings}")

    fallback_refactors = sum(1 for r in results if r["refactored_code"] == r.get("original_code"))
    st.write(f"Files without refactor changes: {fallback_refactors}")

    if readme:
        with st.expander("Generated README.md"):
            st.code(readme, language="markdown")

    # Export options
    st.download_button("Download Report (JSON)", str({"overall_pre":overall_pre,"overall_post":overall_post,"files":results}), "repo_report.json")
    st.download_button("Download Report (Markdown)", export_markdown(results, overall_pre, overall_post), "repo_report.md")
    st.download_button("Download Report (PDF)", export_pdf(results, overall_pre, overall_post), "repo_report.pdf")

# -------------------------------
# Main Logic
# -------------------------------
if uploaded_file:
    file_path, _ = save_uploaded_file_temp(uploaded_file)
    content = file_path.read_text(encoding="utf-8")
    chunks = chunk_code(content)
    if len(chunks) > 1:
        st.warning(f"File split into {len(chunks)} chunks for analysis due to size.")
    result = analyze_sync(file_path)
    result["filename"] = uploaded_file.name
    result["original_code"] = content  # provenance tracking
    display_results(result, uploaded_file.name)
    display_repo_summary([result], result["pre_confidence"], result["post_confidence"], None)

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
        st.subheader("Repository Analysis")
        results = []
        for py_file in py_files:
            content = py_file.read_text(encoding="utf-8")
            chunks = chunk_code(content)
            if len(chunks) > 1:
                st.warning(f"{py_file.name} split into {len(chunks)} chunks for analysis due to size.")
            result = analyze_sync(py_file)
            result["filename"] = f"{py_file.parent.name}/{py_file.name}"
            result["original_code"] = content  # provenance tracking
            results.append(result)
            display_results(result, result["filename"])

        overall_pre = sum(r["pre_confidence"] for r in results) / len(results)
        overall_post = sum(r["post_confidence"] for r in results) / len(results)
        display_repo_summary(results, round(overall_pre,2), round(overall_post,2), None)
    else:
        st.warning("No Python files found in the selected folders/repo.")
