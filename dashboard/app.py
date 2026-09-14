"""PyShield UI; campaign execution and reporting stay in backend modules."""
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
import streamlit as st
from campaign.integration import run_and_store_campaign
from reports.assessment_report import build_assessment_report, render_html, render_markdown, report_filename
from storage.result_store import ResultStore

DEFAULT_CATEGORIES = ["Prompt Injection", "Sensitive Information Leakage", "RAG Security", "Hallucination"]


def _store() -> ResultStore:
    return ResultStore(db_path=os.path.join(PROJECT_ROOT, "qa_safe_results.db"))


def _run_campaign_panel(store: ResultStore) -> None:
    with st.sidebar:
        st.header("Configure assessment")
        st.caption("Choose the security tests to run against your target.")
        st.selectbox("Target system", ["Built-in Development Target"], disabled=True,
                     help="This version uses the local development target.")
        campaign_name = st.text_input("Assessment name", "PyShield Security Assessment")
        categories = st.multiselect("Security categories", DEFAULT_CATEGORIES, default=DEFAULT_CATEGORIES)
        difficulty = st.selectbox("Difficulty", ["EASY", "MEDIUM", "HARD"], index=2)
        tests_per_category = st.number_input("Tests per category", min_value=1, max_value=20, value=2, step=1)
        st.markdown("#### Adaptive testing")
        adaptive_enabled = st.toggle("Enable adaptive follow-up attacks", value=True,
                                     help="Run bounded follow-up tests when a base test fails.")
        max_iterations = st.slider("Max adaptive iterations", 1, 3, 3, disabled=not adaptive_enabled)
        st.caption(f"{len(categories) * int(tests_per_category)} base tests planned. Follow-up tests may increase the total.")
        if not st.button("Run Security Assessment", type="primary", use_container_width=True):
            return
        if not categories:
            st.error("Select at least one security category.")
            return
        config = {
            "campaign_name": campaign_name, "difficulty": difficulty,
            "tests_per_category": int(tests_per_category), "categories": categories,
            "adaptive_enabled": adaptive_enabled,
            "max_adaptive_iterations": int(max_iterations) if adaptive_enabled else 0,
        }
        try:
            with st.status("Running security assessment...", expanded=True) as status:
                status.write("Running tests and evaluating responses. This may take a few minutes.")
                output = run_and_store_campaign(config=config, result_store=store)
                completed_cleanly = output.get("status") == "COMPLETED"
                status.update(label="Assessment saved" if completed_cleanly else "Assessment saved with execution issues",
                              state="complete" if completed_cleanly else "error", expanded=False)
            st.session_state["selected_campaign_id"] = output["campaign_id"]
            st.rerun()
        except Exception:
            # Raw connection exceptions can contain target credentials.
            st.error("The assessment could not be completed. Check that the target and evaluator services are available, then try again.")


def _campaign_selector(store: ResultStore):
    runs = store.list_runs()
    if not runs:
        st.info("No assessments yet. Configure your first assessment in the sidebar.")
        return None
    by_id = {run["campaign_id"]: run for run in runs}
    ids = list(by_id)
    selected = st.session_state.get("selected_campaign_id")
    campaign_id = st.selectbox(
        "Assessment History", ids, index=ids.index(selected) if selected in ids else 0,
        format_func=lambda key: f"{by_id[key].get('campaign_name') or 'Security Assessment'} | {by_id[key].get('created_at') or 'Date not recorded'}",
    )
    st.session_state["selected_campaign_id"] = campaign_id
    return store.get_run(campaign_id)


def _render_summary(report: dict) -> None:
    st.subheader(report["campaign"]["name"])
    st.caption(f"{report['campaign']['date']} | {report['campaign']['status'].replace('_', ' ').title()}")
    columns = st.columns(3)
    columns[0].metric("Safety Score", f"{float(report['safety_score']):.1f} / 100")
    columns[1].metric("Risk Level", report["risk_level"])
    columns[2].metric("Critical Findings", len(report["critical_findings"]))
    vulnerable = report["most_vulnerable_categories"]
    if vulnerable:
        st.write("Most vulnerable category: " + str(vulnerable[0]["category"]))
        st.caption("Ranked by the number of failed tests in this assessment.")
    else:
        st.write("Most vulnerable category: None identified in the recorded tests.")
    for notice in report["notices"]:
        st.warning(notice)


def _render_overview(campaign: dict, report: dict) -> None:
    columns = st.columns(4)
    for column, (key, label) in zip(columns, [("total", "Total tests"), ("pass", "PASS"), ("fail", "FAIL"), ("error", "ERROR")]):
        column.metric(label, report["counts"][key])
    summary = campaign.get("summary") or {}
    if "pass_rate" in summary or "pass_rate" in campaign:
        st.caption(f"Pass rate: {float(summary.get('pass_rate', campaign.get('pass_rate', 0))):.1f}%")
    st.markdown("#### Failures by severity")
    st.dataframe(pd.DataFrame([{"Severity": key, "Failed tests": value}
                              for key, value in report["severity_distribution"].items()]),
                 hide_index=True, use_container_width=True)
    by_category = (campaign.get("summary") or {}).get("by_category") or {}
    if by_category:
        st.markdown("#### Category results")
        st.dataframe(pd.DataFrame([{
            "Category": name, "Total": stats.get("total", 0), "PASS": stats.get("pass", 0),
            "FAIL": stats.get("fail", 0), "ERROR": stats.get("error", 0), "Pass rate (%)": stats.get("pass_rate", 0),
        } for name, stats in by_category.items()]), hide_index=True, use_container_width=True)
    with st.expander("Risk explanation and assessment reference"):
        st.write("Score-based risk: " + str(report["risk_basis"]["score_based_risk"]))
        st.write("Severity floor applied: " + ("Yes" if report["risk_basis"]["severity_floor_applied"] else "No"))
        st.caption("The overall risk includes severity floors, so a serious finding can raise risk even with a high Safety Score.")
        st.text(report["campaign"]["id"])


def _render_findings(report: dict) -> None:
    findings = report["failed_test_evidence"]
    if not findings:
        st.info("No failed findings recorded. Check execution errors and test coverage when interpreting this result.")
        return
    for index, finding in enumerate(findings, 1):
        with st.expander(f"Finding {index} | {finding['severity']} | {finding['category']}"):
            st.write("Attack type: " + finding["attack_type"])
            st.text(finding["reason"])
            st.caption("Full prompts and responses are available under Test evidence and in the downloadable report.")
    st.markdown("#### Recommendations")
    for recommendation in report["recommendations"]:
        st.write(recommendation["category"])
        st.text(recommendation["recommendation"])
    if not report["recommendations"]:
        st.info("No category-specific recommendations were recorded.")


def _render_results(campaign: dict) -> None:
    results = campaign.get("results") or []
    if not results:
        st.info("No test evidence was recorded.")
        return
    left, right = st.columns(2)
    verdict = left.selectbox("Result filter", ["All", "FAIL", "ERROR", "PASS"])
    category = right.selectbox("Category filter", ["All"] + sorted({str(r.get("category") or "Unknown") for r in results}))
    filtered = [r for r in results if (verdict == "All" or r.get("result") == verdict)
                and (category == "All" or (r.get("category") or "Unknown") == category)]
    if not filtered:
        st.info("No tests match these filters.")
        return
    st.dataframe(pd.DataFrame([{
        "Test": index, "Category": r.get("category"), "Attack type": r.get("attack_type"),
        "Difficulty": r.get("difficulty"), "Severity": r.get("severity"), "Result": r.get("result"),
    } for index, r in enumerate(filtered, 1)]), hide_index=True, use_container_width=True)
    index = st.selectbox("Inspect test", range(len(filtered)),
                         format_func=lambda i: f"Test {i + 1} | {filtered[i].get('result', 'Unknown')} | {filtered[i].get('attack_type') or 'Attack type not recorded'}")
    test = filtered[index]
    st.caption(f"Severity: {test.get('severity') or 'Unknown'} | Evaluation method: {test.get('evaluation_method') or 'Not recorded'}")
    for label, value in [
        ("Attack prompt", test.get("prompt") or test.get("attack_prompt") or "Not recorded"),
        ("Target AI response", test.get("target_response") or "(Empty response)"),
        ("Evaluator reason", test.get("reason") or "Not recorded"),
    ]:
        st.markdown(f"**{label}**")
        st.code(str(value), language=None, wrap_lines=True)
    if test.get("expected_behavior"):
        st.write("Expected behavior: " + str(test["expected_behavior"]))
    if test.get("iteration") is not None:
        st.write(f"Adaptive iteration: {test['iteration']}")
        st.text(test.get("strategy") or "Strategy not recorded")
    with st.expander("Test reference"):
        st.text(test.get("test_id") or "Not recorded")
        if test.get("parent_test_id"):
            st.text("Parent test: " + str(test["parent_test_id"]))


def _render_exports(report: dict) -> None:
    st.markdown("#### Download security report")
    st.write("Share the assessment summary, recommendations and failed-test evidence in one report.")
    st.caption("Exports use the selected assessment. Downloading does not run tests or change saved results. Reports include test prompts and target responses.")
    html, markdown = render_html(report), render_markdown(report)
    columns = st.columns(3)
    columns[0].download_button("Download HTML", html, file_name=report_filename(report, "html"),
                               mime="text/html", use_container_width=True, on_click="ignore")
    columns[1].download_button("Download Markdown", markdown, file_name=report_filename(report, "md"),
                               mime="text/markdown", use_container_width=True, on_click="ignore")
    columns[2].download_button("Download JSON", json.dumps(report, indent=2, ensure_ascii=False),
                               file_name=report_filename(report, "json"), mime="application/json",
                               use_container_width=True, on_click="ignore")
    st.caption("HTML is self-contained and includes a print layout. Open it in a browser to print or save as PDF.")
    with st.expander("Preview report"):
        st.markdown(markdown, unsafe_allow_html=False)


def main() -> None:
    st.set_page_config(page_title="PyShield Security Assessment", page_icon="🛡️", layout="wide")
    st.title("🛡️ PyShield")
    st.caption("AI Security Assessment | Configure, test and report")
    store = _store()
    _run_campaign_panel(store)
    campaign = _campaign_selector(store)
    if campaign is None:
        return
    try:
        report = build_assessment_report(campaign)
    except (ValueError, TypeError, KeyError):
        st.error("This assessment has incomplete report data. Select another assessment.")
        return
    st.divider()
    _render_summary(report)
    overview, findings, evidence, exports = st.tabs(["Overview", "Findings", "Test evidence", "Report"])
    with overview:
        _render_overview(campaign, report)
    with findings:
        _render_findings(report)
    with evidence:
        _render_results(campaign)
    with exports:
        _render_exports(report)


if __name__ == "__main__":
    main()
