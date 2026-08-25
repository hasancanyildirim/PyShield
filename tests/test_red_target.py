from red_agent.red_agent import baseline_tests
from target_ai.target_bot import TargetAI


def run_red_target_test():
    target_ai = TargetAI()

    print("\n=== QA SAFE - RED AGENT -> TARGET AI TEST ===\n")

    for index, test_record in enumerate(baseline_tests, start=1):
        print(f"\n{'=' * 60}")
        print(f"TEST {index} - {test_record['test_id']}")
        print(f"{'=' * 60}")

        print("\n[CATEGORY]")
        print(test_record["category"])

        print("\n[SEVERITY]")
        print(test_record["severity"])

        print("\n[RED AGENT PROMPT]")
        print(test_record["prompt"])

        target_data = target_ai.generate_response(
            test_record["prompt"],
            test_mode=True
        )

        print("\n[TARGET AI RESPONSE]")
        print(target_data.get("target_response", ""))

        retrieved_context = target_data.get("retrieved_context", [])
        visibility = target_data.get("visibility", [])

        print("\n[RETRIEVAL INFO]")
        print(f"Retrieved Chunks: {len(retrieved_context)}")
        print(f"Visibility: {visibility}")

    print("\n=== TEST COMPLETED ===")


if __name__ == "__main__":
    run_red_target_test()
