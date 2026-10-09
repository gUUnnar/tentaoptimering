# Modell- och kodrevision (sammanställning)

**Datum:** 2026-10-09. **Status:** S1 pausad, ingen produktionskod skriven. Sex oberoende granskare arbetade skrivskyddat. Fem lämnade slutrapport (`docs/granskning/a2…a6_RAPPORT.md`). Granskaren för problemformulering (a1) stoppades före slutrapport; dess delresultat nedan bygger på experimentloggar och är **ofullständiga**. Siffror i S0-dokumenten (`MALARKITEKTUR_ANALYS`, `DATAANALYS_S0`, `docs/prototyp`) ska betraktas som **ersatta av denna rapport** där de skiljer sig.

## 1. Fel i mina egna S0-underlag (måste rättas)

| Påstående i S0 | Rätt enligt revisionen | Källa |
|---|---|---|
| Känd kapacitet 1 179 platser | **1 119** (sju Uppsalasalar). Resten är rummet `uu-campus-gotland-b40` i Visby (60 platser, enligt registret först från VT 2027, aldrig observerat). Kommer in via `model_inputs._build_optimization_rooms` (ingen ort- eller datumprövning). Terminsmotorn filtrerar bort det på `plan_area`, men "dagar över kapacitet" ändras: 5 av 73 dagar, högst 467 över (inte 4 och 407) | a2, a6 |
| Bokat ≈ 1,38 × registrerade | **1,24**: `optimization_placements.csv` har 179 dubblettrader | a2 |
| 68,3 % av bokade platser i åtta salar | **79,3 %** i de sju salar med kapacitet (terminsfönstret) | a2 |
| "5 506 bokningsordrar" | 5 141 schemalagda tillfällen | a2 |
| ±3 alla dagar → 598 (−62 %) | Fönstret klipps inte till datafönstret (12 jan–31 mar): 34 tentor flyttas före 12 jan. **Klippt: 797 (−50 %)**. ±1: 1 032, ±2: 897, ±3 vardagar: 1 032 | a6 |
| 112 / 503 flyttade | Ej reproducerbara och ej bevisat minimum (119–125 respektive 502–506; nedre gräns 105/499). Får inte vara golden master | a6 |
| "mån–fre, N=0 = 1 586" | Tillstånd som bryter regeln (439 helgtentor ligger kvar) | a6 |
| "Optimala/undre gräns" för alla värden | Kurvpunkterna är bevisat optimala (LP-certifierade) **för förprovets modell**; modellen saknar studentkrockar, rumspackning, 267 oavgjorda och datafönstergränser | a6 |

## 2. Verifierat korrekt

- Datakedjan stämmer exakt: 1 525 → 1 258 → 267; 1 283 behovsposter; 46 698 / 46 604 registrerade; toppar 1 586 (15 jan, 1 255 behov) och 1 604 (16 jan, 1 258 behov). Manifest och determinism OK. 45 stickprov av Ladok↔bokning: alla korrekta (a2).
- Förprovets 18 kurvpunkter reproduceras med annan formulering; lösningarna uppfyller alla regler enligt eget kontrollskript (a6).
- Motorns täckning, salkapacitet per pass, ort och samma-kurs-regel stämmer; bemanningsplanen följer de konfigurerade reglerna (a3). Girig portföljmotor = CP-SAT-optimum i 103 av 103 genomförbara slumpade småfall (a5).
- Kostnadsjämförelsen beräknar ingen differens (a4).

## 3. Fel som måste rättas

**Data (a2):** teckenkodsfel i Ladok-xlsx (`loaders.py:94–97`; +1 behov, +8 personer); Visby-rum i `optimization_rooms` utan ortfilter; dubblettrader i placements; `latest_end_time=18:00` utesluter 104 behov som slutar senare; 79 samtentor (166 behov) behandlas som fristående och delas på olika dagar.
**Restriktioner (a3):** motorn bevarar inte ursprungsschemat (1 249 av 1 258 flyttas, spann −75…+78 dagar); 177+177 tentor på söndag/lördag; ordning ordinarie→omtenta omvänd i 58 % av paren; alla tentor på 08:00; digital kompatibilitet och programkrockar verkningslösa (`digital_requirement` och `program_ids` fylls aldrig); `staff_per_room_session` och `conflict_policy` saknar effekt; byggnad = sal (restid mellan salar i samma hus); delning över byggnader utan gräns; hemtentor/duggor får sal; avtalsregler saknas i bemanningen (576 av 1 383 vaktdagar under 2 h betald tid, 92 % av vakt-veckor över 5 dagar, alla vakter alla helger); `staffing.py:143–144` logikfel (överkonservativ kontinuerlig tid; restid räknas som rast); `required_staff` kastar `ValueError` vid sal över 300 platser; `docs/FORSTA_TERMSKORNING.md` stämmer inte med koden (pool 18, 150,9 Mö, inte 3 / 75,9 Mö).
**Eftervalidering (a4):** fritextfält (`program_relation_data_status="verified"`, rad 257) gör kurs-/programkrock till **pass** utan data; assumption-`status` släcker `assumption_only` för individuell bemanning; antagandekrav visas som `pass`; business-pass möjligt utan täckning av källpopulationen; validatorn kraschar på tom `assignments.csv` (ingen validering vid brist); litar på motorns `model_inputs.json` och `result.json` och delar kalender-/bemanningskod; missar tyst krympning, pool-inflation och manipulerade resultatfält.
**Jämförelser (a4):** `/api/runs/compare` jämför olika dataunderlag och partiella körningar utan varning; ingen dataunderlagshash eller motorversion i `result.json`; lease-baslinjen summerar alla 41 rader (inkl. 32 med giltighet 2026-12-01, förråd, P-platser).
**Resultatvy (a4):** visar aldrig omfattning, begränsningar, status eller gap; "Målfunktion … kr" utan märkning.
**Tester (a5):** 112 mutanter, **74 överlevde**; staffing-gränser, bemanningsvalidering (hela arbetstidskontrollen kan stängas av utan fel), programdata→PASS, adaptern och datumformat saknar skydd; ingen test mot verklig volym, Visby eller kapacitetsbaslinje.

## 4. Problemformulering och målfunktion (a1, ofullständig)

Mätt på verklig data (a1:s loggar; **ej slutgranskat**):
- **Peak-minimering är degenererad.** ±3 dagar: en godtycklig optimal lösning flyttar 1 043 tentor; med andra målnivån 114–117. Bara 10 av de flyttade tentorna låg på dagar som inte påverkade toppen. Efter optimeringen ligger de tio värsta dagarna alla på 598; **medianen av dagstopparna stiger från 312 till 445**, dvs. toppen jämnas ut genom att vanliga dagar belastas.
- **"Klara känd kapacitet" är en annan och mer relevant fråga:** för att toppen ska rymmas inom 1 119 krävs **11 flyttar** (bevisat optimalt), ≤1 000: 15, ≤897: 27, ≤800: 44, ≤700: 63, ≤627: 90, ≤598: 117. Att minimera toppen kostar alltså ~10× fler flyttar än att klara befintlig kapacitet.
- Lastvaraktighet: bara 5 dagar överstiger 1 119 (överskott sammanlagt 1 333 platsdagar); 38 dagar överstiger 300. Fast kapacitet dimensioneras av några få dagar, vilket talar för "klara kapacitet X" och för en inhyrningsregel (tak vid vilken n dagar överskrids) i stället för minsta möjliga topp.
- **Poolens optimum kan ge sämre verkligt utfall.** Toppveckan 12–18 jan, ±2 dagar, kapacitet 1,0×: original 171 vaktpass (nedre gräns 140), poolens optimum **218** (206), rumsmedvetet 211 (158); salstillfällen 65 → 86 → 91; poolens optimum hade fortfarande 4 platser överflöd (ej realiserbart). Vid kapacitet 1,5× försvinner skillnaden (157/155/154). Lösningarna är FEASIBLE med gap; ej bevisat.
- Vakttopp och platstopp infaller olika dagar (16 vs 15 jan; korrelation 0,86).
- Hel termin rumsmedvetet: ±1 löste överflödssteget optimalt på 228 s (0 överflöd, 455 flyttar) men vaktsteget stannade på 717 mot gräns 380 efter 300 s; ±2 hann inte klart. Hel termin gemensam modell är alltså **inte** hanterbar med den formuleringen på 5 minuter.

## 5. Otestat eller osäkert

Sann minsta vaktpool (18 är girigt, nedre gräns 9); Ladok-urvalet (täcker 1 171 av 1 473 tillfällen i fönstret, 85 % av bokade platser, så topparna underskattas); 267 oavgjordas påverkan; terminens verkliga gränser; student- och programkrockar; om restid är arbetstid; vilken kapacitet som är fysiskt tak; Boländerna-hyran saknar rumskoppling.

## 6. Bör ersättas

`term_run._schedule_portfolio` (girig, ingen originalbevarande); validatorns indata och regelstatus (läs hash-låst dataunderlag, aldrig fritext, ingen `pass` för antaganden); Ladok-inläsning från xlsx; `optimization_placements` (dubblettrader); `_build_optimization_rooms` (ort + tillgänglighetsdatum); `/api/runs/compare`; lease-baslinjen; ensam peak-minimering som huvudfråga; tester `test_cost_model`, `test_integrated_config`, `test_cli`, `test_api`, `test_normalize`, hårdkodade summor i `test_model_inputs`.

## 7. Grundläggande modellval som kräver beslut

1. Vad är huvudfrågan: *minsta möjliga platstopp* eller *minsta ingripande för att klara känd kapacitet* (plus inhyrning av toppdagar)? Revisionen pekar mot det senare.
2. Kapacitetsbaslinje för Uppsala: 1 119 publicerat / + Klostergatan / + beslutad kapacitet för Danmarksgatan 30 och Fyrishov / observerat max 2 158 (bevisat nyttjat, ej kapacitet). B40 ur underlaget tills Visby-efterfrågan finns?
3. Klipps fönstret till datafönstret? Är 12 jan terminens första tillåtna dag?
4. Samtentor: ett behov eller flera? Tvetydiga aktiviteter summeras per tillfälle?
5. Studentkrockar: fotnot (beslut B4) trots att AGENTS.md kräver kurs-/programkrockar som hård regel — bekräfta.
6. Ska `assumption_only` ge `pass`, `not_evaluated` eller en egen status? Ska validatorn läsa hash-låst dataunderlag?
7. Ska avtalsregler (2 h-pass, ≤5 dagar/vecka, helgnorm) vara hårda i bemanningen? Är restid arbetstid?
8. Bemanning och lokalrealisering i målfunktionen (gemensam modell) eller efterberäkning — mätt avvikelse enligt avsnitt 4.
9. Flyttantal som golden master: nej; använd intervall.

## 8. Vad som inte kunnat verifieras

a1 saknar slutrapport och hann inte klart med hel-termins rumsmedvetet fall (±2). Frontend kördes inte i webbläsare. Studentöverlapp, verklig salkalender/digital matris, sann optimalitet för bemanningen, juridisk tolkning av veckovila och kollektivavtalets tillämpning på timavlönade kunde inte prövas. Mutanternas ekvivalens är manuellt bedömd. Granskarnas fullständiga rapporter och skript ligger i sessionens scratchpad och är kopierade till `docs/granskning/` (a2–a6).
