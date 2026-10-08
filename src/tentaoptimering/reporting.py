from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .canonical_demand import ScopeReport
from .linkage import CandidateLinkageResult
from .model_inputs import OptimizationInputs
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


def write_linkage_json(result: CandidateLinkageResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "metrics": result.metrics,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_linkage_report(result: CandidateLinkageResult, path: Path) -> None:
    lines = [
        "# Kandidatkoppling bokningar–Ladok",
        "",
        "Detta är en kopplingsdiagnostik, inte en verifierad sammanslagning av källorna.",
        "En kandidat kräver samma kurskod, bokningsdatum och bokningens starttid.",
        "Samma kandidatnyckel kan fortfarande beskriva olika aktiviteter, en samtenta eller flera salplaceringar.",
        "",
        "## Mätvärden",
        "",
        "| Mått | Värde |",
        "|---|---:|",
        *_metric_rows(result.metrics),
        "",
        "## Tolkning och avgränsning",
        "",
        "- `single_candidate` betyder endast att exakt en Ladok-rad delar kandidatnyckeln; det är inte en godkänd verksamhetsmatchning.",
        "- `ambiguous_candidates` ska utredas med stabilt aktivitets-ID eller dokumenterad kopplingsregel. De ska inte väljas automatiskt.",
        "- `location_key_equal` är endast ett transparent kontrollmått. Boknings- och Ladoklokaler har olika namnsättning och saknar verifierad översättningstabell.",
        "- Deltagarantal från Ladok används inte i denna artefakt och tolkas inte som faktisk närvaro.",
        "- Fullständig radnivå finns i `data/processed/candidate_linkage.csv` för manuell granskning och återskapas från originalkällorna.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_scope_json(result: ScopeReport, path: Path) -> None:
    """Write the activity-level scope summary; detailed rows remain in CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "metrics": result.metrics,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_scope_report(result: ScopeReport, path: Path) -> None:
    """Describe why this report is not yet a complete demand definition."""
    metrics = result.metrics
    lines = [
        "# Omfattningsrapport för Ladokaktiviteter",
        "",
        "Varje Ladokaktivitet redovisas i `demand_scope.csv` med ett scope-beslut, en orsak och evidensreferens.",
        "En oavgjord aktivitet får inte räknas bort och förhindrar en fullständig verksamhetsberäkning.",
        "",
        "## Mätvärden",
        "",
        "| Mått | Värde |",
        "|---|---:|",
        *_metric_rows(metrics),
        "",
        "## Tolkning",
        "",
        "- `included` i den första rapporten betyder endast inkluderad i uttrycklig teknisk PoC-omfattning. Ett verksamhetsbeslut krävs innan den får beskrivas som slutligt inkluderad.",
        "- Flera aktiviteter kan tillhöra samma delgrupp; delgruppen äger deltagarantalet så att samma tentander inte dubbelräknas.",
        "- `excluded` måste ha en dokumenterad verksamhetsorsak och evidens, exempelvis digital examination utanför vald fysisk omfattning.",
        "- `unresolved` är synligt i rapporten och blockerar påståenden om full täckning för hela populationen.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_optimization_readiness_json(result: OptimizationInputs, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "metrics": result.metrics}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_optimization_readiness_report(result: OptimizationInputs, path: Path) -> None:
    metrics = result.metrics
    ready = metrics["optimization_demands_ready_provisional"]
    lines = [
        "# Optimeringsunderlag – databereddhet",
        "",
        "Rapporten beskriver det maskinläsbara underlaget för en explorativ PoC-körning.",
        "Den kör ingen optimering och redovisar ingen besparing.",
        "",
        "## Mätvärden",
        "",
        "| Mått | Värde |",
        "|---|---:|",
        *_metric_rows(metrics),
        "",
        "## Vad som nu kan användas i PoC:n",
        "",
        f"- {ready} Ladokaktiviteter "
        f"({metrics['optimization_demand_record_coverage_percent']} %) har en entydig kandidat "
        "till en provisorisk bokningshändelse och ett ifyllt `registered_count`.",
        f"- Dessa rader täcker "
        f"{metrics['available_ladok_demand_share_in_ready_inputs_percent']} % av den "
        "tillgängliga summan i det provisoriska Ladokmåttet.",
        "- Varje sådan efterfrågepost kan följas via `activity_id`, `exam_event_id` och `placement_id` till de historiska placeringarna.",
        f"- Det officiella referensregistret innehåller publicerad rumskapacitet för "
        f"{metrics['published_room_capacities']} rum; "
        f"{metrics['observed_rooms_with_published_capacity']} av dem förekommer i bokningsperioden.",
        f"- `optimization_rooms.csv` innehåller {metrics['optimization_rooms_ready_for_exploratory_poc']} "
        f"scenariorum med sammanlagt {metrics['optimization_room_capacity_sum_ready_for_exploratory_poc']} "
        "publicerade platser. De får användas för explorativ kapacitetsanalys enligt parameterregistret.",
        "- Rummen är scenariokandidater utan kalendergaranti. En PoC får därför undersöka kapacitet, "
        "packning och känslighet men inte hävda att ett föreslaget schema är genomförbart.",
        "- `room_inventory.csv` skiljer publicerad kapacitet från observerade bokade platser. De senare är historiskt utfall och aldrig en antagen kapacitet.",
        "",
        "## Osäkerheter och kvarvarande spärrar för operativ användning",
        "",
        "- De publicerade kapaciteterna kommer från en webbsida uppdaterad 2026-09-24 och är inte tidsverifierade för bokningsperioden 2025–2026. De används endast genom den uttryckliga PoC-regeln och är inte markerade som operativt verifierade.",
        f"- Webbsidan anger totalt {metrics['published_total_places_claim']} platser, medan de individuellt angivna kapaciteterna summerar till {metrics['sum_of_individually_listed_capacities']}. Skillnaden på {metrics['published_capacity_reconciliation_gap']} platser måste förklaras av dataägaren.",
        "- Bokningar visar historisk användning, inte en verifierad tillgänglighetskalender eller ett tillåtet framtida salbestånd.",
        "- Kandidatkopplingen är teknisk och inte en verksamhetsverifierad nyckel; tvetydiga och omatchade aktiviteter exkluderas från efterfrågetabellen i stället för att fördelas godtyckligt.",
        "- `registered_count` är ett provisoriskt registreringsmått enligt parameterregistret, inte faktisk närvaro.",
        "- Lokal- och avtalsrader kopplas inte till rum utan en verifierad översättningstabell; inga kostnadsresultat kan härledas.",
        "",
        "## Nästa konkreta steg",
        "",
        "1. Kör och jämför versionshanterade scenarier mot `optimization_demands.csv` och `optimization_rooms.csv`, med antagandena synliga i varje resultat.",
        "2. Utvärdera täckning, överkapacitet och ej placerbar efterfrågan som PoC-resultat, inte som ett operativt schema eller en besparing.",
        "3. Bekräfta senare kapaciteternas giltighetsperiod, faktisk tillgänglighet och skillnaden mot sidans totalsumma före operativ användning.",
        "4. Godkänn eller ersätt kandidatregeln och efterfrågemåttet när bättre verksamhetsdata finns.",
        "5. Håll alla scenario- och verksamhetsregler justerbara i parameterregistret.",
        "",
        "Kapacitetskälla: https://www.uu.se/medarbetare/stod-och-verktyg/lokaler/boka-tentamensplatser",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
