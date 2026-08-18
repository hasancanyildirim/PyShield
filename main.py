"""QA Safe - first MVP demo."""

from red_agent.red_agent import RedAgent
from target_ai.target_bot import TargetAI


def run_tests():
    print("=" * 60)
    print("QA SAFE - AI SECURITY TESTING MVP")
    print("=" * 60)

    red_agent = RedAgent()
    target_ai = TargetAI()

    attacks = red_agent.get_all_attacks()

    for index, attack in enumerate(attacks, start=1):
        print(f"\n{'=' * 60}")
        print(f"ATTACK {index}")
        print("=" * 60)

        print("\n[RED AGENT PROMPT]")
        print(attack)

        response = target_ai.generate_response(attack)

        print("\n[TARGET AI RESPONSE]")
        print(response)

    print("\n=== TEST COMPLETED ===")


if __name__ == "__main__":
    run_tests()
