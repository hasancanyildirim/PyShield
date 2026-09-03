"""Campaign execution + persistence integration for the PyShield MVP."""

from typing import Optional

from campaign.campaign_runner import run_campaign
from storage.result_store import ResultStore


REQUIRED_REPORTING_FIELDS = {
    "campaign_id",
    "date",
    "safety_score",
    "pass_rate",
    "fail_rate",
    "error_rate",
    "severity_distribution",
    "category_results",
    "test_count",
    "adaptive_iterations",
}


def validate_demo_contract(campaign_output: dict) -> None:
    """Validate fields required by persistence and the dashboard/demo layer."""
    if not isinstance(campaign_output, dict):
        raise ValueError("Campaign output must be a dictionary.")

    if not campaign_output.get("campaign_id"):
        raise ValueError("Campaign output is missing campaign_id.")

    if not isinstance(campaign_output.get("results"), list):
        raise ValueError("Campaign output must contain a results list.")

    summary = campaign_output.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("Campaign output must contain a summary dictionary.")

    for field in ("total", "pass", "fail", "error", "pass_rate", "safety_score", "by_category"):
        if field not in summary:
            raise ValueError(f"Campaign summary is missing required field: {field}")

    reporting = campaign_output.get("reporting")
    if not isinstance(reporting, dict):
        raise ValueError("Campaign output must contain the standardized reporting contract.")

    missing = REQUIRED_REPORTING_FIELDS.difference(reporting)
    if missing:
        raise ValueError(
            "Reporting contract is missing required fields: "
            + ", ".join(sorted(missing))
        )


def run_and_store_campaign(
    config: dict,
    result_store: Optional[ResultStore] = None,
    db_path: str = "qa_safe_results.db",
    red_agent=None,
    target_ai=None,
) -> dict:
    """Run a campaign, validate its demo contract, persist it, and verify read-back."""
    campaign_output = run_campaign(
        config=config,
        red_agent=red_agent,
        target_ai=target_ai,
    )

    validate_demo_contract(campaign_output)

    store = result_store or ResultStore(db_path=db_path)
    campaign_id = store.save_run(campaign_output)

    persisted = store.get_run(campaign_id)
    if persisted is None:
        raise RuntimeError(
            f"Campaign {campaign_id} was saved but could not be read back."
        )

    persisted_result_count = len(persisted.get("results", []))
    expected_result_count = len(campaign_output.get("results", []))
    if persisted_result_count != expected_result_count:
        raise RuntimeError(
            "Persisted campaign result count does not match execution output: "
            f"expected {expected_result_count}, got {persisted_result_count}."
        )

    return campaign_output
