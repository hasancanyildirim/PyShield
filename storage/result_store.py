"""
AI-QA Shield - Persistent Result Storage Module.

Provides SQLite-backed persistence for security test campaigns and individual test execution
results using Python's built-in sqlite3 module.
"""

from contextlib import contextmanager
import json
import os
import sqlite3
from typing import Any, Dict, Generator, List, Optional


class ResultStore:
    """
    SQLite-backed storage manager for campaign execution runs and individual test results.
    """

    def __init__(self, db_path: str = "qa_safe_results.db") -> None:
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        parent_dir = os.path.dirname(self.db_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS campaign_runs (
                    campaign_id TEXT PRIMARY KEY,
                    campaign_name TEXT,
                    status TEXT,
                    total_tests INTEGER,
                    passed_tests INTEGER,
                    failed_tests INTEGER,
                    error_tests INTEGER,
                    pass_rate REAL,
                    safety_score REAL,
                    critical_failures INTEGER,
                    high_failures INTEGER,
                    medium_failures INTEGER,
                    low_failures INTEGER,
                    summary_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_id TEXT NOT NULL,
                    test_id TEXT NOT NULL,
                    category TEXT,
                    attack_type TEXT,
                    difficulty TEXT,
                    severity TEXT,
                    attack_prompt TEXT,
                    target_response TEXT,
                    result TEXT,
                    reason TEXT,
                    evaluation_method TEXT,
                    confidence TEXT,
                    source TEXT,
                    retrieved_context_json TEXT,
                    visibility_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (campaign_id) REFERENCES campaign_runs (campaign_id) ON DELETE CASCADE
                );
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_test_results_campaign_id ON test_results(campaign_id);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_test_results_result ON test_results(result);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_test_results_category ON test_results(category);"
            )

    def save_run(self, campaign_output: Dict[str, Any]) -> str:
        if not isinstance(campaign_output, dict):
            raise ValueError("campaign_output must be a dictionary.")

        campaign_id = campaign_output.get("campaign_id")
        if not campaign_id or not isinstance(campaign_id, str):
            raise ValueError("campaign_output must contain a valid non-empty 'campaign_id'.")

        campaign_name = campaign_output.get("campaign_name", "Security Test Campaign")
        status = campaign_output.get("status", "COMPLETED")
        summary = campaign_output.get("summary", {})
        results = campaign_output.get("results", [])

        total_tests = summary.get("total", len(results)) if isinstance(summary, dict) else len(results)
        passed_tests = summary.get("pass", 0) if isinstance(summary, dict) else 0
        failed_tests = summary.get("fail", 0) if isinstance(summary, dict) else 0
        error_tests = summary.get("error", 0) if isinstance(summary, dict) else 0
        pass_rate = summary.get("pass_rate", 0.0) if isinstance(summary, dict) else 0.0
        safety_score = summary.get("safety_score", 0.0) if isinstance(summary, dict) else 0.0
        critical_failures = summary.get("critical_failures", 0) if isinstance(summary, dict) else 0
        high_failures = summary.get("high_failures", 0) if isinstance(summary, dict) else 0
        medium_failures = summary.get("medium_failures", 0) if isinstance(summary, dict) else 0
        low_failures = summary.get("low_failures", 0) if isinstance(summary, dict) else 0
        summary_json = json.dumps(summary) if summary is not None else None

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO campaign_runs (
                    campaign_id, campaign_name, status, total_tests, passed_tests,
                    failed_tests, error_tests, pass_rate, safety_score,
                    critical_failures, high_failures, medium_failures,
                    low_failures, summary_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    campaign_id, campaign_name, status, total_tests, passed_tests,
                    failed_tests, error_tests, pass_rate, safety_score,
                    critical_failures, high_failures, medium_failures,
                    low_failures, summary_json,
                ),
            )

            for test in results:
                if not isinstance(test, dict):
                    continue

                attack_prompt = test.get("prompt") if "prompt" in test else test.get("attack_prompt")
                confidence = (
                    test.get("classification_confidence")
                    if "classification_confidence" in test
                    else test.get("confidence")
                )
                retrieved_context = test.get("retrieved_context")
                visibility = test.get("visibility")

                cursor.execute(
                    """
                    INSERT INTO test_results (
                        campaign_id, test_id, category, attack_type, difficulty,
                        severity, attack_prompt, target_response, result, reason,
                        evaluation_method, confidence, source,
                        retrieved_context_json, visibility_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        campaign_id,
                        test.get("test_id", "UNKNOWN"),
                        test.get("category"),
                        test.get("attack_type"),
                        test.get("difficulty"),
                        test.get("severity"),
                        attack_prompt,
                        test.get("target_response"),
                        test.get("result"),
                        test.get("reason"),
                        test.get("evaluation_method"),
                        confidence,
                        test.get("source"),
                        json.dumps(retrieved_context) if retrieved_context is not None else None,
                        json.dumps(visibility) if visibility is not None else None,
                    ),
                )

        return campaign_id

    def get_run(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        if not campaign_id or not isinstance(campaign_id, str):
            return None

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM campaign_runs WHERE campaign_id = ?;",
                (campaign_id,),
            )
            campaign_row = cursor.fetchone()
            if campaign_row is None:
                return None

            campaign_dict = dict(campaign_row)
            summary_raw = campaign_dict.get("summary_json")
            if summary_raw:
                try:
                    campaign_dict["summary"] = json.loads(summary_raw)
                except (json.JSONDecodeError, TypeError):
                    campaign_dict["summary"] = {}
            else:
                campaign_dict["summary"] = {}

            cursor.execute(
                "SELECT * FROM test_results WHERE campaign_id = ? ORDER BY id ASC;",
                (campaign_id,),
            )
            test_rows = cursor.fetchall()
            results = []

            for row in test_rows:
                test_dict = dict(row)
                retrieved_context_raw = test_dict.pop("retrieved_context_json", None)
                if retrieved_context_raw:
                    try:
                        test_dict["retrieved_context"] = json.loads(retrieved_context_raw)
                    except (json.JSONDecodeError, TypeError):
                        test_dict["retrieved_context"] = []
                else:
                    test_dict["retrieved_context"] = []

                visibility_raw = test_dict.pop("visibility_json", None)
                if visibility_raw:
                    try:
                        test_dict["visibility"] = json.loads(visibility_raw)
                    except (json.JSONDecodeError, TypeError):
                        test_dict["visibility"] = []
                else:
                    test_dict["visibility"] = []

                if "attack_prompt" in test_dict and "prompt" not in test_dict:
                    test_dict["prompt"] = test_dict["attack_prompt"]
                if "confidence" in test_dict and "classification_confidence" not in test_dict:
                    test_dict["classification_confidence"] = test_dict["confidence"]
                results.append(test_dict)

            campaign_dict["results"] = results
            return campaign_dict

    def get_failed_tests(self, campaign_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            cursor = conn.cursor()
            if campaign_id is not None:
                cursor.execute(
                    """
                    SELECT * FROM test_results
                    WHERE result = 'FAIL' AND campaign_id = ?
                    ORDER BY id ASC;
                    """,
                    (campaign_id,),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM test_results
                    WHERE result = 'FAIL'
                    ORDER BY id ASC;
                    """
                )

            failed_tests = []
            for row in cursor.fetchall():
                test_dict = dict(row)
                retrieved_context_raw = test_dict.pop("retrieved_context_json", None)
                if retrieved_context_raw:
                    try:
                        test_dict["retrieved_context"] = json.loads(retrieved_context_raw)
                    except (json.JSONDecodeError, TypeError):
                        test_dict["retrieved_context"] = []
                else:
                    test_dict["retrieved_context"] = []

                visibility_raw = test_dict.pop("visibility_json", None)
                if visibility_raw:
                    try:
                        test_dict["visibility"] = json.loads(visibility_raw)
                    except (json.JSONDecodeError, TypeError):
                        test_dict["visibility"] = []
                else:
                    test_dict["visibility"] = []

                if "attack_prompt" in test_dict and "prompt" not in test_dict:
                    test_dict["prompt"] = test_dict["attack_prompt"]
                if "confidence" in test_dict and "classification_confidence" not in test_dict:
                    test_dict["classification_confidence"] = test_dict["confidence"]
                failed_tests.append(test_dict)

            return failed_tests

    def list_runs(self) -> List[Dict[str, Any]]:
        """Return campaign history ordered newest-first for dashboard consumption."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM campaign_runs ORDER BY created_at DESC;")
            runs = []
            for row in cursor.fetchall():
                campaign_dict = dict(row)
                summary_raw = campaign_dict.get("summary_json")
                if summary_raw:
                    try:
                        campaign_dict["summary"] = json.loads(summary_raw)
                    except (json.JSONDecodeError, TypeError):
                        campaign_dict["summary"] = {}
                else:
                    campaign_dict["summary"] = {}
                runs.append(campaign_dict)
            return runs
