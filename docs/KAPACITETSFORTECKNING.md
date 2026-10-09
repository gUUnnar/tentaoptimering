# Kapacitetsförteckning (S0)

Varje funktion som dagens system tillhandahåller får en rad: vart den tar vägen, eller varför den avvecklas. Förteckningen bygger på `tools/inventory.py` (importgraf, nåbarhet, oreferererade symboler, API-rutter, CLI-kommandon, frontendfiler) och på granskningen av koden. Omtaget godkänns först när varje rad har exakt en implementation i den nya koden eller en motiverad avveckling, och när `tools/inventory.py` visar att ingen avvecklad komponent finns kvar.

**Resultat av inventeringsverktyget (nuvarande gren, 37 moduler):** moduler utan väg från produktionsingång: `cost_model`, `synthetic_integrated` (båda används bara av tester). Oreferererade publika symboler: `canonical_demand.build_canonical_exam_demands`, `cost_model.CostComponent`, `cost_model.uncalculated_savings`, `integrated_term.solve_integrated_term`, `synthetic_integrated.solve_synthetic_integrated`. API: 17 rutter. CLI: 10 kommandon. Frontend: 9 filer.

Beslutsord: **Behåll**, **Bygg om**, **Ersätt**, **Ta bort**. "Flytta först" anger funktioner som måste leva vidare innan en modul raderas.

## 1. Data och förberedelse

| Funktion | Plats idag | Beslut | Ny plats / skäl | Beroenden |
|---|---|---|---|---|
| Inläsning av tre källfiler | `loaders.py`, `config/source_files.toml` | Behåll | Dataunderlagets bygge | `pipeline` |
| Normalisering | `normalize.py` | Behåll | Oförändrad | - |
| Kvalitetskontroller | `validation.py`, `reporting.py` | Behåll / bygg om reporting | Kvalitetssammanfattning i Dataunderlaget; inga Markdownrapporter i Git | `pipeline` |
| Kandidatrelation aktivitet ↔ bokning | `linkage.py`, `model_inputs._build_candidate_relations` | Behåll | Dataunderlaget | - |
| Bokningshändelser, rumsinventering | `model_inputs.py` | Bygg om | Bär historiskt datum, start, typ, kurskod, institutionskod, `uses_room`; ta bort `optimization_*`-namn | `load_demand_measure` läser `config/parameters.toml` (**måste kopplas bort**) |
| Rumsregister | `config/room_register.toml` | Behåll | Referensdata i Dataunderlaget; kapacitetsgrund och källa | - |
| Omfattningsbeslut | `canonical_demand` (scope-delen) | Behåll | Dataunderlagets omfattning | `pipeline`, `reporting` |
| Tentamensbehov via delgrupper | `canonical_demand.build_canonical_exam_demands` | Bygg om (återanvänd) | Enda väg för att bilda behov (se `DATAANALYS_S0.md` §3) | Idag bara tester |
| Orkestrering av inläsning | `pipeline.py`, `cli prepare` | Bygg om | `DatasetService` skriver ett Dataunderlag | Globala `data/processed`, `reports/` upphör |
| Körmanifest med hashar | `provenance.py`; `optimization_runs._input_manifest` | Behåll / **flytta först** | Dataunderlagets manifest; hashar av källfiler ingår i frusen specifikation | Finns i dag bara i äldre körformatet |
| Normaliserade tabeller i repot | `reports/*`, `data/processed` (gitignored) | Ta bort ur Git | Genererat; Dataunderlaget bär dem | `.gitignore` |
| Historisk topp i efterfrågan (baslinje) | `optimizer_time.historical_capacity_check` | **Flytta först** | Oberoende kontroll av Nuläge (1 604 platser) | Enda implementationen |
| Hjälpfunktioner för tid | `optimizer_time.clock_minutes`, `duration_minutes` | **Flytta först** | Neutral tidsmodul | `integrated_inputs` |

## 2. Beräkning

| Funktion | Plats idag | Beslut | Ny plats / skäl | Beroenden |
|---|---|---|---|---|
| Kapacitetsoptimerare (äldre) | `optimizer_config`, `optimizer_model`, `optimizer_hint`, `optimizer_validation` | Ta bort | Ersätts av steg A | `optimization_runs`, `app_storage`, `cli`, `test_optimizer` |
| Körningslagring och jämförelse (äldre) | `optimization_runs.py` | Ta bort | `RunService`, `CompareService`; flytta först manifest-logiken | `api`, `cli` |
| Konstruktiv terminsmotor | `term_run.py` | Ta bort | Ersätts av steg A/B/C | `integrated_runs`, `cli`, `api` |
| Terminskalender, tillåtna datum/pass | `term_calendar.py` | Bygg om | Tillfälle = datum + starttid; fönster per tentamen | `integrated_validation`, `term_run` |
| Hårda regler (område, kurskrock, digitalt, tillgänglighet) | `term_rules.py` | Bygg om | Samma-kurs-regeln och områdesregeln behålls; digital/tillgänglighet endast om motorn läser dem | `integrated_term` |
| Bemanningsplan | `staffing.py` | Behåll | Steg C; `_staffing_tasks` flyttas ur `term_run` | - |
| Bemanningskontroll | `staffing_validation.py` | Behåll | Fristående validerare | `integrated_config` |
| CP-SAT för små instanser (syntetiskt) | `integrated_term.solve_integrated_term`, `synthetic_integrated.py` | Flytta till `tests/` | Orakel för steg A/B | Dataklasserna i `integrated_term` används av andra moduler |
| Dataklasser för behov och rum | `integrated_term.IntegratedDemand/Room/AggregateStaffing` | Bygg om | Planeringsproblemets typer | `term_rules`, `term_run`, `integrated_inputs` |
| Scenariokonfiguration | `integrated_config.py`, `scenario_consistency.py` | Ta bort | Parameterkatalog + frusen specifikation | `app_storage`, `integrated_runs`, `integrated_validation` |
| Läsning av modellindata | `integrated_inputs.py` | Ta bort | `planning_problem.build` | `integrated_runs` |
| Körningsartefakter | `integrated_runs.py` | Ta bort | `RunService` | `api`, `cli` |
| Kostnadsdatatyper och spärr | `cost_model.py`, `cost_comparison.py` | Bygg om | Resultatmodellens kostnadsprofil; principen "ingen differens mot internhyra" och dess test behålls | `integrated_runs` |

## 3. Validering

| Regel idag | Beslut | Not |
|---|---|---|
| `included_demand_coverage` | Behåll | Täckning av beräkningsbar population |
| `assignment_rows`, `model_inputs` | Bygg om | Konsistens mellan frusen indata och placering |
| `room_capacity`, `room_time_intervals` | Behåll | Mot publicerad kapacitet och ställtid |
| `plan_area` | Behåll | Ort |
| `calendar_pass_constraints` | Bygg om | Fönster, veckodag, spärr, starttid för flyttbara; `not_applicable` för oflyttbara |
| `course_program_conflicts` | Bygg om | Läser **aldrig** `conflict_policy` eller `program_conflict_data_status`; kursregel + ordning; studentkrock `not_evaluated` |
| `digital_compatibility`, `room_availability` | Bygg om | Läser aldrig antagandetext; `not_evaluated` utan data |
| `aggregate_staffing`, `individual_staffing_constraints` | Behåll | Via `staffing_validation` |
| Nya regler: kursordning, efterfrågan omräknad, platstopp omräknad, Nuläge = källa | Nytt | S1 |

## 4. App-lager

| Funktion | Plats idag | Beslut | Ny plats / skäl |
|---|---|---|---|
| `GET /api/health` | `api.py` | Bygg om | Behålls |
| `GET/PUT /api/settings`, `POST /api/settings/choose-source-directory` | `api.py`, `directory_picker.py` | Ersätt | Källkatalog väljs i inläsningen av Dataunderlag; mappväljaren byggs in där (inte som separat inställning) |
| `GET /api/parameters` | `api.py` | Ersätt | `/api/parameterkatalog` |
| `GET/POST/PUT /api/scenarios…`, `POST …/validate` | `api.py`, `app_storage.py` | Ta bort | `/api/simuleringar` (CRUD, kopia, förutsättningar) |
| `POST /api/preparation` | `api.py` | Ersätt | `POST /api/dataunderlag` |
| `POST /api/simulations?scenario_id=` | `api.py` | Ersätt | `POST /api/simuleringar/{id}/korningar` |
| `GET /api/jobs/{id}` | `api.py`, `job_manager.py` | Ersätt | Körningens status och förlopp, persistent |
| `GET /api/runs…`, `…/validation`, `POST /api/runs/compare` | `api.py` | Ersätt | `/api/korningar…`, `/api/jamforelser` |
| Statisk betjäning av frontend | `api.py` | Behåll (mekanismen) | Samma princip i nya API:t |
| Lokal server, port, öppna webbläsare | `desktop.py` | Bygg om | Ledig port, enkel-instans-lås |
| Sökvägar och användardata | `app_paths.py` | Behåll | Ny datakatalog |
| CLI: `prepare`, `status`, `resources`, `parameters`, `validate-config`, `optimize`, `result`, `compare`, `optimize-term`, `validate-term-run` | `cli.py` | Bygg om | Tre kommandon över tjänsterna: importera data, kör simulering, validera körning |
| Frontend: Översikt, Parametrar, Scenarier, Simuleringar, Resultat, jämförelse | `frontend/src/**` (9 filer) | Ersätt | Ny informationsarkitektur; verktygskedjan (Vite, TypeScript, Tailwind) behålls |
| Paketering till Windows | `packaging/*` | Bygg om | Verifierad ren installation |

## 5. Tester

| Test | Beslut |
|---|---|
| `test_optimizer.py` | Ta bort |
| `test_api.py`, `test_app_storage.py`, `test_cli.py` | Ersätt |
| `test_integrated_config.py`, `test_integrated_inputs.py` | Ersätt |
| `test_integrated_validation.py`, `test_staffing.py`, `test_term_calendar.py`, `test_term_run.py` | Behåll regelinnehållet; skriv om mot ny struktur |
| `test_integrated_term.py`, `test_synthetic_integrated.py` | Flytta till orakel |
| `test_canonical_demand.py`, `test_linkage.py`, `test_model_inputs.py`, `test_normalize.py` | Behåll |
| `test_cost_model.py`, `test_cost_comparison.py` | Bygg om (spärren mot besparingspåstående ska finnas kvar) |
| `test_file_policy.py` | Bygg om (utöka till TS/TSX och radlängd) |

## 6. Dokument

Behåll och uppdatera: `KONCEPTUELL_KRAVSPECIFIKATION`, `GEMENSAM_OPTIMERINGSDESIGN`, `KOSTNADSMODELL`, `DATAMODELL`, `OBEROENDE_EFTERVALIDERING`, `BLOCKERANDE_DATAGAP`. Ersätt: `README`, `AGENTS`, `FILOVERSIKT`, `LOKALT_GRANSSNITT`, `OPTIMERINGSMOTOR`. Ta bort när de saknar funktion: `FORSTA_TERMSKORNING`, `GAP_ANALYS_MOT_KRAVSPECIFIKATION`, `KODGRANSKNING_OCH_CODEX_UPPDRAG_2026-10-08`, `OPTIMERINGSUNDERLAG`, `Uppdrag_Claude_Codex_tentalokaler_PoC`, `Slutsatser_tentalokaler_2026-10-06`. Nya: `DOMANMODELL`, `PARAMETERKATALOG`, `ANALYS_KOLLEKTIVAVTAL`, `DATAANALYS_S0`, `KRAVUPPFYLLNAD`, `KAPACITETSFORTECKNING` (denna).

## 7. Kontroll innan omtaget godkänns

| Kontroll | Hur |
|---|---|
| Varje rad ovan har en implementation eller en motiverad avveckling | Manuell genomgång mot denna fil i varje PR |
| Inga avvecklade moduler finns kvar | `python tools/inventory.py` visar inga moduler utan väg från produktionsingång; `removed_symbols`-kontroll (R2 i planen) |
| Funktioner att flytta först är flyttade | Test: varje funktion i "Flytta först" har en anropare i ny kod och ett test |
