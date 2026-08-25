from collections import defaultdict

from red_agent.red_agent import DynamicRedAgent
from target_ai.target_bot import TargetAI
from evaluator.evaluator import evaluate_target_response


TESTS_PER_CATEGORY = 2

TEST_CONFIGS = [
    {
        "category": "Prompt Injection",
        "attack_type": "Role Manipulation / Jailbreak",
        "difficulty": "HARD",
    },
    {
        "category": "Sensitive Information Leakage",
        "attack_type": "Data Exfiltration Attempt",
        "difficulty": "HARD",
    },
    {
        "category": "RAG Security",
        "attack_type": "Context Poisoning",
        "difficulty": "HARD",
    },
    {
        "category": "Hallucination",
        "attack_type": "Fictitious Product",
        "difficulty": "MEDIUM",
    },
]


def run_single_test(
    red_agent,
    target_ai,
    config,
    used_test_ids
):
    """
    Generates and executes one test.

    Selection strategy:
    1. Try requested attack type.
    2. Avoid duplicate test IDs.
    3. If the exact attack-type pool is too small,
       broaden selection inside the same category.
    4. Execute Target AI.
    5. Evaluate the response.
    """

    test_record = None
    candidate = None

    # -----------------------------------------------------
    # RED AGENT - PRIMARY SELECTION
    # -----------------------------------------------------

    for _ in range(20):

        candidate = red_agent.generate_attack(
            category=config["category"],
            attack_type=config["attack_type"],
            difficulty=config["difficulty"],
        )

        candidate_id = candidate.get(
            "test_id"
        )

        if candidate_id not in used_test_ids:
            test_record = candidate
            break

    # -----------------------------------------------------
    # RED AGENT - DIVERSE FALLBACK SELECTION
    # -----------------------------------------------------

    if test_record is None:

        for _ in range(30):

            candidate = red_agent.generate_attack(
                category=config["category"],
                attack_type="__DIVERSE_SELECTION__",
                difficulty=config["difficulty"],
            )

            candidate_id = candidate.get(
                "test_id"
            )

            if candidate_id not in used_test_ids:
                test_record = candidate
                break

    # -----------------------------------------------------
    # ABSOLUTE LAST RESORT
    # -----------------------------------------------------

    if test_record is None:

        if candidate is None:

            candidate = red_agent.generate_attack(
                category=config["category"],
                attack_type=config["attack_type"],
                difficulty=config["difficulty"],
            )

        test_record = candidate

    test_id = test_record.get(
        "test_id"
    )

    if test_id:
        used_test_ids.add(
            test_id
        )

    # -----------------------------------------------------
    # PRINT TEST INFORMATION
    # -----------------------------------------------------

    print(
        "\n" + "=" * 70
    )

    print(
        f"[{test_record.get('test_id')}] "
        f"{test_record.get('category')} - "
        f"{test_record.get('attack_type')}"
    )

    print(
        "=" * 70
    )

    print(
        f"Difficulty: "
        f"{test_record.get('difficulty', 'UNKNOWN')}"
    )

    print(
        f"Severity:   "
        f"{test_record.get('severity', 'UNKNOWN')}"
    )

    print(
        f"Source:     "
        f"{test_record.get('source', 'UNKNOWN')}"
    )

    print(
        f"Confidence: "
        f"{test_record.get('classification_confidence', 'UNKNOWN')}"
    )

    if test_record.get(
        "template_repaired"
    ):

        print(
            "Template:   REPAIRED"
        )

    print(
        "\n[EXPECTED BEHAVIOR]"
    )

    print(
        test_record.get(
            "expected_behavior",
            ""
        )
    )

    print(
        "\n[DYNAMIC RED AGENT PROMPT]"
    )

    print(
        test_record.get(
            "prompt",
            ""
        )
    )

    # -----------------------------------------------------
    # TARGET AI
    # -----------------------------------------------------

    try:

        target_data = target_ai.generate_response(
            test_record.get(
                "prompt",
                ""
            ),
            test_mode=True
        )

    except Exception as error:

        result = test_record.copy()

        result[
            "result"
        ] = "ERROR"

        result[
            "reason"
        ] = (
            f"Target AI failed: {error}"
        )

        result[
            "evaluation_method"
        ] = "ERROR"

        print(
            "\n[TARGET AI ERROR]"
        )

        print(
            error
        )

        return result

    # -----------------------------------------------------
    # TARGET AI STRUCTURE VALIDATION
    # -----------------------------------------------------

    if not isinstance(
        target_data,
        dict
    ):

        result = test_record.copy()

        result[
            "result"
        ] = "ERROR"

        result[
            "reason"
        ] = (
            "Target AI did not return structured test data."
        )

        result[
            "evaluation_method"
        ] = "ERROR"

        print(
            "\n[TARGET AI ERROR]"
        )

        print(
            "Target AI returned invalid test data."
        )

        return result

    target_response = target_data.get(
        "target_response",
        ""
    )

    retrieved_context = target_data.get(
        "retrieved_context",
        []
    )

    visibility = target_data.get(
        "visibility",
        []
    )

    print(
        "\n[TARGET AI RESPONSE]"
    )

    print(
        target_response
    )

    print(
        "\n[RETRIEVAL INFO]"
    )

    print(
        f"Retrieved Chunks: "
        f"{len(retrieved_context)}"
    )

    print(
        f"Visibility: "
        f"{visibility}"
    )

    # -----------------------------------------------------
    # EVALUATOR
    # -----------------------------------------------------

    try:

        evaluation_result = (
            evaluate_target_response(
                test_record=test_record,
                target_response=target_response,
                retrieved_context=retrieved_context,
                visibility=visibility
            )
        )

    except Exception as error:

        evaluation_result = (
            test_record.copy()
        )

        evaluation_result[
            "target_response"
        ] = target_response

        evaluation_result[
            "retrieved_context"
        ] = retrieved_context

        evaluation_result[
            "visibility"
        ] = visibility

        evaluation_result[
            "result"
        ] = "ERROR"

        evaluation_result[
            "reason"
        ] = (
            f"Evaluator failed: {error}"
        )

        evaluation_result[
            "evaluation_method"
        ] = "ERROR"

    # -----------------------------------------------------
    # PRINT EVALUATOR RESULT
    # -----------------------------------------------------

    print(
        "\n[EVALUATOR RESULT]"
    )

    print(
        f"Result: "
        f"{evaluation_result.get('result', 'ERROR')}"
    )

    print(
        f"Reason: "
        f"{evaluation_result.get('reason', 'No reason')}"
    )

    print(
        f"Method: "
        f"{evaluation_result.get('evaluation_method', 'UNKNOWN')}"
    )

    return evaluation_result


def run_tests():

    print("=" * 70)

    print(
        "QA SAFE - DYNAMIC AI SECURITY TESTING"
    )

    print("=" * 70)

    print(
        f"Tests per category: "
        f"{TESTS_PER_CATEGORY}"
    )

    print(
        f"Planned total tests: "
        f"{TESTS_PER_CATEGORY * len(TEST_CONFIGS)}"
    )

    red_agent = DynamicRedAgent()
    target_ai = TargetAI()

    final_results = []

    used_test_ids = set()

    # -----------------------------------------------------
    # EXECUTION
    # -----------------------------------------------------

    for config in TEST_CONFIGS:

        print(
            "\n\n" + "#" * 70
        )

        print(
            f"CATEGORY: {config['category']}"
        )

        print(
            "#" * 70
        )

        for test_number in range(
            1,
            TESTS_PER_CATEGORY + 1
        ):

            print(
                f"\nRunning "
                f"{config['category']} "
                f"test {test_number}/"
                f"{TESTS_PER_CATEGORY}"
            )

            try:

                result = run_single_test(
                    red_agent=red_agent,
                    target_ai=target_ai,
                    config=config,
                    used_test_ids=used_test_ids
                )

            except Exception as error:

                result = {
                    "test_id": "ORCHESTRATOR-ERROR",
                    "category": config[
                        "category"
                    ],
                    "attack_type": config[
                        "attack_type"
                    ],
                    "difficulty": config[
                        "difficulty"
                    ],
                    "severity": "UNKNOWN",
                    "source": "ORCHESTRATOR",
                    "classification_confidence": (
                        "UNKNOWN"
                    ),
                    "result": "ERROR",
                    "reason": (
                        f"Orchestrator failed: {error}"
                    ),
                    "evaluation_method": "ERROR",
                }

                print(
                    "\n[ORCHESTRATOR ERROR]"
                )

                print(
                    error
                )

            final_results.append(
                result
            )

    # -----------------------------------------------------
    # CATEGORY STATISTICS
    # -----------------------------------------------------

    category_stats = defaultdict(
        lambda: {
            "PASS": 0,
            "FAIL": 0,
            "ERROR": 0,
            "TOTAL": 0,
        }
    )

    for result in final_results:

        category = result.get(
            "category",
            "UNKNOWN"
        )

        verdict = result.get(
            "result",
            "ERROR"
        )

        if verdict not in {
            "PASS",
            "FAIL",
            "ERROR"
        }:
            verdict = "ERROR"

        category_stats[
            category
        ][
            verdict
        ] += 1

        category_stats[
            category
        ][
            "TOTAL"
        ] += 1

    # -----------------------------------------------------
    # GENERAL STATISTICS
    # -----------------------------------------------------

    pass_count = sum(
        result.get("result") == "PASS"
        for result in final_results
    )

    fail_count = sum(
        result.get("result") == "FAIL"
        for result in final_results
    )

    error_count = sum(
        result.get("result") == "ERROR"
        for result in final_results
    )

    total_count = len(
        final_results
    )

    # -----------------------------------------------------
    # FINAL REPORT
    # -----------------------------------------------------

    print(
        "\n\n" + "=" * 70
    )

    print(
        "QA SAFE - DYNAMIC TEST REPORT"
    )

    print(
        "=" * 70
    )

    for result in final_results:

        print(
            f"{result.get('test_id')} | "
            f"{result.get('category')} | "
            f"{result.get('difficulty', 'UNKNOWN')} | "
            f"{result.get('severity', 'UNKNOWN')} | "
            f"{result.get('source', 'UNKNOWN')} | "
            f"{result.get('classification_confidence', 'UNKNOWN')} | "
            f"{result.get('result', 'ERROR')}"
        )

    # -----------------------------------------------------
    # CATEGORY REPORT
    # -----------------------------------------------------

    print(
        "\n" + "-" * 70
    )

    print(
        "CATEGORY RESULTS"
    )

    print(
        "-" * 70
    )

    for config in TEST_CONFIGS:

        category = config[
            "category"
        ]

        stats = category_stats[
            category
        ]

        category_total = (
            stats["TOTAL"]
        )

        if category_total:

            category_pass_rate = (
                stats["PASS"]
                / category_total
            ) * 100

        else:
            category_pass_rate = 0.0

        print(
            f"{category}: "
            f"PASS={stats['PASS']} | "
            f"FAIL={stats['FAIL']} | "
            f"ERROR={stats['ERROR']} | "
            f"TOTAL={category_total} | "
            f"PASS RATE="
            f"{category_pass_rate:.1f}%"
        )

    # -----------------------------------------------------
    # OVERALL REPORT
    # -----------------------------------------------------

    print(
        "\n" + "-" * 70
    )

    print(
        "OVERALL RESULTS"
    )

    print(
        "-" * 70
    )

    print(
        f"PASS:  {pass_count}"
    )

    print(
        f"FAIL:  {fail_count}"
    )

    print(
        f"ERROR: {error_count}"
    )

    print(
        f"TOTAL: {total_count}"
    )

    if total_count:

        pass_rate = (
            pass_count
            / total_count
        ) * 100

        fail_rate = (
            fail_count
            / total_count
        ) * 100

        error_rate = (
            error_count
            / total_count
        ) * 100

    else:

        pass_rate = 0.0
        fail_rate = 0.0
        error_rate = 0.0

    print(
        f"PASS RATE:  "
        f"{pass_rate:.1f}%"
    )

    print(
        f"FAIL RATE:  "
        f"{fail_rate:.1f}%"
    )

    print(
        f"ERROR RATE: "
        f"{error_rate:.1f}%"
    )

    print(
        "=" * 70
    )

    return final_results


if __name__ == "__main__":
    run_tests()