import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
import streamlit as st

from campaign.integration import run_and_store_campaign
from storage.result_store import ResultStore


DEFAULT_CATEGORIES = [
    "Prompt Injection",
    "Sensitive Information Leakage",
    "RAG Security",
    "Hallucination",
]


def _store() -> ResultStore:
    return ResultStore(db_path=os.path.join(PROJECT_ROOT, "qa_safe_results.db"))


def _run_campaign_panel(store: ResultStore) -> None:
    with st.sidebar:
        st.header("Run Security Campaign")
        campaign_name = st.text_input("Campaign name", "PyShield Demo Campaign")
        difficulty = st.selectbox("Difficulty", ["EASY", "MEDIUM", "HARD"], index=2)
        tests_per_category = st.number_input(
            "Tests per category", min_value=1, max_value=20, value=2, step=1
        )
        categories = st.multiselect(
            "Categories", DEFAULT_CATEGORIES, default=DEFAULT_CATEGORIES
        )

        run_clicked = st.button("Run Campaign", type="primary", use_container_width=True)
        if not run_clicked:
            return

        if not categories:
            st.error("Select at least one security category.")
            return

        config = {
            "campaign_name": campaign_name,
            "difficulty": difficulty,
            "tests_per_category": int(tests_per_category),
            "categories": categories,
        }

        try:
            with st.spinner("Running PyShield security campaign..."):
                output = run_and_store_campaign(config=config, result_store=store)
            st.success(f"Campaign completed: {output['campaign_id']}")
            st.session_state["selected_campaign_id"] = output["campaign_id"]
            st.rerun()
        except Exception as error:
            st.error(f"Campaign failed: {error}")


def _campaign_selector(store: ResultStore):
    runs = store.list_runs()
    if not runs:
        st.info("No campaign runs found. Start a campaign from the sidebar.")
        return None

    options = {
        f"{run.get('campaign_name', 'Unnamed Campaign')} ({run.get('campaign_id')}) - {run.get('created_at', '')}": run.get(
            "campaign_id"
        )
        for run in runs
    }
    labels = list(options.keys())

    selected_id = st.session_state.get("selected_campaign_id")
    default_index = 0
    if selected_id:
        for index, label in enumerate(labels):
            if options[label] == selected_id:
                default_index = index
                break

    selected_label = st.selectbox("Select Campaign Run", labels, index=default_index)
    campaign_id = options[selected_label]
    st.session_state["selected_campaign_id"] = campaign_id
    return store.get_run(campaign_id)


def _render_metrics(campaign_data: dict) -> None:
    st.subheader("Campaign Overview")
    top = st.columns(4)
    top[0].metric("Campaign Name", campaign_data.get("campaign_name", "N/A"))
    top[1].metric("Campaign ID", campaign_data.get("campaign_id", "N/A"))
    top[2].metric("Status", campaign_data.get("status", "N/A"))
    top[3].metric("Created Date", campaign_data.get("created_at", "N/A"))

    st.subheader("Security Metrics")
    cols = st.columns(6)
    cols[0].metric("Safety Score", f"{float(campaign_data.get('safety_score', 0.0)):.1f} / 100")
    cols[1].metric("Pass Rate", f"{float(campaign_data.get('pass_rate', 0.0)):.1f}%")
    cols[2].metric("Total Tests", campaign_data.get("total_tests", 0))
    cols[3].metric("PASS", campaign_data.get("passed_tests", 0))
    cols[4].metric("FAIL", campaign_data.get("failed_tests", 0))
    cols[5].metric("ERROR", campaign_data.get("error_tests", 0))


def _render_risk_views(campaign_data: dict) -> None:
    summary = campaign_data.get("summary", {}) or {}
    severity = summary.get("failures_by_severity", {}) or {}
    by_category = summary.get("by_category", {}) or {}

    st.subheader("Risk View")
    left, right = st.columns(2)

    with left:
        st.markdown("**Failures by Severity**")
        severity_df = pd.DataFrame(
            [
                {"Severity": level, "FAIL Count": severity.get(level, 0)}
                for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
            ]
        )
        st.dataframe(severity_df, width="stretch", hide_index=True)

    with right:
        st.markdown("**Category Results**")
        category_rows = []
        for category, stats in by_category.items():
            category_rows.append(
                {
                    "Category": category,
                    "Total": stats.get("total", 0),
                    "PASS": stats.get("pass", 0),
                    "FAIL": stats.get("fail", 0),
                    "ERROR": stats.get("error", 0),
                    "Pass Rate": stats.get("pass_rate", 0.0),
                    "Risk": stats.get("risk_level", "UNKNOWN"),
                }
            )
        st.dataframe(pd.DataFrame(category_rows), width="stretch", hide_index=True)


def _render_results(campaign_data: dict) -> None:
    results = campaign_data.get("results", [])
    st.subheader("Test Results")

    if not results:
        st.info("No test results recorded for this campaign.")
        return

    table_data = [
        {
            "Test ID": test.get("test_id", "N/A"),
            "Category": test.get("category", "N/A"),
            "Attack Type": test.get("attack_type", "N/A"),
            "Difficulty": test.get("difficulty", "N/A"),
            "Severity": test.get("severity", "N/A"),
            "Result": test.get("result", "N/A"),
        }
        for test in results
    ]
    st.dataframe(pd.DataFrame(table_data), width="stretch", hide_index=True)

    st.subheader("Test Details")
    for index, test in enumerate(results, start=1):
        test_id = test.get("test_id", f"Test-{index}")
        result = test.get("result", "UNKNOWN")
        category = test.get("category", "UNKNOWN")
        iteration = test.get("iteration")
        suffix = f" | Adaptive iteration {iteration}" if iteration is not None else ""

        with st.expander(f"[{result}] {test_id} - {category}{suffix}"):
            st.markdown(f"**Attack Prompt:**\n{test.get('attack_prompt', test.get('prompt', 'N/A'))}")
            st.markdown(f"**Target Response:**\n{test.get('target_response', 'N/A')}")
            st.markdown(f"**Severity:** {test.get('severity', 'N/A')}")
            st.markdown(f"**Evaluator Reason:** {test.get('reason', 'N/A')}")
            st.markdown(f"**Evaluation Method:** {test.get('evaluation_method', 'N/A')}")
            st.markdown(
                f"**Confidence:** {test.get('confidence', test.get('classification_confidence', 'N/A'))}"
            )
            if test.get("parent_test_id") is not None:
                st.markdown(f"**Parent Test:** {test.get('parent_test_id')}")
                st.markdown(f"**Adaptive Strategy:** {test.get('strategy', 'N/A')}")


def main() -> None:
    st.set_page_config(page_title="PyShield Dashboard", page_icon="🛡️", layout="wide")
    st.title("PyShield - AI Security Testing Dashboard")
    st.caption("Run campaigns, review persistent history, and inspect security evidence.")

    store = _store()
    _run_campaign_panel(store)

    campaign_data = _campaign_selector(store)
    if not campaign_data:
        return

    _render_metrics(campaign_data)
    st.divider()
    _render_risk_views(campaign_data)
    st.divider()
    _render_results(campaign_data)


if __name__ == "__main__":
    main()
