"""Compatibility alias for the shared Test Foundation baseline records.

The canonical baseline test definitions live in red_agent/red_agent.py.
This module remains only for older imports that expect TEST_CASES.
"""

from red_agent.red_agent import baseline_tests


TEST_CASES = baseline_tests
