# Revision a4: eftervalidering, resultat och jämförelser

Datum 2026-10-09. Repo orört (git status ren före och efter). Allt under `...\scratchpad\audit\a4\`. Basrun: `runs\20261009T121351Z-integrated_term_exploratory_2026` (config\scenarios\integrated_term_exploratory.toml mot data\processed; 15 s).
Klassning: V = verifierat (reproducerat), M = motbevisat, O = osäkert/ej testat.

## A. Eftervalideringen

### A1. Oberoende (V)
Läser: `scenario.toml`, `model_inputs.json`, `assignments.csv`, `staff_assignments.csv`, `result.json` (enbart `solution.anonymous_staff_pool_size`). Läser INTE `room_sessions.csv`, `demand_traceability.csv`, `report.md`, `data/processed`.
Importerar `integrated_config` (scenarioparser), `term_calendar.generate_calendar_slots`, `staffing.required_staff`. Importerar inte `term_rules` eller `plan_staffing`/`term_run`. Delad kod (en bugg där syns inte): kalendergenerering (`_is_allowed_date`, perioder/veckodagar/blockerade datum), trappfunktionen, TOML-tolkningen.
Litar på motorns skrivna värden: demandernas `participants`/`duration_minutes`/`plan_area`/`course_code`/`allowed_pass_ids`, rummens `capacity`/`plan_area`/`building_id`, `anonymous_staff_pool_size`. Fångar alltså inte fel i dataunderlaget eller i adaptern `integrated_inputs.py` (M5c, M6b/c, M14, M14b nedan). Mot källpopulationen (1525 aktiviteter; 267 oavgjorda; 1258 inkluderade) jämförs inget. Inget regelstatus beror på `result.json:model_completeness`, `scope_metrics` eller `demand_traceability.csv`.
Ingen integritetskoppling: inga hashar, inget dataunderlagsfingeravtryck, ingen motorversion i integrerade körningar (bara legacy `optimization_runs.py` hashar). En ändrad `scenario.toml` i körningsmappen valideras mot den ändrade regeluppsättningen.

### A2. Kan inställningar/filer göra en okontrollerad regel godkänd?
Rader i `integrated_validation.py`: 212-214 (digital), 232-234 (tillgänglighet), 239 (policy), 257 (program), 278-281 (individuell bemanning).

| Experiment (kopia av basrun) | Resultat | Klass |
|---|---|---|
| S1 `[conflicts] program_relation_data_status="verified"` (fritext, redigerbart i UI-fältet "Status för programrelationer" och i API/JSON) | `course_program_conflicts`: not_evaluated -> **pass**, "respekteras med verifierade relationer", trots att `program_ids` är tomt för alla 1258 behov. Reproducerat helt från start: ny körning med ändrad TOML (scen_e2e\s1_verified.toml) ger samma resultat | V FEL |
| S5 assumption `individual_staffing_rules` `status="verified"` (via "Avancerad JSON" i UI) | `assumption_only` släcks för `individual_staffing_constraints` | V FEL |
| S1+S5 (alla TOML-spakar) | rule-nivå: bara digital/tillgänglighet kvar `pass*`; `business_feasibility` förblir not_verified (digital/tillgänglighet är hårdkodat assumption_only) | V |
| S2 policy="none" | not_evaluated (motorn tillämpar ändå kurskrock) | V konservativt |
| S2b policy innehåller delsträngen `same_course_hard_constraint` + verified | pass: delsträngsmatch på fritext | V svag |
| S3 room_availability-texten ändrad | not_evaluated | V konservativt |
| S3b status=verified på room_availability | ingen effekt (status läses ej) | V |
| S4 digital mode = `all_rooms_verified` | not_evaluated (motorn sätter ändå kapabilitet ["all"] för allt som börjar på `all_`) | V |
| S7 S1+S5 + falsk `model_inputs.json` (`available_slot_ids` för alla rum, ett `digital_requirement`) | **business_feasibility = pass**, inga flaggor, fast 267 källaktiviteter är oavgjorda och ingen verklig data finns | V FEL (kräver filmanipulation av körningsartefakt) |
| S8 ett behov får `digital_requirement` (framtida data), rummen behåller motorns ["all"] härlett ur antagandet | `digital_compatibility`: **pass utan assumption-flagga** ("Explicit matris respekteras") | V latent FEL: `integrated_inputs.py:68` skriver `["all"]` ur ett scenarioläge och validatorn tolkar "all" som verifierad matris |
| Följdobservation | `assumption_only`-regler får **status `pass`** i `validation.json`/`validation.md`/UI (tre av tolv regler: digital, tillgänglighet, individuell bemanning). Bryter AGENTS "avsaknad av data får aldrig bli ett godkänt krav" på regelnivå; endast aggregatet blir not_verified | V |
| `scenario_consistency.py` | skriver bara assumption-`value` ur parametrar, aldrig `status`; room_availability-värdet syns inte i synkroniseringen, så texten är fri. Ingen väg fann där som gör business=pass på egen hand | V |
| Falsklarm: `OBEROENDE_EFTERVALIDERING.md` ("aldrig godkänd kontroll") och UI-texten App.tsx:115 ("saknat datastöd blir inte godkända genom scenarioval") | motbevisade av S1 | M |

### A3. Manipulationstabell (manip.py -> manip_out.txt). tech = teknisk placering, biz = business_feasibility. Basrun: tech=pass, biz=not_verified.

| # | Manipulation | Fångad? | Utfall |
|---|---|---|---|
| M1 | Dubblerad assignment-rad | Ja | tech=fail (coverage, capacity); aggregate+individuell fail |
| M2 | Salskapacitet överskriden (behov konsekvent uppdaterat) | Ja | room_capacity fail |
| M3 | Slot utanför fönster (okänt slot_id) | Ja | assignment_rows fail |
| M3b | Helgplaceringar mot kopia med helgförbud | Ja | assignment_rows fail |
| M4/M4b | Fel ort på sal / behov | Ja | plan_area fail |
| M5 | Behovets deltagare -1 (assignments orörda) | Ja | coverage fail |
| M5b | Assignment-deltagare -1 | Ja | coverage fail |
| M5c | Båda minskade konsekvent (tyst krympning) | **Nej** | tech=pass |
| M6 | Tenta borttagen enbart i assignments | Ja | coverage fail |
| M6b/M6c | Tenta(r) borttagna i assignments + model_inputs (1 resp. 600 av 1258) | **Nej (tech)**; business fail endast för att staff-filen inte uppdaterats | tech=pass, `result.json` påstår fortfarande 1258/100 % |
| M7 | Samma kurs i samma slot | Ja | course_program_conflicts fail |
| M9/9b/9c/9d | Vakt överlappar egna uppdrag / dubblerad rad / allt på en person / rad borttagen | Ja | individuell bemanning fail |
| M9e | staff_assignments.csv borttagen | Ja, konservativt | not_evaluated, biz=not_verified |
| M9f | Varje uppdrag egen person (poolinflation) | **Nej** (inte regelbrott, men pool, kostnad och `anonymous_staff_pool_size` kontrolleras inte mot filen) | pass |
| M10 | pool_size=1 i result.json | Ja | aggregate fail |
| M10b | pool_size=500 | Nej (bara nedre gräns, 9) | pass |
| M10c | objective=1, room_count=1, status=optimal, gap=0 i result.json | **Nej** | objective/rooms/status/gap kontrolleras aldrig |
| M10d | room_sessions.csv skräp | **Nej** | filen läses ej |
| M10e | scheduled_date/pass_id-kolumner i assignments fel | **Nej** | bara slot_id används |
| M11 | Dygnsvila bruten | Ja | staffing fail |
| M12 | Fel byggnad på uppdrag | Ja | fail |
| M14 | Alla salskapaciteter x3 i model_inputs | **Nej** | kapacitet litas på |
| M14b | Alla längder satta till 1 min | Nej på tech; fångas indirekt av bemanning | tech=pass |
| M15 | Samma tenta i två slots | Ja | fail |
| M16 | Två tentor tvingade till samma sal+slot | Ja | capacity fail |
| S11 | Samma sal, samma datum, överlappande pass | Ja | room_time_intervals fail (med baskalendern, ett pass per dag, kan intervallregeln aldrig utlösas av motorn) |
| E1 | Tom assignments.csv (motorns `no_constructive_full_solution`, verifierat end-to-end med infeasible.toml) | **Validatorn kraschar** `EmptyDataError`; ingen validation.json | V FEL |

Sammanfattning: bryts en uttryckt hård regel mellan artefakterna fångas det väl. Missas: fel som ligger i *indata* eller konsistent i *båda* artefakterna, samt alla resultatsiffror (objective, rum, pool, status, gap, täckning).

### A4. Statusrapportering API/UI
- `api.py:188-190`: saknas `validation.json` svarar API `{"status":"not_evaluated","reason":"Den äldre körmotorn saknar ..."}` även för **nya** motorn när validatorn kraschat (E1). Fel orsak, annan JSON-form än normalfallet. `_run` (api.py:236-240) saknar try/except runt validering.
- `frontend/src/App.tsx:23` `statusClass`: pass->grön, fail->röd, annat->neutral. `not_verified` och `constructive_feasible` är neutrala; rule-`pass` med `assumption_only` visas grönt (flaggan finns inte i TS-typen). Teknisk placering visas grön "pass" med orsaken "Alla tekniska placeringsregler passerar" utan att nämna att 267 av 1525 källaktiviteter (17,5 %) inte är med. Resultatvyn visar aldrig `model_completeness`, `limitations`, `cost_comparison`, `optimality_gap` eller `status` (grep ger noll träffar) — "Målfunktion 1 509 000 kr" visas utan explorativ märkning (bara report.md har det).
- `NOT_APPLICABLE` definieras (rad 21) men ingen regel kan returnera det. Ingen regel för: källpopulationstäckning, oavgjorda aktiviteter, bevarat ursprungsschema (AGENTS krav 2), Visby/Uppsala utöver likhet mellan behovets och salens `plan_area` (alla behov är Uppsala; Visby-rummet filtreras bort av `relevant_rooms`, så Visby-regeln är aldrig övad), delade tillfällen.
- Kan teknisk full placering presenteras som genomförbar? Inte med aktuell motor (biz=not_verified), men (a) S7 visar att biz=pass är nåbart utan att populationen täcks, (b) regelnivåns gröna `pass` för antagandekrav, (c) UI:t visar teknisk grön och ger inget omfattningsvarning. V.

## B. Resultat och jämförelser

### B5. Följer redovisade resultat av beräkningarna? (recompute.py, V)
Omräknat enbart ur CSV/TOML: rum = 3 (bergsbrunnagatan-sal-2, fyrislundsgatan-sal-1, råbyvägen-sal-3, 609 platser) x 100000 = 60 900 000; distinkta staff_id = 18 x 5 000 000 = 90 000 000; resa 6390 min x 0; objective 150 900 000 = rapporterat. Arbete 261 720, resa 6 390, bomtid 0, 1272 rader, 237 salstillfällen stämmer. Täckning 1258/1258 av *inkluderade*; 1258/1525 = 82,5 % av källan (rapporterat). Deltagare 46 698 = tilldelade. `anonymous_staff_pool_size` = antal distinkta staff_id (V).
Oberoende toppkontroll av underlaget: max samtidiga platser (alla 1258, ställtid 30) = 1604 den 2026-01-16, matchar docs/MALARKITEKTUR (V).

Statusord: produktens status är `constructive_feasible` (bara greedy-portföljuppräkning, `term_run.py:39-90`) eller `no_constructive_full_solution`; `optimality_gap` är strängen `"not_available_constructive_method"` (ingen siffra). Ingen `optimal` produceras i produktvägen. Ordet "feasible" i `constructive_feasible` bevisar ingen optimalitet; rapporten säger det. Dock:
- Målfunktionen är inte optimerad: bästa av 58 greedy-resultat (portfolios.py): 609-platsportföljen 150,9 M, nästa 151,5 M, 594 platser 159,4 M. Rum 609 mot nedre gräns ceil(46698/79)=591 (3 %). **Bemanning är 60 % av målet (90 M)** och pool 18 är ett greedy-resultat; validatorns nedre gräns är 9 (peak samtidigt behov). Sann nedre gräns okänd, alltså kan poolen vara upp till 2x för stor. Ej bevisat (O).
- Resultatet är en artefakt av modellramen: ett pass per dag 08-18, alla 79 dagar inklusive helg (354 av 1258 tentor på helg), alla tentor fritt flyttbara över hela terminen, ingen kursordning. Det är en plattning över kalendern, inte ett förslag på schema. Kostnadsproxy 1 000 kr/plats och 50 000 kr/vakt är okalibrerade (hyresraderna ger ca 14 200 kr per publicerad plats).
- Tre hemtentor placeras i sal (1258 mot 1255 i nya designen).
- 79 delade `exam_event_id` (166 behov, olika kurskoder) läggs alla på olika datum; ingen regel prövar det (O, jfr B10).
- `staff_per_room_session` används inte av terminsmotorn när `ladder` finns (term_run.py:48 konstrueras men bara kostnaden läses); antagandet `aggregate_staffing`="1" i rapporten är därför missvisande. Parametern lever bara i den oanvända CP-SAT-modellen `integrated_term.py` (CP-SAT: `solver.StatusName().lower()` ger "optimal"/"feasible" utan gap; används bara i tester).
- Portföljuppräkningen är 2^N-1 delmängder per körning; skalar inte till fler rum (O).

### B6. Jämförelser (compare_test.py, V)
`/api/runs/compare` (`api.py:194-212`, `_summarize_run` 41-57):
1. Två körningar på olika dataunderlag (basrun mot samma scenario med 300 aktiviteter flyttade till excluded) jämförs utan varning: delta objective -47 400 000, rum -1, pool -6, placerade -300, `parameter_changes: []` (UI: "Inga scenarieparametrar skiljer körningarna"). Ingen datahash/populationsnyckel i `result.json`.
2. Legacy mot integrerad accepteras (635 av 1258 partiell placering mot full): delta `placed` +623, `objective_ore` None; `parameter_changes` blir en enda jättepost `assumption`.
3. `source_coverage`-delta subtraherar andelar med olika nämnare; ingen kontroll av status (partiell/infeasible), valideringsstatus, motorversion, `included_source_activities`.
4. Parameterdiffen är ofullständig (bara scenario-TOML) och oläsbar för listor: `_flatten_parameters` lägger hela listor (ladder, shift, passes, assumption) som ett värde; frontend `String(change.baseline)` ger "[object Object]" (JS-semantik, ej körd i webbläsare).
5. `delta_from_first` är riktat mot första valda; ingen "jämförbar"-flagga.
6. Basen dubbelräknar: första raden delta 0 trivialt.

### B7. cost_comparison.py (V)
Påståendet "ingen differens" stämmer i kod (inga subtraktioner; test finns); `uncalculated_savings`/`cost_model.py` är död kod (ingen import). Men:
- `source_baseline_preliminary_internal_rent_ore` = 1 674 271 812 återskapat exakt (summa 16 742 718,12 SEK, 41 rader, summan av kolumn `annual_internal_rent_prelim_2026_sek` utan filter).
- Felaktigt definierad: 32 av 41 rader (DH17, `valid_from` 2026-12-01; 2 103 264,66 SEK, 12,6 %) gäller inte den modellerade terminen (jan-mar 2026) och inte idag; rad 4 är P-platser (550 SEK), rad 8 förråd (125 503 SEK), rad 3 utrymningskorridor (26 606 SEK); inget filter på tentamensanvändning eller giltighet. Giltiga i terminen: 9 rader, 14 639 453,46 SEK. Ingen dubbelräkning av `lease_object` men flera rader per objekt (olika rum). Koppling lease-rad -> scenariorum saknas (andra adresser).
- Skalrisk: 16,7 M SEK mot proxykostnad 1,5 M SEK ligger intill varandra i result.json/report.md ("öre per år"). Ingen differens men elva gånger skillnad inbjuder till slutsatsen "91 % besparing". Termin (3 månader) mot årskostnad annualiseras inte.
- `status: not_comparable` men fältet `scenario_assumption_cost_ore` är identiskt med `objective_ore` (inkl. 60 % bemanningsproxy) mot en hyresbaslinje som inte innehåller personal.

### B8. Planerad design (MALARKITEKTUR avsn 3, 4, 9; DOMANMODELL; PARAMETERKATALOG)
Bra: härledd verifiering ("aldrig ur ett värde användaren skrivit"), regel P-1, regression G4, jämbarhetsnyckel, Nuläge = samma kedja, status "kan inte uppfyllas". Luckor:
1. **Valideraren måste inte läsa körningens egna siffror.** Acceptans 7 ("inga fritextfält styr regelstatus") adresserar S1. Men design nämner inte oberoende omräkning av platstopp, population mot Dataunderlag (hash-verifierat), eller att indata (deltagare efter `demand.variation_pct`/avrundning) härleds ur Dataunderlaget + frusen specifikation i stället för sparade modellindata (M5c/M6c/M14). Lägg dessa som obligatoriska regler.
2. **`not_applicable` för oflyttbara** får inte vara parameterstyrt: validatorn ska själv jämföra placering mot originaltillfälle och härleda "oflyttbar". Annars kan `flex.movable_types`/fönster 0 ta bort kontroller och en motorbugg som flyttar en "oflyttbar" tenta missas. Nuvarande `_business_status` behandlar redan `not_applicable` som OK.
3. **Grund "Verifierad" återställs vid återställning.** Härled status ur katalogtabell + dataunderlagsbevis i validatorn (ignorera `basis` i den sparade specen; verifiera `spec_hash` mot en oberoende lagrad hash), annars är SQLite-/JSON-fält en ny fritextväg.
4. **`rooms.capacity_override`/`custom_rooms` (Experiment)** gör `room_capacity` till pass mot påhittad kapacitet. Regelbeviset ska bära kapacitetens proveniens och aggregatet ska bli `experiment`/not_verified.
5. **Jämbarhetsnyckeln räcker inte.** Saknas: lösningsstatus/gap (jämför inte exakt Nuläge med "bästa funna" utan att visa båda sidor), valideringsstatus (fail/partiell får aldrig vara jämförelsepart; AGENTS tillåter partiell placering endast i diagnostik), populations-/omfattningsrad (267 oavgjorda + 82 delade ligger utanför båda sidor, så potentialen för dem är okänd), `objective.*`/`solver.*` är uteslutna ur nyckeln men måste visas som fältvis diff på varje jämförelse (annars samma problem som B6.4). Avvisning ska ange *vilka* fält som skiljer. Reference-cache: motorversionen måste vara kodhash/commit, annars återanvänds en referens räknad med buggig kod. Avrundning i nyckeln även när `variation_pct`=0 ger onödig ojämförbarhet.
6. **B8 "optimistiska undre gränser"** är korrekt bara vid beviset OPTIMAL på relaxationen. Med tidsgräns (`solver.time_limit_seconds`) och "bästa funna" är värdet en övre gräns på optimum; undre gränsen är solverns `best_objective_bound`. Resultatmodellen ska lagra funnet värde, bound, gap och status, och UI/jämförelse får inte kalla funnet värde "undre gräns". Jämförelsen Nuläge (uppnått) minus simulering (gräns) är dessutom ett överskattat delta, inte en lika-med-lika-differens.
7. **Golden master mäts i ett förprov** av samma författare: jag återskapade 1604/2026-01-16 oberoende (V), men 1586, 911, 598 m.fl. är ej återskapade av mig (O).
8. **`rules.keep_course_order` default ja** kan göra Nuläge självt otillåtet om historiska omtentor ligger före ordinarie (O, ej testat); Nuläge ska då redovisa brottet, inte dölja det.
9. **Studentkrockar `not_evaluated` + fotnot** (B4) strider mot AGENTS krav 4 ("hårda villkor ... kurs- och programkrockar"); beslut krävs. Samma kurskod överlappar-ej är kvar som hård regel (bra).
10. Digital kompatibilitet: 813 av 1283 behov är digitala i data (`observed_digital_exam_values`) men ignoreras av nuvarande adapter och utanför katalogen i nya designen. Redovisat som datagap, men validatorn får inte kunna se "all" som verifierad (S8).

## Återskapande
```
cd C:\lokalt\tentalokaler\PoC
$S="C:\Users\gunso745\AppData\Local\Temp\claude\C--lokalt-tentalokaler-PoC\b7d311db-b70e-4a23-b34f-c02537d53902\scratchpad\audit\a4"
.venv\Scripts\python.exe $S\run_base.py config\scenarios\integrated_term_exploratory.toml   # basrun -> $S\runs
.venv\Scripts\python.exe $S\manip.py        # manipulationstabell (manip_out.txt)
.venv\Scripts\python.exe $S\scen.py         # S1-S11 (scen_out.txt)
.venv\Scripts\python.exe $S\recompute.py    # objective/täckning omräkning
.venv\Scripts\python.exe $S\portfolios.py   # portföljuppräkning
.venv\Scripts\python.exe $S\lb.py           # validatorns nedre gräns för pool
$env:LOCALAPPDATA="$S\localappdata"; .venv\Scripts\python.exe $S\compare_test.py   # jämförelsetest
# E2E S1: run_base.py $S\scen_e2e\s1_verified.toml ; E1: $S\scen_e2e\infeasible.toml (se inline-kommando)
```
Sätt `LOCALAPPDATA` för compare_test (api.py skapar annars standard-AppStorage vid import).

## Ej verifierat
Frontend kördes inte i webbläsare (UI-slutsatser från källkod); enhetstestsviten och `check_code_file_lengths` kördes inte; legacy-motorn och CLI-kommandot `validate-term-run`; CP-SAT-vägen; kollektivavtalsanalysen; golden-master-värden utom 1604; om joint-sittings (delade event) är verkliga gemensamma tillfällen; verklig minsta bemanningspool; Visby.
