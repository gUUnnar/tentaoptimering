from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .validation import QualityResult


def combined_payload(results: dict[str, QualityResult]) -> dict[str, Any]:
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "datasets": {name: result.to_dict() for name, result in results.items()},
    }


def write_quality_json(results: dict[str, QualityResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(combined_payload(results), ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _metric_rows(metrics: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    for key, value in metrics.items():
        rendered = json.dumps(value, ensure_ascii=False, default=str) if isinstance(value, dict) else value
        rows.append(f"| `{key}` | {rendered} |")
    return rows


def write_baseline_report(results: dict[str, QualityResult], path: Path) -> None:
    lines = [
        "# Baslinjerapport – Tentalokaler-PoC",
        "",
        "Rapporten beskriver datakällornas korn, täckning och blockerande kvalitetsrisker.",
        "Den beräknar inte någon optimering eller verifierad besparing.",
        "",
    ]
    for name, result in results.items():
        lines.extend(
            [
                f"## {name}",
                "",
                "| Mått | Värde |",
                "|---|---:|",
                *_metric_rows(result.metrics),
                "",
            ]
        )

    lines.extend(
        [
            "## Kvalitetsfynd",
            "",
            "| Allvar | Kod | Fynd | Evidens | Konsekvens | Minsta nästa åtgärd |",
            "|---|---|---|---|---|---|",
        ]
    )
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings = sorted(
        (finding for result in results.values() for finding in result.findings),
        key=lambda item: (severity_order.get(item.severity, 99), item.code),
    )
    for finding in findings:
        values = (
            finding.severity,
            finding.code,
            finding.title,
            finding.evidence,
            finding.impact,
            finding.remediation,
        )
        escaped = [str(value).replace("|", "\\|").replace("\n", " ") for value in values]
        lines.append("| " + " | ".join(escaped) + " |")

    lines.extend(
        [
            "",
            "## Slutsats för nästa checkpoint",
            "",
            "Underlaget räcker för att fortsätta bygga en datamodell och mäta kopplingsgrad.",
            "Det räcker inte för en solver som ska redovisa en verifierad besparing i kronor.",
            "Nästa checkpoint bör därför godkänna korn, nycklar, parameterregister och",
            "kostnadsmodell innan optimeringen införs.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
