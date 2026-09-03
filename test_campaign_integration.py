import os
import tempfile
import unittest
from unittest.mock import patch

from campaign.campaign_runner import run_campaign
from campaign.integration import run_and_store_campaign, validate_demo_contract
from storage.result_store import ResultStore


class CampaignIntegrationTests(unittest.TestCase):
    def _config(self, difficulty="HARD", tests_per_category=1, categories=None):
        return {
            "campaign_name": "Integration Test Campaign",
            "difficulty": difficulty,
            "tests_per_category": tests_per_category,
            "categories": categories or ["Prompt Injection"],
        }

    @staticmethod
    def _result(verdict="PASS", severity="HIGH", category="Prompt Injection", index=1):
        return {
            "test_id": f"TEST-{index}",
            "category": category,
            "attack_type": "Role Manipulation / Jailbreak",
            "difficulty": "HARD",
            "severity": severity,
            "source": "TEST",
            "classification_confidence": "HIGH",
            "prompt": f"attack-{index}",
            "target_response": f"response-{index}",
            "retrieved_context": [],
            "visibility": [],
            "result": verdict,
            "reason": f"controlled-{verdict.lower()}",
            "evaluation_method": "TEST",
        }

    def test_run_and_store_campaign_persists_and_reads_back(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "results.db")
            store = ResultStore(db_path=db_path)

            with patch(
                "campaign.campaign_runner.run_single_test",
                return_value=self._result("PASS"),
            ):
                output = run_and_store_campaign(
                    self._config(),
                    result_store=store,
                    red_agent=object(),
                    target_ai=object(),
                )

            persisted = store.get_run(output["campaign_id"])
            self.assertIsNotNone(persisted)
            self.assertEqual(len(persisted["results"]), 1)
            self.assertEqual(persisted["summary"]["pass"], 1)
            self.assertEqual(persisted["summary"]["fail"], 0)

    def test_metrics_and_category_contract_match_results(self):
        controlled = [
            self._result("PASS", "HIGH", index=1),
            self._result("FAIL", "CRITICAL", index=2),
            self._result("ERROR", "UNKNOWN", index=3),
        ]

        with patch(
            "campaign.campaign_runner.run_single_test",
            side_effect=controlled,
        ):
            output = run_campaign(
                self._config(tests_per_category=3),
                red_agent=object(),
                target_ai=object(),
            )

        summary = output["summary"]
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["pass"], 1)
        self.assertEqual(summary["fail"], 1)
        self.assertEqual(summary["error"], 1)
        self.assertAlmostEqual(summary["pass_rate"], 33.33, places=2)
        self.assertEqual(summary["failures_by_severity"]["CRITICAL"], 1)
        self.assertEqual(summary["by_category"]["Prompt Injection"]["total"], 3)
        self.assertEqual(output["status"], "COMPLETED_WITH_ERRORS")
        validate_demo_contract(output)

    def test_safety_score_drops_with_failure_severity(self):
        scores = {}
        for severity in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            with patch(
                "campaign.campaign_runner.run_single_test",
                return_value=self._result("FAIL", severity),
            ):
                output = run_campaign(
                    self._config(),
                    red_agent=object(),
                    target_ai=object(),
                )
            scores[severity] = output["summary"]["safety_score"]

        self.assertGreater(scores["LOW"], scores["MEDIUM"])
        self.assertGreater(scores["MEDIUM"], scores["HIGH"])
        self.assertGreater(scores["HIGH"], scores["CRITICAL"])
        self.assertEqual(scores["CRITICAL"], 75.0)

    def test_single_execution_exception_becomes_error_and_campaign_continues(self):
        controlled = [
            self._result("PASS", index=1),
            RuntimeError("simulated target failure"),
            self._result("PASS", index=3),
        ]

        with patch(
            "campaign.campaign_runner.run_single_test",
            side_effect=controlled,
        ):
            output = run_campaign(
                self._config(tests_per_category=3),
                red_agent=object(),
                target_ai=object(),
            )

        self.assertEqual(output["summary"]["total"], 3)
        self.assertEqual(output["summary"]["pass"], 2)
        self.assertEqual(output["summary"]["error"], 1)
        self.assertEqual(output["status"], "COMPLETED_WITH_ERRORS")
        self.assertEqual(output["results"][1]["result"], "ERROR")

    def test_smoke_config_variations(self):
        cases = [
            self._config("EASY", 1, ["Hallucination"]),
            self._config("MEDIUM", 2, ["RAG Security"]),
            self._config(
                "HARD",
                1,
                ["Prompt Injection", "Sensitive Information Leakage"],
            ),
        ]

        for config in cases:
            with self.subTest(config=config):
                generated = []

                def fake_run_single_test(red_agent, target_ai, config, used_test_ids, pre_generated_record=None):
                    index = len(generated) + 1
                    result = self._result(
                        "PASS",
                        "HIGH",
                        category=config["category"],
                        index=index,
                    )
                    result["difficulty"] = config["difficulty"]
                    generated.append(result)
                    return result

                with patch(
                    "campaign.campaign_runner.run_single_test",
                    side_effect=fake_run_single_test,
                ):
                    output = run_campaign(
                        config,
                        red_agent=object(),
                        target_ai=object(),
                    )

                expected_total = config["tests_per_category"] * len(config["categories"])
                self.assertEqual(output["summary"]["total"], expected_total)
                self.assertEqual(output["summary"]["error"], 0)
                self.assertEqual(output["summary"]["fail"], 0)
                self.assertEqual(output["summary"]["pass_rate"], 100.0)


if __name__ == "__main__":
    unittest.main()
