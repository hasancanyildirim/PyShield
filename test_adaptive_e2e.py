from unittest.mock import MagicMock, patch

import main


def make_result(test_id, verdict, reason):
    return {
        "test_id": test_id,
        "category": "Prompt Injection",
        "attack_type": "Role Manipulation / Jailbreak",
        "difficulty": "HARD",
        "severity": "HIGH",
        "source": "TEST_SUITE",
        "classification_confidence": "HIGH",
        "result": verdict,
        "reason": reason,
        "evaluation_method": "CONTROLLED",
    }


def test_adaptive_feedback_loop():
    print("=" * 65)
    print("TASK 2 - ADAPTIVE RED TEAMING E2E VALIDATION")
    print("=" * 65)

    # Keep the test isolated to one category / one initial attack.
    original_configs = main.TEST_CONFIGS
    original_tests_per_category = main.TESTS_PER_CATEGORY

    main.TEST_CONFIGS = [
        {
            "category": "Prompt Injection",
            "attack_type": "Role Manipulation / Jailbreak",
            "difficulty": "HARD",
        }
    ]
    main.TESTS_PER_CATEGORY = 1

    try:
        fake_red_agent = MagicMock()
        fake_target_ai = MagicMock()

        # Controlled execution:
        #
        # Initial attack -> FAIL
        # Adaptive #1   -> FAIL
        # Adaptive #2   -> PASS
        #
        # Therefore the loop MUST stop before iteration 3.
        initial_fail = make_result(
            "INITIAL-001",
            "FAIL",
            "Initial vulnerability detected.",
        )

        adaptive_fail = make_result(
            "INITIAL-001-ITER1",
            "FAIL",
            "Alternative payload also succeeded.",
        )
        adaptive_fail.update(
            {
                "parent_test_id": "INITIAL-001",
                "iteration": 1,
                "strategy": "Vulnerability detected. Testing alternative payload at same difficulty",
                "previous_result": "FAIL",
                "previous_reason": "Initial vulnerability detected.",
            }
        )

        adaptive_pass = make_result(
            "INITIAL-001-ITER1-ITER2",
            "PASS",
            "Target resisted the second adaptive attack.",
        )
        adaptive_pass.update(
            {
                "parent_test_id": "INITIAL-001-ITER1",
                "iteration": 2,
                "strategy": "Vulnerability detected. Testing alternative payload at same difficulty",
                "previous_result": "FAIL",
                "previous_reason": "Alternative payload also succeeded.",
            }
        )

        fake_red_agent.generate_adaptive_attack.side_effect = [
            {
                "test_id": "INITIAL-001-ITER1",
                "category": "Prompt Injection",
                "attack_type": "Role Manipulation / Jailbreak",
                "difficulty": "HARD",
                "severity": "HIGH",
                "prompt": "Adaptive payload 1",
                "parent_test_id": "INITIAL-001",
                "iteration": 1,
                "strategy": "Alternative payload",
                "previous_result": "FAIL",
                "previous_reason": "Initial vulnerability detected.",
            },
            {
                "test_id": "INITIAL-001-ITER1-ITER2",
                "category": "Prompt Injection",
                "attack_type": "Role Manipulation / Jailbreak",
                "difficulty": "HARD",
                "severity": "HIGH",
                "prompt": "Adaptive payload 2",
                "parent_test_id": "INITIAL-001-ITER1",
                "iteration": 2,
                "strategy": "Alternative payload",
                "previous_result": "FAIL",
                "previous_reason": "Alternative payload also succeeded.",
            },
        ]

        with (
            patch.object(
                main,
                "DynamicRedAgent",
                return_value=fake_red_agent,
            ),
            patch.object(
                main,
                "TargetAI",
                return_value=fake_target_ai,
            ),
            patch.object(
                main,
                "run_single_test",
                side_effect=[
                    initial_fail,
                    adaptive_fail,
                    adaptive_pass,
                ],
            ) as mocked_run,
        ):
            results = main.run_tests()

        # =====================================================
        # ASSERTIONS
        # =====================================================

        assert len(results) == 3

        assert results[0]["result"] == "FAIL"
        assert results[1]["result"] == "FAIL"
        assert results[2]["result"] == "PASS"

        print("\nControlled FAIL -> FAIL -> PASS: PASS")

        # Initial + 2 adaptive executions.
        assert mocked_run.call_count == 3

        print("Adaptive attacks executed: PASS")

        # Adaptive generator must run exactly twice.
        assert (
            fake_red_agent.generate_adaptive_attack.call_count
            == 2
        )

        print("Feedback loop count: PASS")

        first_call = (
            fake_red_agent
            .generate_adaptive_attack
            .call_args_list[0]
            .kwargs
        )

        second_call = (
            fake_red_agent
            .generate_adaptive_attack
            .call_args_list[1]
            .kwargs
        )

        assert first_call["iteration"] == 1
        assert second_call["iteration"] == 2

        print("Iteration progression 1 -> 2: PASS")

        assert (
            first_call["parent_test"]["test_id"]
            == "INITIAL-001"
        )

        assert (
            second_call["parent_test"]["test_id"]
            == "INITIAL-001-ITER1"
        )

        print("Parent test chaining: PASS")

        assert (
            second_call["previous_result"]
            == "FAIL"
        )

        assert (
            second_call["previous_reason"]
            == "Alternative payload also succeeded."
        )

        print("Evaluator feedback propagation: PASS")

        # PASS must stop the loop.
        assert (
            fake_red_agent.generate_adaptive_attack.call_count
            == 2
        )

        print("PASS termination: PASS")

        print("\n" + "=" * 65)
        print("ALL ADAPTIVE E2E TESTS PASSED")
        print("=" * 65)

    finally:
        main.TEST_CONFIGS = original_configs
        main.TESTS_PER_CATEGORY = original_tests_per_category


def test_max_iteration_limit():
    print("\n" + "=" * 65)
    print("TASK 2 - MAX ADAPTIVE ITERATION VALIDATION")
    print("=" * 65)

    original_configs = main.TEST_CONFIGS
    original_tests_per_category = main.TESTS_PER_CATEGORY

    main.TEST_CONFIGS = [
        {
            "category": "Prompt Injection",
            "attack_type": "Role Manipulation / Jailbreak",
            "difficulty": "HARD",
        }
    ]
    main.TESTS_PER_CATEGORY = 1

    try:
        fake_red_agent = MagicMock()
        fake_target_ai = MagicMock()

        initial_fail = make_result(
            "MAX-001",
            "FAIL",
            "Initial failure.",
        )

        adaptive_results = []

        for iteration in range(1, 4):
            result = make_result(
                f"MAX-001-ITER{iteration}",
                "FAIL",
                f"Adaptive failure {iteration}.",
            )

            result.update(
                {
                    "parent_test_id": (
                        "MAX-001"
                        if iteration == 1
                        else f"MAX-001-ITER{iteration - 1}"
                    ),
                    "iteration": iteration,
                    "strategy": "Controlled adaptive retry",
                    "previous_result": "FAIL",
                }
            )

            adaptive_results.append(result)

        fake_red_agent.generate_adaptive_attack.side_effect = [
            {
                "test_id": f"MAX-001-ITER{i}",
                "category": "Prompt Injection",
                "attack_type": "Role Manipulation / Jailbreak",
                "difficulty": "HARD",
                "severity": "HIGH",
                "prompt": f"Adaptive payload {i}",
                "iteration": i,
                "strategy": "Controlled adaptive retry",
                "previous_result": "FAIL",
            }
            for i in range(1, 4)
        ]

        with (
            patch.object(
                main,
                "DynamicRedAgent",
                return_value=fake_red_agent,
            ),
            patch.object(
                main,
                "TargetAI",
                return_value=fake_target_ai,
            ),
            patch.object(
                main,
                "run_single_test",
                side_effect=[
                    initial_fail,
                    *adaptive_results,
                ],
            ) as mocked_run,
        ):
            results = main.run_tests()

        # 1 initial + exactly 3 adaptive executions.
        assert len(results) == 4
        assert mocked_run.call_count == 4

        assert (
            fake_red_agent.generate_adaptive_attack.call_count
            == 3
        )

        iterations = [
            call.kwargs["iteration"]
            for call in (
                fake_red_agent
                .generate_adaptive_attack
                .call_args_list
            )
        ]

        assert iterations == [1, 2, 3]

        assert all(
            result["result"] == "FAIL"
            for result in results
        )

        print("Initial attack: FAIL")
        print("Adaptive iteration 1: FAIL")
        print("Adaptive iteration 2: FAIL")
        print("Adaptive iteration 3: FAIL")
        print("Iteration sequence [1, 2, 3]: PASS")
        print("No iteration 4 generated: PASS")
        print("Maximum adaptive limit respected: PASS")

        print("\n" + "=" * 65)
        print("MAX ITERATION TEST PASSED")
        print("=" * 65)

    finally:
        main.TEST_CONFIGS = original_configs
        main.TESTS_PER_CATEGORY = original_tests_per_category

if __name__ == "__main__":
    test_adaptive_feedback_loop()
    test_max_iteration_limit()