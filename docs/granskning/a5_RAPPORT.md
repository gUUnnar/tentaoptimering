# Testrevision (A5): mutationstestning och handräknade kontrollexempel

Repo oförändrat. Alla körningar mot kopian `...\audit\a5\repo_copy` (`mut_work`). Verifierat: `tentaoptimering.__file__` pekar på kopian (se första raden i `mut_log.txt` och `handcalc`-utskriften). Sviten: 62 tester, alla gröna, ca 3 s.

## 1. Vad varje testfil faktiskt bevisar
Klass: A = oberoende handräknat facit, B = egenskapstest, C = självbekräftande/tautologiskt, D = ytlig röktest.

| Fil | Klass | Bedömning |
|---|---|---|
| test_term_run (2) | A (smal) | Handräknat start 450/slut 630 (prep 30 + 120 + closing 30). Överlappande pass: ger "no solution". Täcker inte kapacitet, ställtid, kurskrock, ort, portföljval, kostnad, täckningsmått. Termmotorn har alltså 2 tester. |
| test_term_calendar (3) | A | Veckodagar, längd mot pass, period + blockerat datum. Saknar gränsfall (`<=`), allowed_dates, allowed_pass_ids, slutdatum. |
| test_staffing (4) | A/B | Trappa 51->2 (men inte 50, 150/151), restid 30 vs 15 min lucka, rast/vila, utanför pass, segment. Använder inga exakta gränser (300/301, 660/659, rast 30/29): **mutanter M31-M37 överlever**. |
| test_integrated_term (3) CP-SAT | A | Handräknat 80000/2/320000. Täckning, kurskrock och digitalt. Men mutant "krockar borttagna" (M109) överlever. |
| test_synthetic_integrated (2) | A | Handräknat 80000/240000/320000, 630. Mest bevis på modellkoncept, inte på produktionsmotorn. |
| test_integrated_validation (11) | A/B | Bäst test i sviten (fail-fall per regel). Saknar exakta gränser, kurskrock vid tangerande tider, program-krock, individuell bemanning med fail (finns bara ett pass-fall). |
| test_canonical_demand (4) | A/B | Fångar ett fall av dubbelräkning men bara när varje delgrupp har en aktivitet; M78 (sum->max) och M79, M81, M85 överlever. |
| test_linkage (2) | A | Handräknat. Saknar kodmönstergränser (M86), tid i nyckel (M89). |
| test_normalize (2) | D | Bara att `key_text` ger rätt sträng samt `placement_id` unika. Datum-/tidsnormalisering (M92, M93, M91) otestad. |
| test_model_inputs (5) | C/A | Hårdkodade siffror (206, 1220, 8 rum, 1179) mot `config/room_register.toml`: konfigurationsverifiering, inte beräkningstest. Entydig-kandidat-logik testad. M99 dödad, M100/M101 överlever. |
| test_optimizer (6) | A/B | Gamla fixed-time-linjen; kapacitet, delning, tidsflex. Delvis A. M95-M98 (optimizer_time) överlever helt. |
| test_integrated_inputs (1) | D/A | Adapter: enda test; M69-M71, M73-M75 överlever (ready-filter, kostnad per plats, ort, längd). |
| test_integrated_config (1) | D | Läser TOML, kollar antal antaganden >= 6 och att slots > 0. |
| test_cost_model (1) | C | Funktion returnerar konstant None; testet bekräftar konstanten. |
| test_cost_comparison (1) | A (smal) | 100,50 SEK -> 10050 öre. |
| test_cli (7) | D | Parser/JSON-struktur och felkoder. Inga siffror verifieras. |
| test_api (1) | D/B | Röktest end-to-end med **en** tenta och **ett** rum; assertar bara att nycklarna finns i valideringen och att jämförelsen har 2 körningar. Verifierar inte att placeringen är rätt. |
| test_app_storage (4) | B | Rundresa TOML, validering, säkra id:n. |
| test_file_policy (2) | B | Radgränser. |

Tester utan assertion på det väsentliga: test_api (inget om resultat), test_cli, test_integrated_config, test_cost_model, test_term_run kollar bara status/tider men inte kapacitet.

## 2. Mutationsresultat (112 mutanter, en i taget)
Dödade 38, **överlevde 74**. Rådata: `mutation_results.json`, `mut_log.txt`, mutationerna i `mutations.py`. Kolumnen "Hand" = döds av min handräknade svit (`hand_vs_mut.json`, 34 av de 74 dödas där).
Sannolikt ekvivalenta eller icke-hårda: M09 (plan_area dubbelkontrolleras i motorn), M20, M21 (portföljen med minst rum är ändå billigast), M23, M27 (tom ort ger ändå ingen lösning), M29 (lastutjämning), M43 (sorterade uppgifter), M101 (parametern är redan true), M18 (ekvivalent vid ställtid 0 i mitt test). Övriga överlevare är riktiga testluckor.

Överlevande (fil:rad i original -> mutation -> vilket test borde fångat):

| ID | fil:rad | mutation | Hand | Test som borde fångat |
|---|---|---|---|---|
| M01 | term_calendar:112 | `<=`->`<` (tentamen ryms precis) | dödad | eligible_slots 240 min i pass 08-12 |
| M07 | term_calendar:110 | allowed_pass_ids ignoreras | ej | kalender-/motortest med tillåtna pass |
| M08 | term_calendar:86 | allowed_dates ignoreras | ej | kalendertest med allowed_dates |
| M10 | term_rules:37 | `<`->`<=` (tangerande tentor = krock) | dödad | motortest samma kurs 08-10 / 10-12 |
| M11 | term_rules:36 | datumjämförelse borta | dödad | samma kurs två dagar |
| M12 | term_rules:23 | digital kompatibilitet alltid sann | dödad | motortest digitalt krav mot pappersal |
| M13/M15 | term_rules:30/28 | programkrock / kurskrock ignorerad (CP-SAT) | ej | CP-SAT-test med enbart program-relation |
| M16 | term_run:132 | `<`->`<=` kapacitet vid taket | dödad | deltagare = salkapacitet |
| M17 | term_run:193 | ställtid i `_room_is_free` borta | dödad | pass som startar 12:29 vs 12:30 |
| M18 | term_run:219 | ställtid i available_again | ej | room_sessions med ställtid > 0 |
| M19 | term_run:123 | kurskrock ignorerad i motorn | dödad | samma kurs, ett pass |
| M20-M23, M27, M29 | term_run | se ekvivalenta ovan | ej | - |
| M22 | term_run:69 | restidskostnad ur målfunktionen | ej | mål med travel_cost > 0 |
| M24 | term_run:71 | väljer DYRASTE portföljen | dödad | portföljval med tre rum |
| M26 | term_run:260 | alltid 1 vakt oavsett trappa | dödad | 51 deltagare -> 2 vakter |
| M28 | term_run:270 | täckningsmått delat med total | dödad | included=1, total=2 |
| M30 | term_run:192 | rumsöverlapp utan datum | dödad | samma sal två dagar |
| M31 | staffing:61 | trappa `<=`->`<` | dödad | 50/51/150/151 |
| M32 | staffing:162 | arbetspass precis (`<=`->`<`) | dödad | uppgift 450-1110 i pass 450-1110 |
| M33 | staffing:137 | restid precis | dödad | lucka 30 vs 29 |
| M34 | staffing:141 | dygn 660 precis | dödad | 660/661 |
| M35 | staffing:144 | rast 30 precis | dödad | 30/29 |
| M36 | staffing:146 | 300 min precis | dödad | 300/301 |
| M37 | staffing:135 | dygnsvila 660 precis | dödad | 660/659 |
| M42 | staffing:94 | restid summeras inte | dödad | travel_minutes |
| M43 | staffing:132 | datumordning | ej (ekv.) | - |
| M44 | staffing_validation:81 | överbemanning accepteras | dödad | validate_staffing 2 av 1 |
| M45-M49 | staffing_validation:123-133 | restid, dygn, rast, 300, vila precis | dödade | boundary-tester på `_worker_sequences` |
| M50 | staffing_validation:37 | **hela arbetstidskontrollen avstängd** | ej | individuell bemanning med brott (fail) |
| M52 | staffing_validation:61 | förberedelse borta i facit | dödad | validate_staffing fel starttid |
| M53 | staffing_validation:109 | arbetspass kontrolleras inte | ej | vakt utanför pass |
| M54 | staffing_validation:36 | taskcoverage avstängd | dödad | saknad vakt |
| M56 | integrated_validation:177 | rumsintervall `<=` | dödad | pm 12:30 vs 12:29 |
| M59 | integrated_validation:149 | tentamen precis i pass | dödad | 240 vs 241 |
| M60 | integrated_validation:322 | kapacitet utanför teknisk status | ej | status vid kapacitetsbrott |
| M61 | integrated_validation:329 | antagande-pass räknas som verifierat | ej | business=not_verified vid assumption_only |
| M63 | integrated_validation:253 | kurskrock `<=` (tangerande) | dödad | 08-10 + 10-12 |
| M64 | integrated_validation:257 | **overifierad programdata -> PASS** | dödad | status vid program "missing" |
| M65 | integrated_validation:308 | trappa överskriden -> 0 vakter | dödad | 301 deltagare |
| M66-M68 | integrated_validation:295/239/210 | aggregerad prep, policylöst, digital explicit | ej | resp. regel |
| M69-M71, M73-M75 | integrated_inputs | ready-filter, kostnad/plats, scope-krav, digital mode, ort, längd | ej | adaptertest med flera rader/rum/orter |
| M78 | canonical_demand:182 | delgrupper summeras som max | dödad | 10+15=25 |
| M79, M81, M85 | canonical_demand | noll-deltagare, delgrupp utan aktivitet, ogiltig status | ej | negativa tester |
| M86 | linkage:10 | kurskodsmönster | dödad | 7 tecken ger inget |
| M89 | linkage:80 | starttid ur nyckeln | ej | samma kurs/datum olika tid |
| M91-M93 | normalize | å/ä/ö, tidsformat, datumformat `%Y-%d-%m` | ej | normaliseringstester |
| M95-M98 | optimizer_time | tidsfönster, nattpass, veckodag, kapacitetscheck | ej | tester på hela filen |
| M100, M101 | model_inputs | rumsskopad kapacitet, policyflagga | ej | register-/policytester |
| M109 | integrated_term:115 | CP-SAT: krockar bortkopplade | ej | CP-SAT-test samma kurs |

Dödade (38) av projektets sviten: bl.a. M02-M06 (kalender), M14, M25 (kapacitet avdras inte), M38-M41 (restid, segment, prep, closing), M51, M55, M57, M58, M62, M72, M76, M77, M80, M82-M84, M87, M88, M90, M94, M99, M102-M108, M110-M112.

## 3. Handräknade kontrollexempel (`handcalc.py`, 93 kontroller, `handcalc_results.json`)
Facit skrivet för hand före körning; kördes mot kopian (modulväg verifierad). Täcker bl.a.: trappa 50/51/150/151/300/301; tentamen precis i pass (240/241); helg/veckodag (2026-01-17 = lördag); ställtid 30 (pass 12:00/12:29 fel, 12:30 ok); kapacitet 20/20 och 21/20; delning 60 över 2x30; samma kurs/program ett pass (omöjligt) vs två pass; tangerande samma kurs; samma kurs två dagar; dygnsvila 660/659; rast 30/29 efter 300 min; 300/301 min; dygn 660/661; restid 30/29; arbetspass 450-1110 +-1; portföljval (billiga småsalar vs dyr personal -> stor sal, mål 8 respektive 13); Uppsala/Visby; 51 deltagare -> 2 vakter; validerarens gränser; kapacitet 10/10 vs 11/10; rumsintervall 12:30/12:29; delgruppssumma 10+15; restidskostnad 30 min x 7 öre = 210; täckningsmått.

**Avvikelser från handräknat facit (potentiella fel i koden):**
1. **H17, term_run.py:260.** Ett rum med 301 deltagare ger `ValueError` ("Bemanningstrappan täcker inte...") ur `required_staff` i stället för status "no_constructive_full_solution" med blockerande krav. Minimalt motexempel: ett behov på 301, ett rum med 400 platser, trappa som slutar på 300. Latent i verklig data (största rum 229), men bryter acceptanskriteriet att brist ska redovisas som status. (CP-SAT-sidan och validatorn hanterar trappan annorlunda: validatorn ger FAIL.)
2. **H20, integrated_validation.py:242.** `known` filtrerar på `course_code`. Två behov med samma `program_ids` men utan kurskod, samtidigt, ger `course_program_conflicts = not_evaluated` i stället för `fail`. Programkrockar utan kurskod kan alltså aldrig upptäckas. Latent: adaptern fyller aldrig `program_ids`.
3. **H27, integrated_inputs.py:46.** `plan_area = str(row.observed_cities)`: ett event med flera orter ger texten `Uppsala | Visby`, som inte matchar något rum; motorn svarar bara `no_constructive_full_solution` utan orsak. Samma rad: `building_id` (rad 67) faller tillbaka på `room_id`, eftersom `optimization_rooms.csv` saknar byggnadskolumn. Alltså räknas Bergsbrunnagatan sal 1 och sal 2 som olika byggnader, med 30 min restid, i alla verkliga körningar.
(H33 var ett fel i mitt eget facit, rättat: scen() har ställtid 0; ingen kodavvikelse.)

Övrigt verifierat korrekt: alla övriga 89 kontroller stämmer. Slumpmässig korskontroll (`crosscheck_cpsat.py`, 150 små instanser, seed 1): term_run:s girighet gav exakt samma målvärde som CP-SAT-optimum i 103 av 103 genomförbara fall, och båda var ogenomförbara i 47 fall (ingen missad lösning). Gäller bara små instanser (<=5 behov, <=4 rum, <=3 dagar, ett pass).

Oberoende omräkning av verklig körning (`realrun_check.py`, `runs/20261009T082035Z-...`, 1258 behov, 8 rum): täckning, kapacitet (max beläggning 100 %), ort, ett pass/dag, kurskrock, personalregler (egen kod), rumskostnad 60 900 000, personalkostnad 90 000 000, mål 150 900 000 och poolstorlek 18 stämmer med resultatfilen. Validatorn: teknisk = pass, verksamhet = not_verified (kurskrock not_evaluated).

## 4. Fel som sviten principiellt inte kan upptäcka
- Fel i dataunderlaget: efterfrågan = Ladoks `registered_count` (antagande), duration från bokad tid, kapacitet "aktuell publicerad, ej verifierad för perioden". Inget test kan avgöra om siffrorna är rätt.
- Gemensam modellering i motor och validerare: samma `StaffingPolicy`, samma slotgenerering (`generate_calendar_slots`), samma tolkning av förberedelse/avslut/ställtid. Validatorn "oberoende" i namn men importerar `required_staff` (staffing_validation), `generate_calendar_slots`, config-laddaren. Ett fel i kalendern (t.ex. helgfilter) ses likadant av båda. Dessutom har term_run och CP-SAT var sin kurskrockslogik (`term_rules.demands_conflict` används bara av CP-SAT).
- Adaptern fyller aldrig `program_ids`, `digital_requirement`, `allowed_pass_ids`, `available_slot_ids`. Reglerna är kodade men **aldrig exekverade på verklig data**; endast kurskod används.
- Scenariot har ETT pass "day" 08:00-18:00: det finns inget rum-flera-pass-per-dag i verkligheten att testa, och en sal får bara ett salstillfälle per dag. Kapacitetsbaslinjen är därmed en artefakt av passmodellen (inte testad mot faktiska bokningar).
- Verklig datavolym: alla tester har 1-5 behov. Portföljuppräkning är 2^n delmängder; 8 rum är 255, men inget test visar skalning. Inget prestandatest.
- Visby: det finns ett Visbyrum (60 platser) men inga Visbybehov i data; ingen körning med Visby i verklig data. Ortstestet är enbart syntetiskt (mitt H15).
- Ingen test av kapacitetsbaslinje mot historiska bokningar (jämförelse "modellens beläggning vs. verklig").
- Optimalitet: motorn är konstruktiv, inget bevis för optimum; min korskontroll täcker bara små fall.
- Skalfel i trappan (>300 per rum) och 18 vakter jämfört med verklig bemanning: ingen oberoende referens.

## 5. Vilka tester bör ersättas / nya testtyper
Ersätt:
- test_cost_model (konstant), test_integrated_config (antal >= 6), test_cli (utom felkoder), test_api (lägg på handräknat resultat: 1 behov 12 deltagare -> rum, datum, 1 vakt, kostnad 12x... exakt).
- test_model_inputs hårdkodade summor (1220/1179) -> test mot källfilen via oberoende parsning, eller markera som konfigurationsgolv.
- test_normalize och test_integrated_inputs -> flerradsfall med känt facit (flera orter, flera rum, rad-för-rad).
- test_staffing: byt "30 vs 15 min" mot gränsvärdesserier (+-1 min för varje regel).

Nya testtyper som en ny modell behöver:
1. Gränsvärdestester +-1 för varje hård regel (kapacitet, ställtid, pass, rast, 300, dygn, vila, restid, trappa).
2. Oberoende referensberäknare (enkel brute force som inte importerar projektet) för små instanser: genomförbarhet och minimikostnad, jämförd med motorn (som `crosscheck_cpsat.py`, men utan delad regelkod).
3. Oberoende validerare utan import av motorns policy/kalender; fail-fall för varje regel (särskilt individuell bemanning, programkrock, digital).
4. Mutationsgrind i CI på de hårda reglerna (mål: 0 överlevande icke-ekvivalenta).
5. Egenskapstester (Hypothesis): ingen lösning bryter validerare; täckning = efterfrågan; kostnadsmonotoni.
6. Verklig-data-regression: fastlagd körning (kontrollsumma av indata) med förväntade summor och med validerarens utlåtande; enkel kapacitetsbaslinje mot historiska bokningar.
7. Skal-/prestandatest på verklig volym (1258 behov, alla rum) och Visbytest med minst ett Visbybehov.
8. Data-kontrakt: fält som regler kräver (program, digital, byggnad) måste antingen finnas eller ge blockerande status, inte tyst `unknown`.

## 6. Återskapa
```
cd ...\audit\a5
python mutate.py                 # alla mutanter -> mutation_results.json (ca 25 min)
python mutate.py M16 M24         # urval
PYTHONPATH=%CD%\repo_copy\src python handcalc.py
python hand_vs_mut.py            # handräknade tester mot de överlevande
PYTHONPATH=%CD%\repo_copy\src python crosscheck_cpsat.py 1
python realrun_check.py
```
(python = C:\lokalt\tentalokaler\PoC\.venv\Scripts\python.exe)

## 7. Kunde inte verifiera
- Att att 100 % av riktiga `data/processed`-värden är rätt mot originalunderlaget (underlag är skrivskyddade, inte lästa).
- Frontend och packaging (inga tester).
- Fördjupad analys av optimizer_model.py (586 rader, äldre fixed-time-linjen): endast fyra mutanter i optimizer_time.
- Ekvivalens hos mutanterna är bedömd manuellt, inte bevisad.
