from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class Finding:
    code: str
    dataset: str
    severity: str
    title: str
    evidence: str
    impact: str
    remediation: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class QualityResult:
    metrics: dict[str, Any]
    findings: list[Finding]

    def to_dict(self) -> dict[str, Any]:
        return {
            "metrics": self.metrics,
            "findings": [finding.to_dict() for finding in self.findings],
        }


def _missing_count(frame: pd.DataFrame, column: str) -> int:
    return int(frame[column].isna().sum())


def validate_bookings(frame: pd.DataFrame) -> QualityResult:
    prefix_counts = frame["prefix"].value_counts(dropna=True)
    repeated_prefixes = int((prefix_counts > 1).sum())
    repeated_rows = int(prefix_counts[prefix_counts > 1].sum())
    source_columns = [
        column
        for column in frame.columns
        if column
        not in {"placement_id", "exam_order_id", "address_key", "room_key", "location_key"}
    ]
    exact_duplicates = int(frame[source_columns].duplicated().sum())
    status_counts = {
        str(key): int(value) for key, value in frame["status"].value_counts(dropna=False).items()
    }
    metrics = {
        "rows": int(len(frame)),
        "normalized_columns": int(frame.shape[1]),
        "unique_non_missing_prefixes": int(frame["prefix"].nunique()),
        "missing_prefix_rows": _missing_count(frame, "prefix"),
        "repeated_non_missing_prefixes": repeated_prefixes,
        "rows_in_repeated_non_missing_prefixes": repeated_rows,
        "exact_duplicate_rows": exact_duplicates,
        "scheduled_date_min": frame["scheduled_date"].dropna().min(),
        "scheduled_date_max": frame["scheduled_date"].dropna().max(),
        "status_counts": status_counts,
        "missing_room": _missing_count(frame, "room"),
        "missing_address": _missing_count(frame, "address"),
    }
    findings = [
        Finding(
            code="BOOKING_MIXED_GRAIN",
            dataset="bookings",
            severity="critical",
            title="En bokningsrad är inte samma sak som ett tentamenstillfälle",
            evidence=(
                f"{repeated_prefixes} icke-tomma prefix förekommer på flera rader och omfattar "
                f"{repeated_rows} av {len(frame)} placeringsrader."
            ),
            impact="Summering av deltagarantal eller platser per rad kan dubbelräkna efterfrågan.",
            remediation=(
                "Fastställ prefixets definition och modellera beställning, salplacering och "
                "stödplacering som separata korn."
            ),
        ),
        Finding(
            code="BOOKING_STATUS_NOT_ATTENDANCE",
            dataset="bookings",
            severity="high",
            title="Bokningsstatus bevisar inte genomförande",
            evidence=f"Statusfördelning: {status_counts}.",
            impact="En retrospektiv baslinje kan inkludera avbokade eller ej genomförda tillfällen.",
            remediation="Definiera vilka statusvärden som ska ingå och verifiera genomförande separat.",
        ),
    ]
    if exact_duplicates:
        findings.append(
            Finding(
                code="BOOKING_EXACT_DUPLICATES",
                dataset="bookings",
                severity="medium",
                title="Exakta dubbletter finns i bokningsexporten",
                evidence=f"{exact_duplicates} rader är exakta dubbletter när internt rad-ID ignoreras.",
                impact="Dubbletter kan blåsa upp placerings- och volymmått.",
                remediation="Verifiera om raderna är verkliga separata placeringar eller exportdubbletter.",
            )
        )
    return QualityResult(metrics=metrics, findings=findings)


def validate_ladok(frame: pd.DataFrame) -> QualityResult:
    candidate_key = ["course_code", "start_date", "start_time", "location_key"]
    duplicate_candidates = int(frame.duplicated(candidate_key, keep=False).sum())
    missing = {
        column: _missing_count(frame, column)
        for column in (
            "total_count",
            "registered_count",
            "cancelled_count",
            "added_count",
            "location",
            "start_time",
        )
    }
    metrics = {
        "rows": int(len(frame)),
        "normalized_columns": int(frame.shape[1]),
        "start_date_min": frame["start_date"].dropna().min(),
        "start_date_max": frame["start_date"].dropna().max(),
        "candidate_key_duplicate_rows": duplicate_candidates,
        "missing": missing,
    }
    findings = [
        Finding(
            code="LADOK_NO_ATTENDANCE_MEASURE",
            dataset="ladok",
            severity="critical",
            title="Faktisk närvaro saknar verifierat fält",
            evidence="Fälten beskriver anmälan och antal men inget fält är uttryckligen faktisk närvaro.",
            impact="Överdimensionering och realiserbar lokalminskning kan inte uppskattas säkert.",
            remediation="Låt dataägaren definiera ANTAL_TOT och leverera verifierad faktisk närvaro.",
        ),
        Finding(
            code="LADOK_MISSING_COUNTS",
            dataset="ladok",
            severity="high",
            title="Deltagarfält innehåller saknade värden",
            evidence=f"Saknade värden: {missing}.",
            impact="Tomt kan inte utan definition tolkas som noll.",
            remediation="Fastställ betydelsen av tomma fält och komplettera eller flagga dem per rad.",
        ),
        Finding(
            code="LADOK_JOIN_KEY_AMBIGUITY",
            dataset="ladok",
            severity="high",
            title="Gemensam stabil nyckel till bokningarna saknas",
            evidence=(
                f"Den provisoriska nyckeln kurskod, datum, tid och lokal markerar "
                f"{duplicate_candidates} rader som dubblettkandidater."
            ),
            impact="Kopplingen kan tappa eller dubblera samtentor och delade salplaceringar.",
            remediation="Mät kopplingsgrad och tvetydighet samt inför ett stabilt aktivitets-ID.",
        ),
    ]
    return QualityResult(metrics=metrics, findings=findings)


def validate_leases(frame: pd.DataFrame) -> QualityResult:
    future_rows = int((frame["valid_from"].fillna("") > "2026-08-31").sum())
    missing_rent = _missing_count(frame, "annual_internal_rent_prelim_2026_sek")
    total_rent = float(frame["annual_internal_rent_prelim_2026_sek"].sum(min_count=1))
    metrics = {
        "rows": int(len(frame)),
        "normalized_columns": int(frame.shape[1]),
        "lease_objects": int(frame["lease_object_key"].nunique()),
        "future_rows_after_booking_period": future_rows,
        "missing_annual_internal_rent": missing_rent,
        "annual_internal_rent_prelim_2026_sek_sum": round(total_rent, 2),
    }
    findings = [
        Finding(
            code="LEASE_MIXED_OBJECT_TYPES",
            dataset="leases",
            severity="critical",
            title="Lokalrapportens rader är inte ett salregister",
            evidence=f"{len(frame)} rader omfattar bland annat rum, förråd, korridor och parkering.",
            impact="Rapporten kan inte ensam ge salarnas kapacitet eller avvecklingsbara kostnad.",
            remediation="Komplettera med ett verifierat salregister och en typklassning per rad.",
        ),
        Finding(
            code="LEASE_COST_NOT_AVOIDABLE",
            dataset="leases",
            severity="critical",
            title="Internhyra är inte samma sak som realiserbar besparing",
            evidence=(
                "Källan redovisar preliminär internhyra men saknar avvecklingsbar avtalsenhet, "
                "uppsägningstid och engångskostnader."
            ),
            impact="En minskad salanvändning kan felaktigt beskrivas som en kostnadsbesparing.",
            remediation="Koppla salar till avtal och klassificera fasta, rörliga och undvikbara kostnader.",
        ),
        Finding(
            code="LEASE_PERIOD_MISMATCH",
            dataset="leases",
            severity="high",
            title="Lokalbeståndet och bokningsperioden avser olika tidpunkter",
            evidence=f"{future_rows} lokalrader börjar gälla efter bokningsperiodens slut 2026-08-31.",
            impact="Framtida lokaler kan annars behandlas som historiskt tillgängliga.",
            remediation="Bygg ett tidsversionerat sal- och avtalsregister.",
        ),
    ]
    return QualityResult(metrics=metrics, findings=findings)
