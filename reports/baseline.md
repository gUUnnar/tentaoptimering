# Baslinjerapport – Tentalokaler-PoC

Rapporten beskriver datakällornas korn, täckning och blockerande kvalitetsrisker.
Den beräknar inte någon optimering eller verifierad besparing.

## Bokningsplaceringar

| Mått | Värde |
|---|---:|
| `rows` | 8466 |
| `normalized_columns` | 40 |
| `unique_non_missing_prefixes` | 5498 |
| `missing_prefix_rows` | 8 |
| `repeated_non_missing_prefixes` | 2468 |
| `rows_in_repeated_non_missing_prefixes` | 5428 |
| `exact_duplicate_rows` | 0 |
| `scheduled_date_min` | 2025-09-01 |
| `scheduled_date_max` | 2026-08-29 |
| `status_counts` | {"Klar": 8089, "Avbokad": 364, "Under behandling": 10, "Andring begard": 3} |
| `missing_room` | 3461 |
| `missing_address` | 364 |

## Ladok-aktiviteter

| Mått | Värde |
|---|---:|
| `rows` | 1525 |
| `normalized_columns` | 14 |
| `start_date_min` | 2026-01-12 |
| `start_date_max` | 2026-03-31 |
| `candidate_key_duplicate_rows` | 162 |
| `missing` | {"total_count": 16, "registered_count": 38, "cancelled_count": 512, "added_count": 1523, "location": 5, "start_time": 1} |

## Lokal- och kostnadsrader

| Mått | Värde |
|---|---:|
| `rows` | 41 |
| `normalized_columns` | 17 |
| `lease_objects` | 8 |
| `future_rows_after_booking_period` | 32 |
| `missing_annual_internal_rent` | 0 |
| `annual_internal_rent_prelim_2026_sek_sum` | 16742718.12 |

## Kvalitetsfynd

| Allvar | Kod | Fynd | Evidens | Konsekvens | Minsta nästa åtgärd |
|---|---|---|---|---|---|
| critical | BOOKING_MIXED_GRAIN | En bokningsrad är inte samma sak som ett tentamenstillfälle | 2468 icke-tomma prefix förekommer på flera rader och omfattar 5428 av 8466 placeringsrader. | Summering av deltagarantal eller platser per rad kan dubbelräkna efterfrågan. | Fastställ prefixets definition och modellera beställning, salplacering och stödplacering som separata korn. |
| critical | LADOK_NO_ATTENDANCE_MEASURE | Faktisk närvaro saknar verifierat fält | Fälten beskriver anmälan och antal men inget fält är uttryckligen faktisk närvaro. | Överdimensionering och realiserbar lokalminskning kan inte uppskattas säkert. | Låt dataägaren definiera ANTAL_TOT och leverera verifierad faktisk närvaro. |
| critical | LEASE_COST_NOT_AVOIDABLE | Internhyra är inte samma sak som realiserbar besparing | Källan redovisar preliminär internhyra men saknar avvecklingsbar avtalsenhet, uppsägningstid och engångskostnader. | En minskad salanvändning kan felaktigt beskrivas som en kostnadsbesparing. | Koppla salar till avtal och klassificera fasta, rörliga och undvikbara kostnader. |
| critical | LEASE_MIXED_OBJECT_TYPES | Lokalrapportens rader är inte ett salregister | 41 rader omfattar bland annat rum, förråd, korridor och parkering. | Rapporten kan inte ensam ge salarnas kapacitet eller avvecklingsbara kostnad. | Komplettera med ett verifierat salregister och en typklassning per rad. |
| high | BOOKING_STATUS_NOT_ATTENDANCE | Bokningsstatus bevisar inte genomförande | Statusfördelning: {'Klar': 8089, 'Avbokad': 364, 'Under behandling': 10, 'Andring begard': 3}. | En retrospektiv baslinje kan inkludera avbokade eller ej genomförda tillfällen. | Definiera vilka statusvärden som ska ingå och verifiera genomförande separat. |
| high | LADOK_JOIN_KEY_AMBIGUITY | Gemensam stabil nyckel till bokningarna saknas | Den provisoriska nyckeln kurskod, datum, tid och lokal markerar 162 rader som dubblettkandidater. | Kopplingen kan tappa eller dubblera samtentor och delade salplaceringar. | Mät kopplingsgrad och tvetydighet samt inför ett stabilt aktivitets-ID. |
| high | LADOK_MISSING_COUNTS | Deltagarfält innehåller saknade värden | Saknade värden: {'total_count': 16, 'registered_count': 38, 'cancelled_count': 512, 'added_count': 1523, 'location': 5, 'start_time': 1}. | Tomt kan inte utan definition tolkas som noll. | Fastställ betydelsen av tomma fält och komplettera eller flagga dem per rad. |
| high | LEASE_PERIOD_MISMATCH | Lokalbeståndet och bokningsperioden avser olika tidpunkter | 32 lokalrader börjar gälla efter bokningsperiodens slut 2026-08-31. | Framtida lokaler kan annars behandlas som historiskt tillgängliga. | Bygg ett tidsversionerat sal- och avtalsregister. |

## Slutsats för nästa checkpoint

Underlaget räcker för att fortsätta bygga en datamodell och mäta kopplingsgrad.
Det räcker inte för en solver som ska redovisa en verifierad besparing i kronor.
Nästa checkpoint bör därför godkänna korn, nycklar, parameterregister och
kostnadsmodell innan optimeringen införs.
