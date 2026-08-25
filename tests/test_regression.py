"""
AI-QA Shield: Lightweight Regression Checks.

Verifies the integrity of the standardized test registry schema
and the Target AI output contract.
"""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from target_ai.target_bot import ask_target_bot
from tests.test_registry import BASELINE_TESTS, get_test_by_id


REQUIRED_FIELDS = {
    "test_id",
    "category",
    "attack_type",
    "severity",
    "prompt",
    "expected_behavior",
}


def check_required_fields():
    """1. All baseline tests must contain all required fields."""
    for test in BASELINE_TESTS:
        missing_fields = REQUIRED_FIELDS - test.keys()
        assert not missing_fields, f"Test {test.get('test_id')} is missing fields: {missing_fields}"
        for field in REQUIRED_FIELDS:
            assert isinstance(test[field], str) and test[field].strip(), (
                f"Test {test.get('test_id')} field '{field}' must be a non-empty string"
            )
    print("[PASS] Check 1: All baseline tests contain all required fields.")


def check_unique_test_ids():
    """2. All test_id values must be unique."""
    test_ids = [test["test_id"] for test in BASELINE_TESTS]
    assert len(test_ids) == len(set(test_ids)), f"Duplicate test_ids found: {test_ids}"
    print("[PASS] Check 2: All test_id values are unique.")


def check_get_test_by_id():
    """3. get_test_by_id() must correctly return known baseline tests."""
    expected_ids = ["RAG-001", "SIL-001", "HAL-001", "PI-001"]
    for test_id in expected_ids:
        test = get_test_by_id(test_id)
        assert test is not None, f"get_test_by_id('{test_id}') returned None"
        assert test["test_id"] == test_id, (
            f"Expected test_id '{test_id}', got '{test['test_id']}'"
        )
    print("[PASS] Check 3: get_test_by_id correctly returned all expected baseline tests.")


def check_target_contract():
    """4 & 5. ask_target_bot(..., test_mode=True) must return a dict with target_response, retrieved_context, and visibility list."""
    query = "What is the default SSH port for NovaCloud VMs?"
    result = ask_target_bot(query, test_mode=True)

    assert isinstance(result, dict), f"Expected dict from ask_target_bot with test_mode=True, got {type(result)}"
    assert "target_response" in result, "Missing 'target_response' in ask_target_bot result"
    assert "retrieved_context" in result, "Missing 'retrieved_context' in ask_target_bot result"
    assert "visibility" in result, "Missing 'visibility' in ask_target_bot result"
    print("[PASS] Check 4: ask_target_bot(test_mode=True) returns expected dictionary keys.")

    assert isinstance(result["visibility"], list), f"Expected 'visibility' to be list, got {type(result['visibility'])}"
    print("[PASS] Check 5: 'visibility' field is a list.")


def run_all_checks():
    print("=" * 60)
    print("AI-QA SHIELD - REGRESSION CHECKS")
    print("=" * 60)
    check_required_fields()
    check_unique_test_ids()
    check_get_test_by_id()
    check_target_contract()
    print("=" * 60)
    print("All regression checks passed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_checks()
