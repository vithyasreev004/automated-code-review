import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import altair as alt
import json

st.set_page_config(page_title="Code Review Dashboard", layout="wide", page_icon="📊")
st.title("📊 Code Review Monitoring Dashboard")

# -------------------------------
# Database Connection
# -------------------------------
def load_history(limit=50):
    engine = create_engine("postgresql+psycopg2://postgres:admin123@localhost:5432/reviewdb")
    query = f"""
        SELECT id, repo, files, overall_pre_confidence, overall_post_confidence, created_at, results
        FROM public.analysis_runs
        ORDER BY created_at DESC
        LIMIT {limit}
    """
    return pd.read_sql(query, engine)

# -------------------------------
# Sidebar Controls
# -------------------------------
st.sidebar.header("Filters")
limit = st.sidebar.slider("Number of runs to display", 5, 100, 20)

# -------------------------------
# Load Data
# -------------------------------
try:
    history = load_history(limit)
    if history.empty:
        st.warning("No historical runs found.")
    else:
        st.success(f"Loaded {len(history)} runs")

        # -------------------------------
        # Table View
        # -------------------------------
        st.subheader("Recent Runs")
        st.dataframe(history.drop(columns=["results"]))  # show summary without JSON

        # -------------------------------
        # Drill-down Details
        # -------------------------------
        st.subheader("Run Details")
        run_ids = history["id"].tolist()
        selected_id = st.selectbox("Choose a run ID to view details", run_ids)

        if selected_id:
            run = history[history["id"] == selected_id].iloc[0]
            st.write(f"**Repo:** {run['repo']}")
            st.write(f"**Files:** {run['files']}")
            st.write(f"**Pre Confidence:** {run['overall_pre_confidence']}")
            st.write(f"**Post Confidence:** {run['overall_post_confidence']}")
            st.write(f"**Created At:** {run['created_at']}")

            # Parse results JSON into a DataFrame
            try:
                results = run["results"]
                if isinstance(results, str):
                    results = json.loads(results)

                # Show issues in a clean table
                all_issues = []
                for r in results:
                    for i in r.get("issues", []):
                        all_issues.append({
                            "File": r.get("file"),
                            "Line": i.get("line"),
                            "Category": i.get("category"),
                            "Message": i.get("message"),
                            "Source": i.get("source")
                        })
                if all_issues:
                    st.subheader("Detected Issues")
                    st.dataframe(pd.DataFrame(all_issues))
                else:
                    st.info("No issues detected.")

                # Show diffs and docstrings in expanders
                for r in results:
                    with st.expander(f"File: {r.get('file')}"):
                        if r.get("diff"):
                            st.markdown("**Suggested Changes (Diff):**")
                            st.code(r["diff"], language="diff")
                        if r.get("documented_code"):
                            st.markdown("**Documented Code:**")
                            st.code(r["documented_code"], language="python")
                        if r.get("refactored_code"):
                            st.markdown("**Refactored Code:**")
                            st.code(r["refactored_code"], language="python")

            except Exception as e:
                st.error(f"⚠️ Could not parse results JSON: {e}")

        # -------------------------------
        # Trend Charts (Altair)
        # -------------------------------
        st.subheader("Confidence Trends")
        trend_data = history[["created_at", "overall_pre_confidence", "overall_post_confidence"]]
        trend_data = trend_data.melt("created_at", var_name="Confidence Type", value_name="Score")

        chart = alt.Chart(trend_data).mark_line(point=True).encode(
            x="created_at:T",
            y="Score:Q",
            color="Confidence Type:N",
            tooltip=["created_at", "Confidence Type", "Score"]
        ).properties(title="Confidence Trends Over Time")

        st.altair_chart(chart, use_container_width=True)

        st.subheader("Files Analyzed per Run")
        bar_chart = alt.Chart(history).mark_bar().encode(
            x="created_at:T",
            y="files:Q",
            tooltip=["id", "repo", "files"]
        ).properties(title="Files Analyzed per Run")

        st.altair_chart(bar_chart, use_container_width=True)

        # -------------------------------
        # Issue Distribution (Pie Chart)
        # -------------------------------
        issue_counts = []
        for _, run in history.iterrows():
            results = run["results"]
            if isinstance(results, str):
                results = json.loads(results)
            for r in results:
                for i in r.get("issues", []):
                    issue_counts.append(i.get("category"))

        if issue_counts:
            issue_df = pd.DataFrame(issue_counts, columns=["Category"])
            pie_data = issue_df["Category"].value_counts().reset_index()
            pie_data.columns = ["Category", "Count"]

            pie_chart = alt.Chart(pie_data).mark_arc().encode(
                theta="Count:Q",
                color="Category:N",
                tooltip=["Category", "Count"]
            ).properties(title="Issue Distribution")

            st.subheader("Issue Distribution")
            st.altair_chart(pie_chart, use_container_width=True)

        # -------------------------------
        # KPI Metrics
        # -------------------------------
        avg_pre = history["overall_pre_confidence"].mean()
        avg_post = history["overall_post_confidence"].mean()
        total_files = history["files"].sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("Avg Pre Confidence", round(avg_pre, 2))
        col2.metric("Avg Post Confidence", round(avg_post, 2))
        col3.metric("Total Files Reviewed", int(total_files))

except Exception as e:
    st.error(f"⚠️ Could not load history: {e}")
