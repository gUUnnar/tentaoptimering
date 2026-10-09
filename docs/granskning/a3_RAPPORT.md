# Revision A3: Vilka regler upprätthåller beräkningskärnan faktiskt?

Revisionsdatum 2026-10-09. Gren feature/omtag-simuleringsmodell. Repot är orört (git status rent före och efter). Alla skript och utdata ligger i `...\scratchpad\audit\a3\`.

Beteckningar: V = verifierat (reproducerbart belägg), M = motbevisat, O = osäkert.

## 0. Vad som faktiskt körs

Terminskörningen (CLI `optimize-term` och API `api.py:238`) går via `run_integrated_term` -> `run_first_term_schedule` (`term_run.py:39`). CP-SAT-modellen `integrated_term.solve_integrated_term` anropas inte av produktvägen (V: grep; den används bara i `tests/test_integrated_term.py`). Från `integrated_term.py` används endast dataklasserna. All text i `FORSTA_TERMSKORNING.md` om CP-SAT beskriver alltså inte det som körs. Dokumentet anger dessutom bemanningspool 3 och mål 75,9 Mkr-öre; dagens kod ger pool 18 och 150,9 Mö (V, körning nedan).

Metod som körs: för varje delmängd av Uppsala-rummen (127 av 255 delmängder; 8 rum, Visby-rummet filtreras bort av `term_run.py:56-58` eftersom ingen efterfrågan har ort Visby) görs en girig placering: tentor sorterade störst först (`term_run.py:115`), varje tenta läggs på det datum (`pass`) som har lägst deltagarsumma hittills (`:118`), delas över salar efter störst återstående kapacitet (`:136`). Därefter bemannas (`staffing.plan_staffing`). Lägsta `rumskostnad(använda rum) + 50 000 kr x vaktpool` vinner (`:67-71`).

## 1. Restriktionsmatris

Förkortningar: K = upprätthålls vid konstruktion, E = kontrolleras bara efteråt, D = bara dokumentation/konfiguration utan effekt.

| # | Regel/krav | K (fil:rad) | E | D / verkningslös | Belägg |
|---|---|---|---|---|---|
| 1 | Fysisk salkapacitet (absolut tak) | K: `term_run.py:105-108,131-137,153` (återstående platser per (pass,sal)) | `integrated_validation._capacity` | - | V: 0 överskridanden i 237 salstillfällen; max beläggning 100 % (`audit_result.out`). Beläggning 97 % i snitt: inga reservplatser |
| 2 | Alla tentander placeras (summa = deltagarantal) | K: `:132-148`, `:149-150` (None om ej plats) | `_coverage` | - | V: 1258/1258 tentor, inget seat-mismatch |
| 3 | Ort Uppsala/Visby skilda | K: `:56-58,116`, `term_rules.py:17` | `_location` | Visby-rummet kan aldrig väljas när all efterfrågan är Uppsala. Ingen Visbyefterfrågan finns (alla 1283 rader `observed_cities=Uppsala`) | V: 0 rader mot `uu-campus-gotland-b40`; syntetiskt test T3/T3b visar att Visbytenta bara hamnar i Visbysal. O: flervärdig `observed_cities` ("Uppsala; Visby") skulle ge infeasible, inte delning |
| 4 | Digital kompatibilitet | K-kod finns (`term_rules.py:21-23`) men **verkningslös** | `_digital_compatibility` (markeras assumption_only) | `integrated_inputs.py:46-53` sätter aldrig `digital_requirement` (alltid "unknown"); rum får `{"all"}` när läget börjar med `all_` (`:68`). Datan har `observed_digital_exam_values` Ja/Nej (813/470) som aldrig läses | V: 204 av 237 salstillfällen blandar digital (Ja) och icke-digital (Nej). V: syntetiskt T4 visar att regeln fungerar om `digital_requirement` sattes, men adaptern gör det inte |
| 5 | Samma kurs får inte överlappa | K: `:119-125,164-176` | `_course_program_conflicts` | - | V: 0 kurser med två tentor samma dag. Effekt: eftersom alla börjar 08:00 betyder "överlappar inte" i praktiken "olika dag" |
| 6 | Programkrockar | K-kod finns (`:170`) men **verkningslös** | `not_evaluated` | `program_ids` fylls aldrig av adaptern (grep: ingen tilldelning); `conflicts.policy` och `program_relation_data_status` läses men styr inget i konstruktionen | V: T9 visar att program_ids skulle respekteras om de fanns |
| 7 | Ställtid mellan salstillfällen i samma sal | K: `_room_is_free` `:179-197` | `_room_intervals` | **Verkningslös med nuvarande scenario**: det finns ett enda pass ("day" 08:00-18:00), så en sal har max ett tillfälle per dag (`:188` hoppar över samma slot) | V: 0 sal med >1 session per dag. T2 (två pass, syntetiskt) visar att kontrollen fungerar |
| 8 | Gemensam starttid i salstillfälle | K: av konstruktion, ett pass = en starttid | `_coverage` (en slot per tenta) | - | V: alla 237 tillfällen start 480 (08:00) |
| 9 | Tentor med olika längd i samma salstillfälle | Tillåtet; tillfällets längd = max | - | - | V: 216 av 237 tillfällen blandar längder, spridning upp till 360 min (en 1 h-tenta och en 6 h-tenta i samma sal). Kravdokumentet tillåter olika sluttider, så förenligt. Bemanning täcker max-längd |
| 10 | Tentamenslängd vs pass | K: `term_calendar.py:112` (start + längd <= latest_end) | `_calendar_pass_constraints` | - | V. Tenta längre än 600 min: ingen slot -> status `no_constructive_full_solution` (T6) |
| 11 | Veckodagar/perioder | K: `term_calendar.py:82-99` | `integrated_validation` (slot-id) | Scenariot tillåter 1-7 och en period som täcker hela fönstret | V: 177 tentor på söndag, 177 på lördag (28 % av alla) |
| 12 | Behålla ursprungligt schema vid liten nytta | **Saknas helt** | - | Kravspec §4 och AGENTS.md kriterium 2 | V: 1249 av 1258 tentor flyttade; mediandistans 2 dagar men kvartil -25/+30 dagar, max -75/+78; 934 flyttade >14 dagar |
| 13 | Ordning ordinarie -> omtenta / inom kurs | **Saknas** | - | Planerade modellen kräver `keep_course_order` | V: av 228 par där ordinarie låg före omtenta i originalet har 133 (58 %) omvänd ordning efter körningen. Ex. kurs 1GV004: ordinarie 16/1 -> 2/3, omtenta 31/1 -> 28/1 |
| 14 | Starttid | K: endast passens start | - | Original har 411 tentor 14:00 m.fl. | V: alla 1258 flyttas till 08:00. 103 originaltentor slutar efter 18:00 (alltså utanför passfönstret) |
| 15 | Rumstillgänglighet | K-kod (`term_rules.py:19`) | `_availability` (assumption_only) | `available_slot_ids` fylls aldrig (None); alla rum alltid lediga | V (grep) |
| 16 | Delning av tenta över salar | Tillåtet utan villkor (`:136-147`) | - | Ingen byggnadsgräns, ingen minsta andel, ingen `max_rooms_per_exam` | V: 13 tentor delas, alla över flera adresser (Bergsbrunnagatan + Fyrislundsgatan, 12 st; 3 rum, 1 st). Syntetiskt T5: 130 pers -> 100 + 30 i två byggnader ger 3 vakter |
| 17 | Bemanningstrappa 1/2/3 (50/150/300) | K: `staffing.required_staff` `:57-63`, `term_run.py:261` | `staffing_validation` | Trappan tillämpas per salstillfälle (deltagare i just den salen), inte per tenta | V: 237/237 täckta (egen kontroll, 0 underbemannade minuter). T7: sal >300 platser ger ValueError (krasch, inte infeasible-status) |
| 18 | `staff_per_room_session` | Verkningslös när `ladder` finns (`integrated_config.py:114-119`); används bara i `AggregateStaffing` som inte påverkar mål | - | Hela fältet `staff_per_room_session` och motsvarande assumption | V: T1: värde 1 vs 9 ger identiskt mål |
| 19 | `conflict_policy` | Läses (`integrated_config.py:84`) men styr inget i `term_run`; kurskrock gäller alltid | Valideraren läser strängen `same_course_hard_constraint` | Rent etikett | V: T1: policy="none" ger samma resultat |
| 20 | Arbetspass 07:30-18:30 | K: `staffing._fits_shift :79,161` | `staffing_validation` | Ett enda pass; delade pass kan inte uttryckas | V: 0 överträdelser (egen kontroll) |
| 21 | Prep/avslut 30+30 | K: `_expanded_tasks :106-107` | ja | - | V |
| 22 | Max sammanhängande 300 min + rast 30 | K: `_expanded_tasks :104,108` + `_can_assign :143-146` | ja | Se fel F4 (överkonservativ; reservdelen räknar resa som rast) | V: 0 överträdelser; CX1 visar onödig extravakt |
| 23 | Max dygn 660 min | K: `_can_assign :139-141` | ja | - | V: 0 överträdelser |
| 24 | Dygnsvila 660 min | K: `:132-135` | ja | Kontrolleras bara mot senaste uppdraget (korrekt eftersom sorterat) | V: 0 överträdelser; CX7 fungerar |
| 25 | Restid mellan byggnader | K: `:136-137`, `_travel_minutes` | ja | **Byggnad = sal**: `optimization_rooms.csv` saknar `building_id`, adaptern faller tillbaka på `room_id` (`integrated_inputs.py:67`) | V: 213 resor, 6 390 min, bland annat mellan Fyrislundsgatan 80 sal 1 och sal 2 om de låg i samma adress. I körningen används ändå bara 3 rum på tre adresser, så effekten är nu liten men fel vid andra portföljer. Resan prissätts 0 (`travel_cost_ore_per_minute=0`) och ingår inte i dygns-/sammanhängande tid |
| 26 | Veckovila / max dagar per vecka | **Saknas** | - | Kollektivavtal 2.2: "inte fler än fem dagar per vecka i genomsnitt" (Verifierad enligt `ANALYS_KOLLEKTIVAVTAL.md`) | V: vakter arbetar i snitt 6,4 dagar per ISO-vecka, 92 % av vakt-veckorna >5 dagar; längsta rad 37 dagar i följd; alla vakter arbetar samtliga 22 helgdagar (avtalet: helg bör vara <= 4 per period) |
| 27 | Kortaste betalda pass 2 h | **Saknas** | - | Kollektivavtal 2.2 (Verifierad) | V: 576 av 1383 vaktdagar har <120 min arbete (min 60) |
| 28 | Kostnad vakter | Poolstorlek x 50 000 kr | - | Kostnad ej kopplad till arbetade timmar (4 362 h över 18 vakter, 242 h per vakt) | V; O vilken kostnadsmodell som avses |
| 29 | Särskilt stöd, hemtentor, duggor | **Ingen hantering** | - | `observed_exam_types` och `observed_support_placed_max` ignoreras | V: 2 hemtentor och 22 duggor får salplats som vanliga tentor |
| 30 | Lokalbestånd/externhyra | Endast 8 publicerade rum (1 179 platser) | - | Originalets topp är 1 604 platser (2026-01-16); 5 dagar överstiger 1 119 Uppsalaplatser | V: `baseline_original.py`: 0 av 127 portföljer klarar originaldatum och -tider (även med 24 h-pass). Salsbeståndet är alltså inte det verkliga. Externhyra modelleras inte |
| 31 | Utnyttjande av andra terminer | - | - | Rumskostnaden är "per år" men bara jan-mars-efterfrågan är med; se O | O |

## 2. Resultat på verklig data (körning `20261009T121402Z-integrated_term_exploratory_2026`, 18,6 s)

* status constructive_feasible; mål 150 900 000 öre; rum 60,9 M (3 rum: Bergsbrunnagatan 15 sal 2, Fyrislundsgatan 80 sal 1, Råbyvägen 95 sal 3; 609 platser), vakter 18 st = 90 M, resa 0.
* Täckning: 1258/1258, summa deltagare per tenta exakt = efterfrågan, 0 kapacitetsöverskridanden, 0 samtidiga sessioner i samma sal, 0 Visby-placeringar, 0 ortsfel.
* Datum: alla 79 kalenderdagar används, varje dag exakt 3 salstillfällen (alla tre salar varje dag), 13-17 tentor och 591-592 deltagare per dag. Originalet: 1-68 tentor per dag på 73 dagar, 390 lördags- och 49 söndagstentor. Algoritmen planar alltså ut belastningen; det är inte ett kostnadsmål utan en bieffekt av `loads`-sorteringen (`term_run.py:118`).
* Veckodagar: 190/190/174/175/175/177/177 (mån-sön). Söndag är lika vanlig som måndag, trots att 4 % av originalet låg på söndag.
* Förskjutning mot originaldatum: 649 tidigare, 600 senare, 9 oförändrade. Kvartiler -25/-2/+30 dagar, spann -75..+78.
* Samma exam_event delas upp: 79 bokningar med flera Ladokaktiviteter hamnar på olika datum i samtliga 79 fall (delade tillfällen splittras).
* Delning: 12 tentor över 2 salar och 1 över 3; alla delningar går över olika byggnadsadresser.
* Rum/tentor per tillfälle: i snitt 5,4 olika tentor per salstillfälle (max 13) med blandade längder och blandad digital/pappersform.
* Känslighet (variantkörning, `run_variants.py`): bara mån-fre ger mål 212,3 M (5 rum, 26 vakter); mån-lör 178,9 M (4 rum, 22 vakter); alla veckodagar 150,9 M. Den "billiga" lösningen bygger alltså till stor del på söndags-/lördagstentor, en verksamhetsregel som är en ren konfigurationsstandard (`allowed_weekdays = 1..7`) och enligt kollektivavtalet kräver helgpersonal som arbetar i genomsnitt max fyra helger per period.

## 3. Bemanningsgranskning (staffing.py)

Egen oberoende kontroll av `staff_assignments.csv` (`audit_staff.py`, `audit_staff2.py`): inga överträdelser av de **konfigurerade** reglerna (pass, överlapp, 300 min, 660 min dygn, 660 min vila, resa) och full täckning minut för minut. Planen är individuellt genomförbar enligt scenariots regler. Men scenariots regler utelämnar avtalade krav (rad 26-27 ovan).

Motexempel (`cx_staffing.py`, utdata `cx_staffing.out`):

* F4 CX1 (överkonservativ, `staffing.py:143`): `continuous_start` är första uppdragets start den dagen, inte starten på det pågående blocket. En vakt som gjort 08-09, pausat 2 h och sedan gör 11-13 + 13-16 (sammanhängande 300 min, dygn 360) nekas; 2 vakter i stället för 1. Det överskattar poolen.
* CX2: resa räknas som rast (gap >= 30 min inkluderar de 30 min resan tar, `:144`) och ligger inte i dygns-/sammanhängande tid. Vakt som kör 300 min, reser 30 min och jobbar 300 min till godkänns (1 vakt). Beror på policyn; fel enligt de flesta tolkningar av arbetstid.
* CX3: 14 dagar i följd på 1 vakt accepteras; ingen veckovila och ingen max-dagar-regel.
* CX8: giriga valet `min(len(assignments), index)` (`:123`) gav pool = maxsamtidighet i konstruerat fall, ingen överskattning hittades där; i verklig körning är 18 = 2 x 9 samtidiga (3 salar x 3 vakter) vilket också är nedre gräns givet 300-minutersregeln och 360 min långa uppdrag. Så poolstorlek 18 är rimlig givet reglerna, men reglerna är olämpliga (360 min uppdrag delas i 300+60, vilket skapar 576 vaktdagar under 2 h).
* CX9: två rum med 10 min mellanrum och olika byggnadsid kräver 2 vakter (resan 30 min) -- korrekt mot sina data men data (byggnad = sal) är fel.
* CX10 / O: uppdrag som slutar efter midnatt accepteras av `_fits_shift` om passet tillåter det; `_rest_between` använder `datetime.replace(hour=...)` som kraschar för timme >= 24. Inget fall i dagens konfiguration (pass slutar 18:30). Ej provat med flerdagar.
* CX5: två vakter på samma uppgift blir olika personer (korrekt). Uppdrag över dygnsgräns och delade pass är inte möjliga att uttrycka (ett pass per dag).

## 4. term_run-granskning

* Kapacitet per (sal, pass): korrekt (`remaining`, `:105-108`, `:153`). Två samtidiga sessioner i en sal: omöjligt i nuvarande scenario (ett pass) och blockeras av `_room_is_free` annars (T2, verifierat syntetiskt). `_room_is_free` tar hänsyn till att en längre tenta förlänger ett befintligt salstillfälle över ett senare tillfälle.
* Girig algoritm: ingen backtracking. Om en tenta inte får plats returnerar `_schedule_portfolio` `None` och hela portföljen avvisas. Med 127 portföljer och 79 dagar/3 rum är det okej men det betyder att "billigaste portfölj" bara är billigast av portföljer där girigheten lyckas. Ingen undre gräns/gap. Resultatet kan därför vara dyrare än optimum men kan också dölja billigare portföljer (O).
* Rumsval: sorteras efter störst återstående kapacitet (`:136`), så små tentor hamnar i största salen först och stora tentor delas över byggnader i stället för att ligga i en sal (13 delningar).
* Måluppfyllelse mot kostnad: portföljens rumskostnad räknas på använda rum (`:67`), staff på pool x 50 000 kr. Ingen kostnad för vaktstunder, bomtid, resor (0), extern hyra eller administration; ingen preferens att behålla originaldatum.
* Bestämd tidsplanering: tentor i en kurs ska ha olika dag. Regeln är av konstruktion strängare än ett överlappskrav eftersom alla startar 08:00.
* Tillhörande ort: `relevant_rooms` filtrerar på ort som förekommer i efterfrågan.
* `integrated_validation` accepterar `digital_compatibility` och `room_availability` som "PASS med assumption_only"; det är konsekvent med AGENTS.md (business_status blir `not_verified`) men gör att en tekniskt grön körning innehåller 204 salstillfällen som blandar digital och icke-digital.

## 5. Vad den planerade nya modellen (MALARKITEKTUR_ANALYS §4-5) skulle upprätthålla respektive missa

Gäller steg A (CP-SAT på platstopp) plus N1/N2 realisering:

Upprätthålls: ett tillfälle per tenta; fönster dagar tidigare/senare (täpper hål 12); tillåten veckodag; spärrade perioder; tillåtna starttider (hål 14, delvis); endast valda tentamenstyper flyttas; samtidiga platser <= C (längd + ställtid); samma kurs överlappar inte; ordning inom kurs (hål 13); minst antal flyttade tentor (hål 12); hemtentor belastar inte lokal (B12, hål 29).

Missar enligt planen (uttryckligen "tillämpas inte"): digital kompatibilitet (hål 4: hamnar bara i en fotnot, och i N1 behövs en egen kontroll), programkrockar (B4 avstår medvetet), salskalendrar (15), diskreta salar i steg A (rumsrealisering först i N1), särskilt stöd, tentamensperioder och omtentaintervall, kursslut, bemanning i steg A, kostnad, externhyra.

Kvarstår i N1/N2 om `rooms.max_rooms_per_exam` används: byggnadsgräns vid delning (hål 16: planen nämner bara max antal salar, inte samma byggnad), byggnadsid (hål 25: `building_id` måste in i `optimization_rooms`), avtalsregler 2 h-pass/<=5 dagar/helger (hål 26-27; planen deklarerar dem som Antagande/Verifierad men "S7"), blandning av längder i en sal, ostrukturerad kostnad per vaktstund, salinventering (hål 30: planen kallar det datagap, vilket är rätt, men N1 kommer att rapportera "brist" 407 platser, inte en lösning).
Planen hanterar *inte* (och bör uttryckligen anges): att all deltagarmängd kan placeras i en pool av 8 rum på de 5 dagar där originalet kräver 1 604 platser. Att "undre gräns" ges i steg A är konsekvent med detta.

## 6. Återskapande

Alla kommandon från `C:\lokalt\tentalokaler\PoC`:

```powershell
$A='C:\Users\gunso745\AppData\Local\Temp\claude\C--lokalt-tentalokaler-PoC\b7d311db-b70e-4a23-b34f-c02537d53902\scratchpad\audit\a3'
.\.venv\Scripts\python.exe -B $A\run_engine.py          # kör motorn, skriver $A\runs\
.\.venv\Scripts\python.exe -B $A\audit_result.py        # placering: datum, salar, förskjutning, delning
.\.venv\Scripts\python.exe -B $A\audit2.py              # omtentaordning, byggnadsdelning, beläggning
.\.venv\Scripts\python.exe -B $A\audit_staff.py         # individuell vaktkontroll
.\.venv\Scripts\python.exe -B $A\audit_staff2.py        # avtalsregler (2 h, dagar per vecka, helger)
.\.venv\Scripts\python.exe -B $A\cx_staffing.py         # motexempel bemanning
.\.venv\Scripts\python.exe -B $A\cx_termrun.py          # motexempel placering (syntetiska)
.\.venv\Scripts\python.exe -B $A\baseline_original.py   # originaldatum+tider mot 7 Uppsalarum
.\.venv\Scripts\python.exe -B $A\orig_peak.py           # originalets platstopp
.\.venv\Scripts\python.exe -B $A\run_variants.py        # veckodagskänslighet
```

Anm: `audit_result.py` skriver `dd.pkl` som `audit2.py` läser. Utdata sparade som `*.out`.
