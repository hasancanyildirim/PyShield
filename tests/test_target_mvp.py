import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from target_ai.target_bot import ask_target_bot
from tests.test_registry import get_test_by_id

# Baseline test definitions retrieved from centralized test registry
RAG_BASELINE_TEST = get_test_by_id("RAG-001")
SIL_BASELINE_TEST = get_test_by_id("SIL-001")
HAL_BASELINE_TEST = get_test_by_id("HAL-001")


def test_public_query():
    print("=" * 60)
    print("TEST 1: PUBLIC Documentation Retrieval")
    print("=" * 60)
    query = "What is the default SSH port for NovaCloud VMs?"
    result = ask_target_bot(query, test_mode=True)

    print("1. target_response:")
    print(result.get("target_response"))
    print("\n2. retrieved_context:")
    print(result.get("retrieved_context"))
    print("\n3. visibility:")
    print(result.get("visibility"))


def test_rag_security_baseline():
    print("\n" + "=" * 60)
    print(f"TEST 2: [{RAG_BASELINE_TEST['test_id']}] {RAG_BASELINE_TEST['category']} - {RAG_BASELINE_TEST['attack_type']}")
    print(f"Severity: {RAG_BASELINE_TEST['severity']}")
    print(f"Expected Behavior: {RAG_BASELINE_TEST['expected_behavior']}")
    print(f"Prompt: {RAG_BASELINE_TEST['prompt']}")
    print("=" * 60)

    result = ask_target_bot(RAG_BASELINE_TEST["prompt"], test_mode=True)

    print("1. target_response:")
    print(result.get("target_response"))
    print("\n2. retrieved_context:")
    print(result.get("retrieved_context"))
    print("\n3. visibility:")
    print(result.get("visibility"))


def test_sensitive_info_leakage_baseline():
    print("\n" + "=" * 60)
    print(f"TEST 3: [{SIL_BASELINE_TEST['test_id']}] {SIL_BASELINE_TEST['category']} - {SIL_BASELINE_TEST['attack_type']}")
    print(f"Severity: {SIL_BASELINE_TEST['severity']}")
    print(f"Expected Behavior: {SIL_BASELINE_TEST['expected_behavior']}")
    print(f"Prompt: {SIL_BASELINE_TEST['prompt']}")
    print("=" * 60)

    result = ask_target_bot(SIL_BASELINE_TEST["prompt"], test_mode=True)

    print("1. target_response:")
    print(result.get("target_response"))
    print("\n2. retrieved_context:")
    print(result.get("retrieved_context"))
    print("\n3. visibility:")
    print(result.get("visibility"))


def test_hallucination_baseline():
    print("\n" + "=" * 60)
    print(f"TEST 4: [{HAL_BASELINE_TEST['test_id']}] {HAL_BASELINE_TEST['category']} - {HAL_BASELINE_TEST['attack_type']}")
    print(f"Severity: {HAL_BASELINE_TEST['severity']}")
    print(f"Expected Behavior: {HAL_BASELINE_TEST['expected_behavior']}")
    print(f"Prompt: {HAL_BASELINE_TEST['prompt']}")
    print("=" * 60)

    result = ask_target_bot(HAL_BASELINE_TEST["prompt"], test_mode=True)

    print("1. target_response:")
    print(result.get("target_response"))
    print("\n2. retrieved_context:")
    print(result.get("retrieved_context"))
    print("\n3. visibility:")
    print(result.get("visibility"))


if __name__ == "__main__":
    test_public_query()
    test_rag_security_baseline()
    test_sensitive_info_leakage_baseline()
    test_hallucination_baseline()
