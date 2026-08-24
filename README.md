# QA Safe

AI security testing MVP for evaluating an LLM-based application end to end.

## Current flow

```text
Baseline Test Record
        ↓
Red Agent
        ↓
Target AI (NovaBot / Gemma 3:1b + RAG)
        ↓
Evaluator (Gemma 3:1b)
        ↓
PASS / FAIL / ERROR + reason
        ↓
Final Orchestrator Report
```

## Current MVP test categories

- Prompt Injection
- Sensitive Information Leakage
- RAG Security
- Hallucination

Each baseline test uses a shared record containing fields such as:

- `test_id`
- `category`
- `attack_type`
- `severity`
- `prompt`
- `expected_behavior`

During execution, the Target AI adds structured output including:

- `target_response`
- `retrieved_context`
- `visibility`

The Evaluator then adds:

- `result`
- `reason`

## Target AI

The current Target AI is NovaBot, a local RAG-based assistant using:

- Ollama
- Gemma 3:1b
- ChromaDB
- NovaCloud Markdown documentation

The vector store contains both PUBLIC and INTERNAL test documents, but customer-facing retrieval is filtered to PUBLIC chunks.

## Evaluator

The Evaluator uses the local Gemma 3:1b model through the Ollama HTTP API. It compares each Target AI response against the expected behavior and returns a structured PASS, FAIL, or ERROR result with a short reason.

## Project structure

```text
QA-Safe/
├── evaluator/
├── knowledge_base/
├── red_agent/
├── target_ai/
├── tests/
├── main.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Requirements

Python 3.12 is recommended.

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Local Ollama models used by the current MVP:

```text
gemma3:1b
nomic-embed-text
```

## Run the full Test Foundation pipeline

From the repository root:

```bash
python main.py
```

## Run the Red Agent -> Target AI diagnostic test

From the repository root:

```bash
python -m tests.test_red_target
```

## Security notes

- Never commit real API keys, access tokens, passwords, or `.env` files.
- `.env` and local ChromaDB data are excluded by `.gitignore`.
- The INTERNAL documents currently stored in `knowledge_base/` are synthetic test data for the MVP. Real internal or production documents should be kept outside the source repository and protected by appropriate access controls.

## Next stages

The current focus is a stable Test Foundation. Planned later milestones include dynamic Red Agent test generation, richer Evaluator output, logging/observability, failure diagnosis, feedback loops, and future cloud/service integrations.
