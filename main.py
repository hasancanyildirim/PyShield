from red_agent.red_agent import baseline_tests
from target_ai.target_bot import TargetAI
from evaluator.evaluator import evaluate_target_response


def run_tests():
    print("=" * 70)
    print("QA SAFE - TEST FOUNDATION MVP")
    print("=" * 70)

    target_ai = TargetAI()

    final_results = []

    for test_record in baseline_tests:
        print("\n" + "=" * 70)
        print(
            f"[{test_record['test_id']}] "
            f"{test_record['category']} "
            f"- {test_record['attack_type']}"
        )
        print("=" * 70)

        print(f"Severity: {test_record['severity']}")

        print("\n[EXPECTED BEHAVIOR]")
        print(test_record["expected_behavior"])

        print("\n[RED AGENT PROMPT]")
        print(test_record["prompt"])

        # -------------------------------------------------
        # TARGET AI
        # -------------------------------------------------

        target_data = target_ai.generate_response(
            test_record["prompt"],
            test_mode=True
        )

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

        print("\n[TARGET AI RESPONSE]")
        print(target_response)

        print("\n[RETRIEVAL INFO]")
        print(f"Retrieved Chunks: {len(retrieved_context)}")
        print(f"Visibility: {visibility}")

        # -------------------------------------------------
        # EVALUATOR
        # -------------------------------------------------

        evaluation_result = evaluate_target_response(
            test_record=test_record,
            target_response=target_response,
            retrieved_context=retrieved_context,
            visibility=visibility
        )

        print("\n[EVALUATOR RESULT]")
        print(
            f"Result: "
            f"{evaluation_result.get('result', 'ERROR')}"
        )
        print(
            f"Reason: "
            f"{evaluation_result.get('reason', 'No reason')}"
        )

        final_results.append(evaluation_result)

    # -----------------------------------------------------
    # FINAL REPORT
    # -----------------------------------------------------

    print("\n\n" + "=" * 70)
    print("AI-QA SHIELD - FINAL TEST FOUNDATION REPORT")
    print("=" * 70)

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

    for result in final_results:
        print(
            f"{result.get('test_id')} | "
            f"{result.get('category')} | "
            f"{result.get('severity')} | "
            f"{result.get('result')}"
        )

    print("-" * 70)

    print(f"PASS:  {pass_count}")
    print(f"FAIL:  {fail_count}")
    print(f"ERROR: {error_count}")

    print(
        f"TOTAL: {len(final_results)}"
    )

    print("=" * 70)


if __name__ == "__main__":
    run_tests()