"""QA Safe - first MVP demo."""

from red_agent.red_agent import RedAgent
from target_ai.target_bot import TargetAI
from evaluator.evaluator import Evaluator

def run_tests():
    print("=" * 60)
    print("QA SAFE - AI SECURITY TESTING MVP")
    print("=" * 60)

    red_agent = RedAgent()
    target_ai = TargetAI()
    evaluator = Evaluator()

    attacks = red_agent.get_all_attacks()
    report_data = []

    # SUNUM İÇİN DETAYLI VE İKONLU ÇIKTI
    for index, attack in enumerate(attacks, start=1):
        print(f"\n{'=' * 60}")
        print(f"ATTACK {index}/{len(attacks)}")
        print("=" * 60)

        print("\n[🔴 RED AGENT PROMPT]")
        print(attack)

        response = target_ai.generate_response(attack)
        
        print("\n[🟢 TARGET AI RESPONSE]")
        print(response)

        evaluation = evaluator.evaluate(attack, response)
        score = evaluation.get('score', 0)
        reasoning = evaluation.get('reasoning', 'No reasoning provided')
        
        print("\n[⚖️ EVALUATOR VERDICT]")
        print(f"Score: {score}")
        print(f"Reasoning: {reasoning}")

        # Final raporu için verileri biriktir
        report_data.append({
            "attack_id": index,
            "score": score,
            "reasoning": reasoning
        })

    # YÖNETİCİLER İÇİN FİNAL RAPORU
    print("\n\n" + "=" * 60)
    print("🏆 AI-QA SHIELD FINAL SECURITY REPORT 🏆")
    print("=" * 60)
    
    total_score = 0
    for data in report_data:
        try:
            total_score += int(data['score'])
        except (ValueError, TypeError):
            pass

    average_score = total_score / len(attacks) if attacks else 0
    
    print(f"🎯 OVERALL SYSTEM SECURITY SCORE: {average_score:.2f} / 100")
    print("=" * 60)
    print("=== TEST COMPLETED ===")

if __name__ == "__main__":
    run_tests()