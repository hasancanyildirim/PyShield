import os
import tempfile

from storage.result_store import ResultStore


def build_campaign():
    return {
        "campaign_id": "STORE-TEST-001",
        "campaign_name": "Persistent Storage Integration Test",
        "status": "COMPLETED_WITH_ERRORS",

        "summary": {
            "total": 3,
            "pass": 1,
            "fail": 1,
            "error": 1,
            "pass_rate": 33.33,
            "safety_score": 85.0,

            "critical_failures": 0,
            "high_failures": 1,
            "medium_failures": 0,
            "low_failures": 0,
        },

        "results": [
            {
                "test_id": "STORE-PASS-001",
                "category": "Prompt Injection",
                "attack_type": "Jailbreak",
                "difficulty": "HARD",
                "severity": "HIGH",
                "prompt": "Controlled PASS prompt",
                "target_response": "Safe response",
                "result": "PASS",
                "reason": "Target resisted the attack.",
                "evaluation_method": "CONTROLLED",
                "classification_confidence": "HIGH",
                "source": "TEST_SUITE",
                "retrieved_context": ["public-context"],
                "visibility": ["PUBLIC"],
            },

            {
                "test_id": "STORE-FAIL-001",
                "category": "Prompt Injection",
                "attack_type": "Jailbreak",
                "difficulty": "HARD",
                "severity": "HIGH",
                "prompt": "Controlled FAIL prompt",
                "target_response": "Unsafe response",
                "result": "FAIL",
                "reason": "Target followed malicious instruction.",
                "evaluation_method": "CONTROLLED",
                "classification_confidence": "HIGH",
                "source": "TEST_SUITE",
                "retrieved_context": ["public-context"],
                "visibility": ["PUBLIC"],
            },

            {
                "test_id": "STORE-ERROR-001",
                "category": "Hallucination",
                "attack_type": "Fictitious Product",
                "difficulty": "MEDIUM",
                "severity": "MEDIUM",
                "prompt": "Controlled ERROR prompt",
                "target_response": None,
                "result": "ERROR",
                "reason": "Simulated execution error.",
                "evaluation_method": "ERROR",
                "classification_confidence": "HIGH",
                "source": "ORCHESTRATOR",
                "retrieved_context": [],
                "visibility": [],
            },
        ],
    }


def test_result_store():

    # Temporary real SQLite file.
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(
        temp_dir,
        "qa_safe_task1_test.db",
    )

    campaign = build_campaign()

    # =====================================================
    # TEST 1 - INITIAL SAVE
    # =====================================================

    store = ResultStore(db_path)

    saved_id = store.save_run(campaign)

    assert saved_id == "STORE-TEST-001"
    assert os.path.exists(db_path)

    print("=" * 60)
    print("TASK 1 - RESULT STORE TEST")
    print("=" * 60)

    print("SQLite database created: PASS")
    print("save_run(): PASS")

    # =====================================================
    # TEST 2 - READ CAMPAIGN
    # =====================================================

    loaded = store.get_run("STORE-TEST-001")

    assert loaded is not None

    assert loaded["campaign_id"] == "STORE-TEST-001"

    assert (
        loaded["campaign_name"]
        == "Persistent Storage Integration Test"
    )

    assert loaded["status"] == "COMPLETED_WITH_ERRORS"

    assert loaded["total_tests"] == 3
    assert loaded["passed_tests"] == 1
    assert loaded["failed_tests"] == 1
    assert loaded["error_tests"] == 1

    assert loaded["pass_rate"] == 33.33
    assert loaded["safety_score"] == 85.0

    assert len(loaded["results"]) == 3

    print("get_run(): PASS")
    print("Campaign metrics restored: PASS")
    print("Individual test results restored: PASS")

    # =====================================================
    # TEST 3 - JSON FIELD RESTORATION
    # =====================================================

    first_result = loaded["results"][0]

    assert first_result["retrieved_context"] == [
        "public-context"
    ]

    assert first_result["visibility"] == [
        "PUBLIC"
    ]

    # Compatibility aliases
    assert first_result["prompt"] == (
        "Controlled PASS prompt"
    )

    assert (
        first_result["classification_confidence"]
        == "HIGH"
    )

    print("JSON fields restored: PASS")
    print("Compatibility aliases restored: PASS")

    # =====================================================
    # TEST 4 - FAILED TEST QUERY
    # =====================================================

    failed_tests = store.get_failed_tests(
        "STORE-TEST-001"
    )

    assert len(failed_tests) == 1

    assert (
        failed_tests[0]["test_id"]
        == "STORE-FAIL-001"
    )

    assert failed_tests[0]["result"] == "FAIL"

    # ERROR must not appear here.
    assert all(
        result["result"] == "FAIL"
        for result in failed_tests
    )

    print("get_failed_tests(): PASS")
    print("ERROR exclusion from failed tests: PASS")

    # =====================================================
    # TEST 5 - REAL PERSISTENCE
    #
    # Destroy the ResultStore object and create a completely
    # new one pointing at the same database file.
    # =====================================================

    del store

    reopened_store = ResultStore(db_path)

    reopened = reopened_store.get_run(
        "STORE-TEST-001"
    )

    assert reopened is not None
    assert reopened["campaign_id"] == "STORE-TEST-001"
    assert len(reopened["results"]) == 3

    reopened_failures = (
        reopened_store.get_failed_tests(
            "STORE-TEST-001"
        )
    )

    assert len(reopened_failures) == 1

    print("Database reopen persistence: PASS")

    # =====================================================
    # TEST 6 - UNKNOWN CAMPAIGN
    # =====================================================

    assert (
        reopened_store.get_run(
            "DOES-NOT-EXIST"
        )
        is None
    )

    print("Unknown campaign handling: PASS")

    # =====================================================
    # CLEANUP
    # =====================================================

    del reopened_store

    if os.path.exists(db_path):
        os.remove(db_path)

    os.rmdir(temp_dir)

    print("\n" + "=" * 60)
    print("ALL RESULT STORE TESTS PASSED")
    print("=" * 60)


def test_security_report_persists_and_reads_back():
    import os
    import tempfile

    from storage.result_store import ResultStore

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "security-report.db")
        store = ResultStore(db_path)

        security_report = {
            "report_version": "1.0",
            "campaign_id": "REPORT-001",
            "safety_score": 72.0,
            "risk_level": "HIGH",
            "critical_findings": [
                {
                    "test_id": "PI-001",
                    "category": "Prompt Injection",
                    "severity": "CRITICAL",
                    "reason": "Injected instruction was followed.",
                }
            ],
            "most_vulnerable_categories": [
                {
                    "category": "Prompt Injection",
                    "failed_tests": 2,
                }
            ],
            "recommendations": [
                {
                    "category": "Prompt Injection",
                    "recommendation": (
                        "Strengthen instruction hierarchy enforcement."
                    ),
                }
            ],
        }

        campaign_output = {
            "campaign_id": "REPORT-001",
            "campaign_name": "Security Report Persistence Test",
            "status": "COMPLETED",
            "summary": {
                "total": 2,
                "pass": 0,
                "fail": 2,
                "error": 0,
                "pass_rate": 0.0,
                "safety_score": 72.0,
                "critical_failures": 1,
                "high_failures": 1,
                "medium_failures": 0,
                "low_failures": 0,
            },
            "results": [],
            "security_report": security_report,
        }

        store.save_run(campaign_output)

        persisted = store.get_run("REPORT-001")

        assert persisted is not None
        assert "security_report" in persisted

        restored_report = persisted["security_report"]

        assert restored_report["campaign_id"] == "REPORT-001"
        assert restored_report["safety_score"] == 72.0
        assert restored_report["risk_level"] == "HIGH"

        assert (
            restored_report["critical_findings"][0]["category"]
            == "Prompt Injection"
        )

        assert (
            restored_report["most_vulnerable_categories"][0]["failed_tests"]
            == 2
        )

        assert (
            restored_report["recommendations"][0]["category"]
            == "Prompt Injection"
        )

if __name__ == "__main__":
    test_result_store()