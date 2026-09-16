"""Read-only assessment model and standalone exports for live or stored campaigns.

Risk decisions stay in report_generator; renderers only present those decisions.
The allowlisted model deliberately excludes target headers, raw API responses,
and connection configuration. Test evidence is included verbatim.
"""

from collections import Counter
from copy import deepcopy
from html import escape
import re

from reports.report_generator import generate_security_report


SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN")


def build_assessment_report(campaign: dict) -> dict:
    """Build a deterministic, JSON-safe report without changing the input or DB.

Accepts run_and_store_campaign output or ResultStore.get_run output, including
older runs without security_report. Missing historical fields remain explicit.
"""
    if not isinstance(campaign, dict) or not campaign.get("campaign_id"):
        raise ValueError("A saved assessment with a campaign ID is required.")
    results = campaign.get("results")
    if not isinstance(results, list) or any(not isinstance(r, dict) for r in results):
        raise ValueError("Assessment results must be a list of test records.")

    summary = deepcopy(campaign.get("summary") or {})
    counts = Counter(str(r.get("result", "ERROR")).strip().upper() for r in results)
    defaults = {
        "total": campaign.get("total_tests", len(results)),
        "pass": campaign.get("passed_tests", counts["PASS"]),
        "fail": campaign.get("failed_tests", counts["FAIL"]),
        "error": campaign.get("error_tests", sum(v for k, v in counts.items() if k not in {"PASS", "FAIL"})),
        "safety_score": campaign.get("safety_score", 0.0),
    }
    for key, value in defaults.items():
        summary.setdefault(key, value)

    security = campaign.get("security_report") or generate_security_report({
        "campaign_id": campaign["campaign_id"],
        "campaign_name": campaign.get("campaign_name", "Security Assessment"),
        "summary": summary,
        "results": results,
    })
    evidence = []
    for result in results:
        if str(result.get("result", "")).strip().upper() != "FAIL":
            continue
        item = {
            "test_id": str(result.get("test_id") or "Not recorded"),
            "category": str(result.get("category") or "Unknown"),
            "attack_type": str(result.get("attack_type") or "Not recorded"),
            "difficulty": str(result.get("difficulty") or "Not recorded"),
            "severity": str(result.get("severity") or "UNKNOWN").strip().upper(),
            "attack_prompt": str(result.get("prompt") or result.get("attack_prompt") or "Not recorded"),
            "target_response": str(result.get("target_response") or "(Empty response)"),
            "expected_behavior": str(result.get("expected_behavior") or "Not recorded"),
            "reason": str(result.get("reason") or "Not recorded"),
            "evaluation_method": str(result.get("evaluation_method") or "Not recorded"),
            "parent_test_id": result.get("parent_test_id"),
            "iteration": result.get("iteration"),
        }
        evidence.append(item)
    severity = Counter(item["severity"] if item["severity"] in SEVERITIES else "UNKNOWN" for item in evidence)
    # Explicit projections avoid exporting unknown future fields such as headers.
    vulnerable = [{"category": str(v.get("category", "Unknown")),
                   "failed_tests": v.get("failed_tests", 0)}
                  for v in security.get("most_vulnerable_categories", []) if isinstance(v, dict)]
    recommendations = [{"category": str(r.get("category", "General")),
                        "recommendation": str(r.get("recommendation", ""))}
                       for r in security.get("recommendations", []) if isinstance(r, dict)]
    notices = []
    if summary["error"]:
        notices.append("Some tests could not be evaluated. Review execution errors before drawing security conclusions.")
    if not summary["total"]:
        notices.append("No tests were recorded. This assessment does not establish the target's security.")
    if summary["total"] != len(results):
        notices.append("Stored totals differ from the available test records; evidence may be incomplete.")

    basis = security.get("risk_basis") or {}
    return {
        "report_version": "1.0",
        "title": "PyShield Security Assessment Report",
        "campaign": {
            "id": str(campaign["campaign_id"]),
            "name": str(campaign.get("campaign_name") or "Security Assessment"),
            "date": str(campaign.get("date") or campaign.get("started_at") or campaign.get("created_at") or "Not recorded"),
            "status": str(campaign.get("status") or "Not recorded"),
        },
        "safety_score": security.get("safety_score", summary["safety_score"]),
        "risk_level": str(security.get("risk_level", "UNKNOWN")),
        "risk_basis": {
            "score_based_risk": basis.get("score_based_risk", "Not recorded"),
            "severity_floor_applied": basis.get("severity_floor_applied", False),
        },
        "counts": {"total": summary["total"], "pass": summary["pass"], "fail": summary["fail"], "error": summary["error"]},
        "severity_distribution": {s: severity[s] for s in SEVERITIES},
        "critical_findings": deepcopy([e for e in evidence if e["severity"] == "CRITICAL"]),
        "most_vulnerable_categories": vulnerable,
        "recommendations": recommendations,
        "failed_test_evidence": evidence,
        "notices": notices,
    }


def report_filename(report: dict, extension: str) -> str:
    if extension not in {"html", "md", "json"}:
        raise ValueError("Unsupported report file extension.")
    identifier = re.sub(r"[^A-Za-z0-9_-]+", "_", report["campaign"]["id"]).strip("_")[:100] or "assessment"
    return f"pyshield_{identifier}.{extension}"


def _md(value) -> str:
    # Escape raw HTML and Markdown delimiters in user/target-controlled text.
    text = escape(str(value), quote=False).replace("\r", " ").replace("\n", " ")
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", text)


def _code(value) -> str:
    text = str(value)
    longest = max((len(m.group()) for m in re.finditer(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}text\n{text}\n{fence}"


def render_markdown(report: dict) -> str:
    """Render a portable report; model creation and rendering need no services."""
    campaign, counts = report["campaign"], report["counts"]
    lines = ["# PyShield Security Assessment Report", "", f"## {_md(campaign['name'])}", "",
             f"Date: {_md(campaign['date'])}  ", f"Status: {_md(campaign['status'])}  ",
             f"Assessment reference: {_md(campaign['id'])}", "", "## Assessment summary", "",
             "| Metric | Value |", "| --- | --- |",
             f"| Safety Score | {_md(report['safety_score'])} / 100 |",
             f"| Risk Level | {_md(report['risk_level'])} |"]
    lines.extend(f"| {label} | {_md(counts[key])} |" for key, label in [("total", "Total tests"), ("pass", "PASS"), ("fail", "FAIL"), ("error", "ERROR")])
    lines.extend(["", f"Score-based risk: {_md(report['risk_basis']['score_based_risk'])}. "
                  f"Severity floor applied: {'Yes' if report['risk_basis']['severity_floor_applied'] else 'No'}.", ""])
    lines.extend(f"> {_md(n)}\n" for n in report["notices"])
    lines.extend(["## Failures by severity", "", "| Severity | Findings |", "| --- | --- |"])
    lines.extend(f"| {severity} | {_md(count)} |" for severity, count in report["severity_distribution"].items())
    lines.extend(["", "## Critical findings", ""])
    lines.extend([f"- {_md(e['category'])}: {_md(e['reason'])}" for e in report["critical_findings"]] or ["No critical findings recorded."])
    lines.extend(["", "## Most vulnerable categories", ""])
    lines.extend([f"- {_md(v['category'])}: {_md(v['failed_tests'])} failed tests." for v in report["most_vulnerable_categories"]] or ["No category with confirmed failures recorded."])
    lines.extend(["", "## Recommendations", ""])
    lines.extend([f"- **{_md(r['category'])}:** {_md(r['recommendation'])}" for r in report["recommendations"]] or ["No category-specific recommendations generated."])
    lines.extend(["", "## Failed test evidence", ""])
    for index, item in enumerate(report["failed_test_evidence"], 1):
        lines.extend([f"### Finding {index}: {_md(item['category'])}", ""])
        for key, label in [("test_id", "Test reference"), ("attack_type", "Attack type"), ("difficulty", "Difficulty"), ("severity", "Severity"), ("evaluation_method", "Evaluation method")]:
            lines.append(f"**{label}:** {_md(item[key])}  ")
        if item["iteration"] is not None:
            lines.append(f"**Adaptive iteration:** {_md(item['iteration'])} (parent: {_md(item['parent_test_id'])})")
        for key, label in [("expected_behavior", "Expected behavior"), ("attack_prompt", "Attack prompt"), ("target_response", "Target AI response"), ("reason", "Evaluator reason")]:
            lines.extend(["", f"**{label}**", "", _code(item[key])])
        lines.append("")
    if not report["failed_test_evidence"]:
        lines.append("No failed test evidence recorded.")
    lines.extend(["", "---", "Results describe the recorded assessment only. PASS is not a guarantee of security; rule-based and LLM evaluations can be incorrect.", ""])
    return "\n".join(lines)


def render_html(report: dict) -> str:
    """Standalone escaped HTML, with print CSS and no scripts or remote assets.

This renderer can later feed a PDF renderer without changing the report model.
"""
    def h(value):
        return escape(str(value), quote=True)

    campaign, counts = report["campaign"], report["counts"]
    cards = [("Safety Score", f"{report['safety_score']} / 100"), ("Risk Level", report["risk_level"]),
             ("Total tests", counts["total"]), ("PASS", counts["pass"]), ("FAIL", counts["fail"]), ("ERROR", counts["error"])]
    metrics = "".join(f'<div class="metric"><span>{h(k)}</span><strong>{h(v)}</strong></div>' for k, v in cards)
    notices = "".join(f'<p class="notice">{h(n)}</p>' for n in report["notices"])
    severity_rows = "".join(f"<tr><th scope='row'>{h(s)}</th><td>{h(n)}</td></tr>" for s, n in report["severity_distribution"].items())
    critical = "".join(f"<li><strong>{h(e['category'])}</strong>: {h(e['reason'])}</li>" for e in report["critical_findings"])
    vulnerable = "".join(f"<li>{h(v['category'])}: {h(v['failed_tests'])} failed tests</li>" for v in report["most_vulnerable_categories"])
    recommendations = "".join(f"<li><strong>{h(r['category'])}</strong>: {h(r['recommendation'])}</li>" for r in report["recommendations"])
    evidence = []
    for index, item in enumerate(report["failed_test_evidence"], 1):
        details = "".join(f"<dt>{label}</dt><dd>{h(item[key])}</dd>" for key, label in [("test_id", "Test reference"), ("attack_type", "Attack type"), ("difficulty", "Difficulty"), ("severity", "Severity"), ("evaluation_method", "Evaluation method")])
        if item["iteration"] is not None:
            details += f"<dt>Adaptive iteration</dt><dd>{h(item['iteration'])}; parent: {h(item['parent_test_id'])}</dd>"
        fields = "".join(f"<h4>{label}</h4><pre>{h(item[key])}</pre>" for key, label in [("expected_behavior", "Expected behavior"), ("attack_prompt", "Attack prompt"), ("target_response", "Target AI response"), ("reason", "Evaluator reason")])
        evidence.append(f'<article><h3>Finding {index}: {h(item["category"])}</h3><dl>{details}</dl>{fields}</article>')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>PyShield Security Assessment Report</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#eef2f6;color:#172a3a;font:15px/1.6 system-ui,sans-serif}}
main{{max-width:1080px;margin:32px auto;padding:40px;background:white;border-top:6px solid #176b75}}
h1{{font-size:30px;line-height:1.2;margin:8px 0 16px}}h2{{font-size:21px;margin-top:30px}}h3{{font-size:18px}}
p,li,dd,h1,h2,h3{{overflow-wrap:anywhere}}.brand{{color:#176b75;font-weight:700;letter-spacing:.12em}}
.muted,footer{{color:#526577}}.metrics{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}
.metric{{padding:16px;border:1px solid #d9e2eb;border-radius:8px}}.metric span{{display:block;color:#526577}}
.metric strong{{display:block;font-size:24px;overflow-wrap:anywhere}}.notice{{padding:12px;background:#fff3d8;border-left:4px solid #b77510}}
table{{border-collapse:collapse;width:100%}}th,td{{border-bottom:1px solid #d9e2eb;text-align:left;padding:8px 12px}}
article{{border-top:2px solid #d9e2eb;padding-top:12px;margin-top:26px}}dl{{display:grid;grid-template-columns:150px minmax(0,1fr);gap:4px 16px}}dt{{font-weight:600}}dd{{margin:0}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;background:#f3f6f9;border:1px solid #d9e2eb;padding:14px;font:13px/1.6 monospace}}
footer{{border-top:1px solid #d9e2eb;margin-top:32px;padding-top:16px;font-size:12px}}
@media(max-width:640px){{main{{margin:0;padding:20px}}.metrics{{grid-template-columns:repeat(2,minmax(0,1fr))}}dl{{grid-template-columns:1fr}}}}
@page{{size:A4;margin:16mm}}@media print{{body{{background:white}}main{{margin:0;padding:0;max-width:none;border:0}}h2,h3,h4{{break-after:avoid}}.metric,tr{{break-inside:avoid}}pre{{box-decoration-break:clone}}}}
</style></head><body><main>
<header><div class="brand">PYSHIELD</div><h1>Security Assessment Report</h1><h2>{h(campaign['name'])}</h2>
<p class="muted">Date: {h(campaign['date'])}<br>Status: {h(campaign['status'])}<br>Assessment reference: {h(campaign['id'])}</p></header>
<section><h2>Assessment summary</h2><div class="metrics">{metrics}</div>{notices}
<p>Score-based risk: {h(report['risk_basis']['score_based_risk'])}. Severity floor applied: {'Yes' if report['risk_basis']['severity_floor_applied'] else 'No'}.</p></section>
<section><h2>Failures by severity</h2><table><thead><tr><th>Severity</th><th>Findings</th></tr></thead><tbody>{severity_rows}</tbody></table></section>
<section><h2>Critical findings</h2>{'<ul>' + critical + '</ul>' if critical else '<p>No critical findings recorded.</p>'}</section>
<section><h2>Most vulnerable categories</h2>{'<ul>' + vulnerable + '</ul>' if vulnerable else '<p>No category with confirmed failures recorded.</p>'}</section>
<section><h2>Recommendations</h2>{'<ul>' + recommendations + '</ul>' if recommendations else '<p>No category-specific recommendations generated.</p>'}</section>
<section><h2>Failed test evidence</h2>{''.join(evidence) or '<p>No failed test evidence recorded.</p>'}</section>
<footer>Results describe the recorded assessment only. PASS is not a guarantee of security; rule-based and LLM evaluations can be incorrect.</footer>
</main></body></html>'''
