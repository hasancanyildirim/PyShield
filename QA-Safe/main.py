"""QA Safe - first MVP demo."""

from target_ai.target_bot import get_response
from red_agent.red_agent import send_test
from evaluator.evaluator import evaluate
from tests.test_cases import TEST_CASES

def run_tests():
    print("=" * 60)
    print("QA SAFE - AI SECURITY TESTING MVP")
    print("=" * 60)

    results = []
    for test in TEST_CASES:
        print(f"\nTest #{test['id']} | {test['category']}")
        print(f"Prompt: {test['prompt']}")
        response = send_test(test["prompt"], get_response)
        result = evaluate(test["prompt"], response)
        print(f"Target AI: {response}")
        print(f"Result: {result['status']}")
        print(f"Reason: {result['reason']}")
        results.append(result)

    passed = sum(r["status"] == "PASS" for r in results)
    print(f"\nSUMMARY: {passed} PASS / {len(results)-passed} FAIL")

if __name__ == "__main__":
    run_tests()
