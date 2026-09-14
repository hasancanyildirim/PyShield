# PyShield

AI quality and security assessment platform with campaign execution, bounded adaptive tests, hybrid evaluation, SQLite history, and shareable reports.

## Assessment flow

Streamlit configuration -> Campaign -> Red Agent -> Target Adapter -> Target AI -> Evaluator -> Adaptive follow-ups -> Result Store -> Dashboard and report export.

- Categories: Prompt Injection, Sensitive Information Leakage, RAG Security, Hallucination.
- The Red Agent selects curated tests by category and difficulty, with fallback prompts when the pool has no match.
- Failed base tests can trigger up to three follow-ups per chain. PASS or ERROR stops the chain.
- Evaluation uses deterministic checks, then local LLM evaluation when needed.
- Safety Score uses severity penalties. Overall risk also applies severity floors.
- The local development target is NovaBot: Gemma 3:1b through Ollama, with ChromaDB retrieval restricted to PUBLIC documents.
- `RESTTargetAdapter` supports external APIs programmatically. Web target configuration and scenario-profile selection are separate pending integrations.

## Setup

Python 3.12 is recommended.

```bash
pip install -r requirements.txt
ollama pull gemma3:1b
ollama pull nomic-embed-text
streamlit run dashboard/app.py
```

Ollama must be running for a live assessment. The original console diagnostic flow remains available with `python main.py`.

## Shareable assessment reports

Select a completed assessment from **Assessment History**, then open **Report**.

- **HTML**: standalone report with print styling and no external assets. Open in a browser and print or save as PDF.
- **Markdown**: portable text report.
- **JSON**: structured assessment-report model, including failed-test evidence.

Reports include campaign reference, date and status; Safety Score and risk; PASS/FAIL/ERROR totals; failed-test severity distribution; critical findings; vulnerable categories; recommendations; and each failure's attack type, prompt, response, severity and evaluator reason.

`reports.assessment_report.build_assessment_report()` accepts both live campaign output and `ResultStore.get_run()` data. It is read-only: exports never rerun a campaign, modify the input, or write to SQLite. Historical records without a stored security report use the existing risk-report generator. Fields absent from older records, such as expected behavior, are displayed as `Not recorded`.

The structured export deliberately excludes connection settings, authentication headers and raw adapter metadata. It includes attack prompts and target responses as evidence; review their contents before sharing outside your team. HTML escapes embedded markup and Markdown uses protected code fences for evidence.

```python
from reports.assessment_report import build_assessment_report, render_html
from storage.result_store import ResultStore

campaign = ResultStore("qa_safe_results.db").get_run("YOUR_CAMPAIGN_ID")
report = build_assessment_report(campaign)
html = render_html(report)
```

The model and renderers are separate so a dedicated PDF renderer can be added later. No server-side PDF dependency is required today.

## Main modules

| Module | Responsibility |
| --- | --- |
| `main.py` | Single-test execution and legacy CLI |
| `campaign/` | Base execution, adaptive integration, aggregation and persistence coordination |
| `red_agent/` | Curated attack selection and dataset preparation |
| `target_ai/` | Local RAG target and generic REST adapter |
| `evaluator/` | Hybrid PASS/FAIL/ERROR evaluation |
| `storage/` | SQLite campaign and test history |
| `reports/` | Risk decisions and read-only assessment exports |
| `dashboard/` | Assessment configuration, findings, evidence and downloads |

## Regression tests

```bash
pip install pytest
python -m pytest -q test_campaign.py test_campaign_integration.py test_result_store.py test_adaptive_e2e.py test_feedback_guided_adaptive.py test_security_report.py tests/test_adapters.py test_assessment_report.py
```

These checks cover campaign contracts, adaptive orchestration, SQLite persistence, risk reports, adapters, read-only exports, historical regeneration and Streamlit interactions. Most execution tests use controlled responses. The existing `test_campaign_output_contains_security_report` also attempts the development target and can complete with an ERROR result when Ollama is unavailable; passing this suite does not establish a successful live-model assessment.

`tests/test_target_mvp.py` contains live Ollama diagnostics and is not part of the automated regression command.

## Current limitations

- The curated library does not cover every category/difficulty combination.
- Adaptive feedback guidance currently uses category templates, not reason-conditioned LLM attack generation.
- Evaluator decisions can include false positives and false negatives.
- REST connection errors need further integration work to retain their ERROR metadata throughout the campaign.
- Existing stored runs omit some execution configuration and metadata.
- Task 1 (web target configuration) and Task 2 (expanded coverage/scenario profiles) must be integrated when their branches become available.

The `knowledge_base/` INTERNAL examples are synthetic development data. Never commit real credentials or production internal documents.
