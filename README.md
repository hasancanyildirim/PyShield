# QA Safe

Simple AI security testing MVP for the first project presentation.

## Current flow

Manual Test Prompts → Red Agent → Target AI → Evaluator → PASS/FAIL

## Structure

```text
QA-Safe/
├── target_ai/
├── red_agent/
├── evaluator/
├── tests/
├── main.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Run

Python 3.12 is recommended.

```bash
python main.py
```

The current MVP intentionally has no Huawei Cloud, RAG, database, mobile app, or external LLM dependency yet.
