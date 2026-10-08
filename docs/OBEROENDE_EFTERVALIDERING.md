# Oberoende eftervalidering

Eftervalideraren kontrollerar en sparad terminskörning utan att anropa den konstruktiva placeringsmetoden. Varje körning innehåller därför en kopia av scenariofilen och `model_inputs.json` med de konkreta behov, rum, spårbarhetsrelationer och scopemått som placeringsresultatet byggde på.

## Körning

```powershell
.\.venv\Scripts\python.exe -m tentaoptimering.cli validate-term-run --run-id <körnings-id>
```

Kommandot skriver `validation.json` och `validation.md` i samma körningsmapp. Varje regel har status `pass`, `fail`, `not_evaluated` eller `not_applicable`, en orsak och berörda objektidentifierare.

## Kontroller

| Regel | Nuvarande kontroll | Begränsning |
| --- | --- | --- |
| `included_demand_coverage` | Varje inkluderat behov har exakt dess deltagarantal placerat. | Gäller endast den valda preliminära omfattningen. |
| `room_capacity` | Summa deltagare per salstillfälle ryms i salens kapacitet. | Kapacitet är fortfarande scenario-/PoC-underlag. |
| `room_time_intervals` | Salintervall jämförs parvis över olika pass, med längsta tentamenslängd och ställtid. | Kontrollerar placeringsresultatet, inte framtida verksamhetsregler. |
| `plan_area` | Behov och sal måste ha samma planeringsområde. | Bygger på tillgänglig ortsinformation. |
| `digital_compatibility` | Redovisar aktiv global kompatibilitetsregel. | Är `assumption_only` utan en verifierad matris. |
| `room_availability` | Redovisar aktiv tillgänglighetsregel. | Är `assumption_only` utan verifierad bokningskalender. |
| `course_program_conflicts` | Kontrolleras när policy och relationer finns. | Nu `not_evaluated`; kurskod räcker inte för att anta en krockregel. |
| `aggregate_staffing` | Jämför beräknad maximal samtidighet med den anonyma poolen. | Ingen individuell vaktplan. |
| `individual_staffing_constraints` | — | Nu `not_evaluated`; raster, resor, kompetens och arbetstid saknas. |

## Sammanfattande status

`technical_placement_completeness` avser endast deltagartäckning, salkapacitet, intervall och ort. `business_feasibility` blir `fail` om en kontrollerad regel bryts och `not_verified` om obligatoriska regler är okontrollerbara eller endast täcks av antaganden. Den kan alltså vara `not_verified` även när 100 procent av inkluderade behov är placerade.
