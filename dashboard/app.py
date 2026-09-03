import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
import streamlit as st

from storage.result_store import ResultStore


def main():
    st.set_page_config(page_title="AI-QA Shield Dashboard", layout="wide")
    st.title("AI-QA Shield - Security Test Dashboard")

    db_path = os.path.join(PROJECT_ROOT, "qa_safe_results.db")
    store = ResultStore(db_path=db_path)

    runs = store.list_runs()

    if not runs:
        st.info("No campaign runs found in the database.")
        return

    # Campaign selection
    campaign_options = {
        f"{run.get('campaign_name', 'Unnamed Campaign')} ({run.get('campaign_id')}) - {run.get('created_at', '')}": run.get("campaign_id")
        for run in runs
    }

    selected_label = st.selectbox(
        "Select Campaign Run:",
        options=list(campaign_options.keys())
    )

    selected_campaign_id = campaign_options[selected_label]
    campaign_data = store.get_run(selected_campaign_id)

    if not campaign_data:
        st.error(f"Campaign details could not be found for ID: {selected_campaign_id}")
        return

    # 1. Overview
    st.subheader("Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Campaign Name", campaign_data.get("campaign_name", "N/A"))
    col2.metric("Campaign ID", campaign_data.get("campaign_id", "N/A"))
    col3.metric("Status", campaign_data.get("status", "N/A"))
    col4.metric("Created Date", campaign_data.get("created_at", "N/A"))

    st.divider()

    # 2. KPI Metrics
    st.subheader("KPI Metrics")
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5, kpi_col6 = st.columns(6)
    safety_score = campaign_data.get("safety_score", 0.0)
    pass_rate = campaign_data.get("pass_rate", 0.0)
    total_tests = campaign_data.get("total_tests", 0)
    passed_tests = campaign_data.get("passed_tests", 0)
    failed_tests = campaign_data.get("failed_tests", 0)
    error_tests = campaign_data.get("error_tests", 0)

    kpi_col1.metric("Safety Score", f"{safety_score:.1f} / 100")
    kpi_col2.metric("Pass Rate", f"{pass_rate:.1f}%")
    kpi_col3.metric("Total Tests", total_tests)
    kpi_col4.metric("PASS Count", passed_tests)
    kpi_col5.metric("FAIL Count", failed_tests)
    kpi_col6.metric("ERROR Count", error_tests)

    st.divider()

    # 3. Test Results Table
    st.subheader("Test Results")
    results = campaign_data.get("results", [])

    if not results:
        st.info("No test results recorded for this campaign.")
        return

    table_data = []
    for test in results:
        table_data.append({
            "category": test.get("category", "N/A"),
            "attack_type": test.get("attack_type", "N/A"),
            "difficulty": test.get("difficulty", "N/A"),
            "severity": test.get("severity", "N/A"),
            "result": test.get("result", "N/A"),
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, width="stretch")

    st.divider()

    # 4. Test Details (Expandable)
    st.subheader("Test Details")
    for idx, test in enumerate(results, start=1):
        test_id = test.get("test_id", f"Test-{idx}")
        category = test.get("category", "Unknown")
        result = test.get("result", "UNKNOWN")

        with st.expander(f"[{result}] {test_id} - {category}"):
            st.markdown(f"**Attack Prompt:**\n{test.get('attack_prompt', test.get('prompt', 'N/A'))}")
            st.markdown(f"**Target Response:**\n{test.get('target_response', 'N/A')}")
            st.markdown(f"**Result:** `{result}`")
            st.markdown(f"**Reason:** {test.get('reason', 'N/A')}")
            st.markdown(f"**Evaluation Method:** {test.get('evaluation_method', 'N/A')}")
            st.markdown(f"**Confidence:** {test.get('confidence', test.get('classification_confidence', 'N/A'))}")


if __name__ == "__main__":
    main()
