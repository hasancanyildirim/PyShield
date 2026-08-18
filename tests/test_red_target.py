from red_agent.red_agent import RedAgent
from target_ai.target_bot import TargetAI


red_agent = RedAgent()
target_ai = TargetAI()

attacks = red_agent.get_all_attacks()

print("\n=== QA SAFE - RED AGENT -> TARGET AI TEST ===\n")

for index, attack in enumerate(attacks, start=1):

    print(f"\n{'=' * 60}")
    print(f"ATTACK {index}")
    print(f"{'=' * 60}")

    print("\n[RED AGENT PROMPT]")
    print(attack)

    print("\n[TARGET AI RESPONSE]")

    response = target_ai.generate_response(attack)

    print(response)

print("\n=== TEST COMPLETED ===")