import json
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
    return ResultStore(
        db_path=os.path.join(
            PROJECT_ROOT,
            "qa_safe_results.db",
        )
    )


def _run_campaign_panel(store: ResultStore) -> None:
    """Render the productized security assessment configuration panel."""
    with st.sidebar:
        st.header("Configure Security Assessment")

        st.caption(
            "Configure the assessment, run PyShield, and review the "
            "resulting risk score, findings, and test evidence."
        )

        st.selectbox(
            "Target system",
            ["Built-in Development Target"],
            index=0,
            disabled=True,
            help=(
                "The current main branch still uses the built-in TargetAI. "
                "External target selection will be enabled here when the "
                "Generic Target Adapter is integrated."
            ),
        )

        campaign_name = st.text_input(
            "Assessment name",
            "PyShield Security Assessment",
        )

        categories = st.multiselect(
            "Security categories",
            DEFAULT_CATEGORIES,
            default=DEFAULT_CATEGORIES,
        )

        difficulty = st.selectbox(
            "Difficulty",
            [
                "EASY",
                "MEDIUM",
                "HARD",
            ],
            index=2,
        )

        tests_per_category = st.number_input(
            "Tests per category",
            min_value=1,
            max_value=20,
            value=2,
            step=1,
        )

        st.markdown("#### Adaptive Testing")

        adaptive_enabled = st.toggle(
            "Enable adaptive follow-up attacks",
            value=True,
            help=(
                "When a test fails, PyShield can generate bounded follow-up "
                "attacks guided by the evaluator's failure reason."
            ),
        )

        max_adaptive_iterations = st.slider(
            "Max adaptive iterations",
            min_value=1,
            max_value=3,
            value=3,
            step=1,
            disabled=not adaptive_enabled,
        )

        planned_tests = len(categories) * int(tests_per_category)

        st.caption(
            f"Planned base tests: {planned_tests}. "
            "Adaptive follow-up tests may increase the final test count."
        )

        run_clicked = st.button(
            "Run Security Assessment",
            type="primary",
            use_container_width=True,
        )

        if not run_clicked:
            return

        if not categories:
            st.error(
                "Select at least one security category."
            )
            return

        config = {
            "campaign_name": campaign_name,
            "difficulty": difficulty,
            "tests_per_category": int(
                tests_per_category
            ),
            "categories": categories,
            "adaptive_enabled": adaptive_enabled,
            "max_adaptive_iterations": (
                int(max_adaptive_iterations)
                if adaptive_enabled
                else 0
            ),
        }

        try:
            with st.status(
                "Running security assessment...",
                expanded=True,
            ) as status:
                status.write(
                    "Configuration validated. Starting the security campaign."
                )
                status.write(
                    "Executing attacks, target responses, evaluation, and "
                    "adaptive follow-up testing."
                )

                output = run_and_store_campaign(
                    config=config,
                    result_store=store,
                )

                status.write(
                    "Security report generated, results persisted to SQLite, "
                    "and read-back verification completed."
                )

                status.update(
                    label="Security assessment completed",
                    state="complete",
                    expanded=False,
                )

            st.success(
                f"Assessment completed: "
                f"{output['campaign_id']}"
            )

            st.session_state[
                "selected_campaign_id"
            ] = output["campaign_id"]

            st.rerun()

        except Exception as error:
            st.error(
                f"Security assessment failed: {error}"
            )


def _campaign_selector(
    store: ResultStore,
):
    runs = store.list_runs()

    if not runs:
        st.info(
            "No campaign runs found. "
            "Start a campaign from the sidebar."
        )
        return None

    options = {
        (
            f"{run.get('campaign_name', 'Unnamed Campaign')} "
            f"({run.get('campaign_id')}) - "
            f"{run.get('created_at', '')}"
        ): run.get("campaign_id")
        for run in runs
    }

    labels = list(options.keys())

    selected_id = st.session_state.get(
        "selected_campaign_id"
    )

    default_index = 0

    if selected_id:
        for index, label in enumerate(labels):
            if options[label] == selected_id:
                default_index = index
                break

    selected_label = st.selectbox(
        "Assessment History",
        labels,
        index=default_index,
    )

    campaign_id = options[selected_label]

    st.session_state[
        "selected_campaign_id"
    ] = campaign_id

    return store.get_run(campaign_id)



def _render_assessment_summary(
    campaign_data: dict,
) -> None:
    """Show the most important security assessment outcome at a glance."""
    report = campaign_data.get(
        "security_report",
        {},
    ) or {}

    summary = report.get(
        "summary",
        {},
    ) or {}

    risk_level = report.get(
        "risk_level",
        "UNKNOWN",
    )

    safety_score = float(
        report.get(
            "safety_score",
            campaign_data.get(
                "safety_score",
                0.0,
            ),
        )
    )

    critical_findings = summary.get(
        "critical_findings",
        0,
    )

    vulnerable_categories = report.get(
        "most_vulnerable_categories",
        [],
    ) or []

    if vulnerable_categories:
        first_item = vulnerable_categories[0]

        if isinstance(first_item, dict):
            most_vulnerable = first_item.get(
                "category",
                "N/A",
            )
            failed_tests = first_item.get(
                "failed_tests",
                first_item.get(
                    "fail_count",
                    0,
                ),
            )
            most_vulnerable_display = (
                f"{most_vulnerable} ({failed_tests} FAIL)"
            )
        else:
            most_vulnerable_display = str(
                first_item
            )
    else:
        most_vulnerable_display = "None identified"

    st.subheader("Security Assessment Summary")

    cols = st.columns(4)

    cols[0].metric(
        "Risk Level",
        risk_level,
    )

    cols[1].metric(
        "Safety Score",
        f"{safety_score:.1f} / 100",
    )

    cols[2].metric(
        "Critical Findings",
        critical_findings,
    )

    cols[3].metric(
        "Most Vulnerable Category",
        most_vulnerable_display,
    )

    status = campaign_data.get(
        "status",
        "UNKNOWN",
    )

    if status == "COMPLETED_WITH_ERRORS":
        st.warning(
            "The assessment completed, but one or more tests returned "
            "execution errors. Review ERROR results before treating the "
            "security assessment as complete evidence."
        )
    elif status == "EMPTY":
        st.warning(
            "The assessment did not produce any test results."
        )

def _render_metrics(
    campaign_data: dict,
) -> None:
    st.subheader("Assessment Overview")

    top = st.columns(4)

    top[0].metric(
        "Campaign Name",
        campaign_data.get(
            "campaign_name",
            "N/A",
        ),
    )

    top[1].metric(
        "Campaign ID",
        campaign_data.get(
            "campaign_id",
            "N/A",
        ),
    )

    top[2].metric(
        "Status",
        campaign_data.get(
            "status",
            "N/A",
        ),
    )

    top[3].metric(
        "Created Date",
        campaign_data.get(
            "created_at",
            "N/A",
        ),
    )

    st.subheader("Security Metrics")

    cols = st.columns(6)

    cols[0].metric(
        "Safety Score",
        (
            f"{float(campaign_data.get('safety_score', 0.0)):.1f}"
            " / 100"
        ),
    )

    cols[1].metric(
        "Pass Rate",
        (
            f"{float(campaign_data.get('pass_rate', 0.0)):.1f}%"
        ),
    )

    cols[2].metric(
        "Total Tests",
        campaign_data.get(
            "total_tests",
            0,
        ),
    )

    cols[3].metric(
        "PASS",
        campaign_data.get(
            "passed_tests",
            0,
        ),
    )

    cols[4].metric(
        "FAIL",
        campaign_data.get(
            "failed_tests",
            0,
        ),
    )

    cols[5].metric(
        "ERROR",
        campaign_data.get(
            "error_tests",
            0,
        ),
    )


def _render_security_report(
    campaign_data: dict,
) -> None:
    """
    Render the deterministic PyShield security report.

    The report is stored together with the campaign and restored
    from SQLite when a historical campaign is selected.
    """

    report = campaign_data.get(
        "security_report",
        {},
    ) or {}

    st.subheader("Automatic Security Report")

    if not report:
        st.info(
            "No automatic security report is stored for "
            "this campaign. This may be an older campaign "
            "created before security reporting was enabled."
        )
        return

    risk_level = report.get(
        "risk_level",
        "UNKNOWN",
    )

    safety_score = float(
        report.get(
            "safety_score",
            0.0,
        )
    )

    summary = report.get(
        "summary",
        {},
    ) or {}

    critical_count = summary.get(
        "critical_findings",
        len(
            report.get(
                "critical_findings",
                [],
            )
        ),
    )

    high_count = summary.get(
        "high_findings",
        len(
            report.get(
                "high_findings",
                [],
            )
        ),
    )

    # ---------------------------------------------------------
    # Main report metrics
    # ---------------------------------------------------------

    report_metrics = st.columns(4)

    report_metrics[0].metric(
        "Overall Risk Level",
        risk_level,
    )

    report_metrics[1].metric(
        "Safety Score",
        f"{safety_score:.1f} / 100",
    )

    report_metrics[2].metric(
        "Critical Findings",
        critical_count,
    )

    report_metrics[3].metric(
        "High Findings",
        high_count,
    )

    # ---------------------------------------------------------
    # Risk basis
    # ---------------------------------------------------------

    risk_basis = report.get(
        "risk_basis",
        {},
    ) or {}

    with st.expander(
        "Risk Score Explanation"
    ):
        st.markdown(
            f"**Score-Based Risk:** "
            f"{risk_basis.get('score_based_risk', 'N/A')}"
        )

        st.markdown(
            f"**Severity Floor Applied:** "
            f"{risk_basis.get('severity_floor_applied', 'N/A')}"
        )

        thresholds = risk_basis.get(
            "thresholds",
            {},
        )

        if thresholds:
            threshold_rows = [
                {
                    "Risk Level": level,
                    "Minimum Safety Score": score,
                }
                for level, score in thresholds.items()
            ]

            st.dataframe(
                pd.DataFrame(
                    threshold_rows
                ),
                width="stretch",
                hide_index=True,
            )

    # ---------------------------------------------------------
    # Most vulnerable categories
    # ---------------------------------------------------------

    vulnerable_categories = report.get(
        "most_vulnerable_categories",
        [],
    ) or []

    st.markdown(
        "### Most Vulnerable Areas"
    )

    if vulnerable_categories:
        vulnerable_rows = []

        for item in vulnerable_categories:
            if isinstance(item, dict):
                vulnerable_rows.append(
                    {
                        "Category": item.get(
                            "category",
                            "N/A",
                        ),
                        "Failed Tests": item.get(
                            "failed_tests",
                            item.get(
                                "fail_count",
                                0,
                            ),
                        ),
                    }
                )
            else:
                vulnerable_rows.append(
                    {
                        "Category": str(
                            item
                        ),
                        "Failed Tests": "N/A",
                    }
                )

        st.dataframe(
            pd.DataFrame(
                vulnerable_rows
            ),
            width="stretch",
            hide_index=True,
        )

    else:
        st.success(
            "No vulnerable category was identified."
        )

    # ---------------------------------------------------------
    # Critical and High findings
    # ---------------------------------------------------------

    st.markdown(
        "### Critical & High Findings"
    )

    important_findings = []

    for finding in report.get(
        "critical_findings",
        [],
    ):
        important_findings.append(
            finding
        )

    for finding in report.get(
        "high_findings",
        [],
    ):
        important_findings.append(
            finding
        )

    if important_findings:
        for index, finding in enumerate(
            important_findings,
            start=1,
        ):
            severity = finding.get(
                "severity",
                "UNKNOWN",
            )

            category = finding.get(
                "category",
                "UNKNOWN",
            )

            test_id = finding.get(
                "test_id",
                f"Finding-{index}",
            )

            with st.expander(
                f"[{severity}] "
                f"{category} - "
                f"{test_id}"
            ):
                st.markdown(
                    f"**Category:** {category}"
                )

                st.markdown(
                    f"**Severity:** {severity}"
                )

                st.markdown(
                    f"**Finding Summary:** "
                    f"{finding.get('summary', 'N/A')}"
                )

                if finding.get(
                    "reason"
                ):
                    st.markdown(
                        f"**Evaluator Reason:** "
                        f"{finding.get('reason')}"
                    )

                if finding.get(
                    "attack_prompt"
                ):
                    st.markdown(
                        "**Attack Prompt:**"
                    )

                    st.code(
                        finding.get(
                            "attack_prompt"
                        ),
                        language=None,
                    )

                if finding.get(
                    "target_response"
                ):
                    st.markdown(
                        "**Target Response:**"
                    )

                    st.code(
                        finding.get(
                            "target_response"
                        ),
                        language=None,
                    )

    else:
        st.success(
            "No CRITICAL or HIGH findings "
            "were identified."
        )

    # ---------------------------------------------------------
    # All findings
    # ---------------------------------------------------------

    findings = report.get(
        "findings",
        [],
    ) or []

    if findings:
        with st.expander(
            "View All Security Findings"
        ):
            finding_rows = []

            for finding in findings:
                finding_rows.append(
                    {
                        "Test ID": finding.get(
                            "test_id",
                            "N/A",
                        ),
                        "Category": finding.get(
                            "category",
                            "N/A",
                        ),
                        "Severity": finding.get(
                            "severity",
                            "N/A",
                        ),
                        "Result": finding.get(
                            "result",
                            "FAIL",
                        ),
                        "Finding": finding.get(
                            "summary",
                            finding.get(
                                "reason",
                                "N/A",
                            ),
                        ),
                    }
                )

            st.dataframe(
                pd.DataFrame(
                    finding_rows
                ),
                width="stretch",
                hide_index=True,
            )

    # ---------------------------------------------------------
    # Recommendations
    # ---------------------------------------------------------

    st.markdown(
        "### Security Recommendations"
    )

    recommendations = report.get(
        "recommendations",
        [],
    ) or []

    if recommendations:
        for recommendation in recommendations:
            if isinstance(
                recommendation,
                dict,
            ):
                category = recommendation.get(
                    "category",
                    "General",
                )

                text = recommendation.get(
                    "recommendation",
                    recommendation.get(
                        "text",
                        "N/A",
                    ),
                )

                st.markdown(
                    f"- **{category}:** {text}"
                )

            else:
                st.markdown(
                    f"- {recommendation}"
                )

    else:
        st.info(
            "No additional security recommendations "
            "were generated."
        )

    # ---------------------------------------------------------
    # JSON export
    # ---------------------------------------------------------

    st.markdown(
        "### Export"
    )

    campaign_id = campaign_data.get(
        "campaign_id",
        "campaign",
    )

    report_json = json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    )

    st.download_button(
        label="Download Security Report (JSON)",
        data=report_json,
        file_name=(
            f"{campaign_id}_security_report.json"
        ),
        mime="application/json",
        use_container_width=False,
    )


def _render_risk_views(
    campaign_data: dict,
) -> None:
    summary = campaign_data.get(
        "summary",
        {},
    ) or {}

    severity = summary.get(
        "failures_by_severity",
        {},
    ) or {}

    by_category = summary.get(
        "by_category",
        {},
    ) or {}

    st.subheader("Risk View")

    left, right = st.columns(2)

    with left:
        st.markdown(
            "**Failures by Severity**"
        )

        severity_df = pd.DataFrame(
            [
                {
                    "Severity": level,
                    "FAIL Count": severity.get(
                        level,
                        0,
                    ),
                }
                for level in (
                    "CRITICAL",
                    "HIGH",
                    "MEDIUM",
                    "LOW",
                )
            ]
        )

        st.dataframe(
            severity_df,
            width="stretch",
            hide_index=True,
        )

    with right:
        st.markdown(
            "**Category Results**"
        )

        category_rows = []

        for category, stats in (
            by_category.items()
        ):
            category_rows.append(
                {
                    "Category": category,
                    "Total": stats.get(
                        "total",
                        0,
                    ),
                    "PASS": stats.get(
                        "pass",
                        0,
                    ),
                    "FAIL": stats.get(
                        "fail",
                        0,
                    ),
                    "ERROR": stats.get(
                        "error",
                        0,
                    ),
                    "Pass Rate": stats.get(
                        "pass_rate",
                        0.0,
                    ),
                    "Risk": stats.get(
                        "risk_level",
                        "UNKNOWN",
                    ),
                }
            )

        if category_rows:
            st.dataframe(
                pd.DataFrame(
                    category_rows
                ),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info(
                "No category metrics available."
            )


def _render_results(
    campaign_data: dict,
) -> None:
    results = campaign_data.get(
        "results",
        [],
    )

    st.subheader("Test Results")

    if not results:
        st.info(
            "No test results recorded "
            "for this campaign."
        )
        return

    table_data = [
        {
            "Test ID": test.get(
                "test_id",
                "N/A",
            ),
            "Category": test.get(
                "category",
                "N/A",
            ),
            "Attack Type": test.get(
                "attack_type",
                "N/A",
            ),
            "Difficulty": test.get(
                "difficulty",
                "N/A",
            ),
            "Severity": test.get(
                "severity",
                "N/A",
            ),
            "Result": test.get(
                "result",
                "N/A",
            ),
        }
        for test in results
    ]

    st.dataframe(
        pd.DataFrame(
            table_data
        ),
        width="stretch",
        hide_index=True,
    )

    st.subheader(
        "Test Details"
    )

    for index, test in enumerate(
        results,
        start=1,
    ):
        test_id = test.get(
            "test_id",
            f"Test-{index}",
        )

        result = test.get(
            "result",
            "UNKNOWN",
        )

        category = test.get(
            "category",
            "UNKNOWN",
        )

        iteration = test.get(
            "iteration"
        )

        suffix = (
            f" | Adaptive iteration {iteration}"
            if iteration is not None
            else ""
        )

        with st.expander(
            f"[{result}] "
            f"{test_id} - "
            f"{category}"
            f"{suffix}"
        ):
            attack_prompt = test.get(
                "attack_prompt",
                test.get(
                    "prompt",
                    "N/A",
                ),
            )

            st.markdown(
                "**Attack Prompt:**"
            )

            st.code(
                attack_prompt,
                language=None,
            )

            st.markdown(
                "**Target Response:**"
            )

            st.code(
                test.get(
                    "target_response",
                    "N/A",
                ),
                language=None,
            )

            st.markdown(
                f"**Severity:** "
                f"{test.get('severity', 'N/A')}"
            )

            st.markdown(
                f"**Evaluator Reason:** "
                f"{test.get('reason', 'N/A')}"
            )

            st.markdown(
                f"**Evaluation Method:** "
                f"{test.get('evaluation_method', 'N/A')}"
            )

            st.markdown(
                f"**Confidence:** "
                f"{test.get(
                    'confidence',
                    test.get(
                        'classification_confidence',
                        'N/A',
                    ),
                )}"
            )

            if (
                test.get(
                    "parent_test_id"
                )
                is not None
            ):
                st.markdown(
                    f"**Parent Test:** "
                    f"{test.get('parent_test_id')}"
                )

                st.markdown(
                    f"**Adaptive Strategy:** "
                    f"{test.get('strategy', 'N/A')}"
                )


def main() -> None:
    st.set_page_config(
        page_title="PyShield Security Assessment",
        page_icon="🛡️",
        layout="wide",
    )

    st.title(
        "🛡️ PyShield"
    )

    st.caption(
        "Autonomous AI Quality & Security Testing — Configure • Run • Assess • Report"
    )

    store = _store()

    _run_campaign_panel(
        store
    )

    campaign_data = _campaign_selector(
        store
    )

    if campaign_data is None:
        return

    st.divider()

    _render_assessment_summary(
        campaign_data
    )

    st.divider()

    _render_metrics(
        campaign_data
    )

    st.divider()

    _render_security_report(
        campaign_data
    )

    st.divider()

    _render_risk_views(
        campaign_data
    )

    st.divider()

    _render_results(
        campaign_data
    )


if __name__ == "__main__":
    main()