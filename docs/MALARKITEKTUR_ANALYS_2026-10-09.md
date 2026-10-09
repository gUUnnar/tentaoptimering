# Målarkitektur och leveransplan, revision 4 (S0 klar för granskning)

**Datum:** 2026-10-09
**Status:** S0 (inventering, beslutsarbete, prototyp) är genomfört. Ingen produktionskod är skriven; `tools/inventory.py` är ett utvecklingsverktyg. Implementationen (S1 och framåt) börjar först när S0-leveransen är granskad och godkänd.
**Grenen** `feature/omtag-simuleringsmodell` är skapad från `main`. Mappväljarimplementationen från `feature/source-directory-picker` följer inte med; funktionen byggs in i den nya applikationen som del av inläsning av dataunderlag.

## S0-leveransen (att granska)

| Leverans | Fil |
|---|---|
| **Användarupplevelse (klickbar prototyp, uppmätta värden)** | [docs/prototyp/index.html](prototyp/index.html) |
| **Kapacitetsförteckning** (varje funktion i dagens system: behåll, bygg om, ersätt, ta bort) | [KAPACITETSFORTECKNING.md](KAPACITETSFORTECKNING.md) |
| **Kravmatris** (varje krav: idag, efter första leveransen, bevis, datakrav) | [KRAVUPPFYLLNAD.md](KRAVUPPFYLLNAD.md) |
| Parameterkatalog v1 | [PARAMETERKATALOG.md](PARAMETERKATALOG.md) |
| Domänmodell | [DOMANMODELL.md](DOMANMODELL.md) |
| Dataanalys (population, delade tillfällen, hemtentor, institution, kapacitet, `canonical_demand`) | [DATAANALYS_S0.md](DATAANALYS_S0.md) |
| Analys av kollektivavtalet (läst, 9 sidor) | [ANALYS_KOLLEKTIVAVTAL.md](ANALYS_KOLLEKTIVAVTAL.md) |
| Inventeringsverktyg | `tools/inventory.py` |
| Kravspecifikation §11 (UI, experimentellt arbetsflöde, N-1…N-10) | [KONCEPTUELL_KRAVSPECIFIKATION.md](KONCEPTUELL_KRAVSPECIFIKATION.md) |

---

## 1. Beslut som gäller

| # | Beslut |
|---|---|
| B1 | Alternativ B. Ingen migrering, ingen bakåtkompatibilitet. Ersatt kod raderas när ersättaren fungerar. Originaldata rörs aldrig. |
| B2 | Fem begrepp, SQLite plus filer, en parameterkatalog, härledd verifiering. |
| B3 | Första leveransen: korrekt Nuläge, datumflexibilitet, veckodagspolicy, flexibilitet per tentamenstyp och efterfrågevariation. Jämförelse av resursbehov mot Nuläge med samma population, efterfrågedefinition och redovisade restriktioner. Total kostnad optimeras inte. |
| B4 | Studentkrockar begränsar inte optimeringen. En diskret fotnot räcker. Antaganden och begränsningar visas men dominerar inte. Verktyget undersöker möjligheter. |
| B5 | Inga lokaler uppfinns. Historiskt samtidigt platsbehov skiljs från känd lokalportfölj. Saknad kapacitet är ett synligt datagap. |
| B6 | Registrerade tentander är grundmått. Registrerade, bokade och närvarande platser blandas aldrig. |
| B7 | Oavgjorda aktiviteter exkluderas inte automatiskt ur potentialbedömningen. Inläst, beräkningsbar och kvarstående gap redovisas skilda. |
| B8 | Optimerade platsnivåer är optimistiska undre gränser under angivna restriktioner. Lokalrealisering och bemanning förväxlas inte med platsmåttet. |
| B9 | **Publicerad lokalkapacitet är preliminärt tak.** Avvikelser mot historiska bokningar undersöks och redovisas; historiskt bokat antal är inte verifierad fysisk kapacitet. Nuläget skiljer historisk efterfrågan och faktisk lokalrealisering. |
| B10 | **De 82 delade tillfällena ingår inte i huvudberäkningen** förrän en säker metod mot dubbelräkning finns. Omfattningen redovisas separat; analysen "största aktivitet mot summa" bevaras. |
| B11 | Kollektivavtalet är analyserat före användning; bara regler med uttryckligt stöd blir *Verifierade*. |
| B12 | Hemtentor belastar inte lokaler om ingen lokal används. Duggor bedöms efter bokning och examinationsform. |
| B13 | `canonical_demand` återanvänds endast om det är den enda vägen för att bilda tentamensbehov. Annars raderas det. |
| B14 | Flexibilitetskurvan är en analysfunktion; dagvärden är fritt justerbara. Förval begränsar inget. |
| B15 | Institution är granskningsdimension när datakopplingen är tillförlitlig (villkoret är uppfyllt på ordernivå). |

---

## 2. Vad S0 visade

| Fynd | Konsekvens | Dokument |
|---|---|---|
| Delade tillfällen: för olika kurskoder passar *summan* (kvot summa/bokat 1,01; största/bokat 0,34); för samma kurskod ligger *största aktiviteten* närmast referenskvoten (0,77 mot 0,73) men utfallet är inte avgörande | Metod inte säker → utanför huvudberäkning; intervall 3 583-5 203 platser redovisas | DATAANALYS §2 |
| `canonical_demand.build_canonical_exam_demands` är en strukturvalidator (en delgrupp äger ett antal, ingen dubbelräkning); används inte i produkten idag | Återanvänd som enda väg att bilda behov, annars radera | DATAANALYS §3 |
| Tre behov (94 platser) har bara hemma-placering; 22 duggor (1 432 platser) har lokalbokning | Regeln "behovet använder lokal" härleds ur bokningen | DATAANALYS §4 |
| `org_code` finns på alla 5 506 bokningsordrar, exakt en per order; 48 koder i huvudpopulationen; namn saknas | Granskning per institutionskod nu, namn när tabell finns | DATAANALYS §5 |
| 23 av 1 259 bokningar under terminen överstiger publicerad kapacitet | Redovisas som kvalitetsmått; publicerad kapacitet är tak | DATAANALYS §6 |
| Kollektivavtalet reglerar inte bemanning per sal, arbetspass eller restid. Verifierade regler: rast vid pass > 5 h, kortaste betalda pass 2 h, 39 h/vecka, begränsningsperiod 2 mån, ≤ 5 dagar, helgnorm ≤ 4 per period | Bara två regler blir Verifierade i första leveransen; övriga förblir Antagande | ANALYS_KOLLEKTIVAVTAL |
| De 25 med saknat värde ingår i de 267 oavgjorda | Ingen dubbelräkning | DATAANALYS §1 |
| Lokaler utan kapacitetsuppgift i registret men identifierade i bokningarna: Danmarksgatan 30, Fyrishov hall D–F (cirka 16 % av bokade platser) | Synligt datagap | DATAANALYS §6 |

---

## 3. Nuläge: beräkning och kontroll mot historiken

**Definition.** Nuläge är samma planeringskedja som en simulering med alla flexibilitetsparametrar avstängda. Varje tentamen ligger på historiskt datum och starttid. Populationen är den beräknabara populationen som använder lokal: **1 255 tentor, 46 604 registrerade tentander** (1 258 beräkningsbara minus tre hemma-tentor). Efterfrågemått, ställtid, lokalportfölj, bemanningsregler och kod är identiska med simuleringens.

**Tre skilda begrepp i resultatet.** (1) *Historisk efterfrågan*: modellerat samtidigt platsbehov. (2) *Känd lokalportfölj*: publicerad kapacitet, 1 179 platser i åtta salar. (3) *Faktisk lokalrealisering*: vad som bokades. Den tredje redovisas som kontext, inte som baslinje (se DATAANALYS §6).

**Kontroller mot historiken (golden master mot lokalt underlag, `requires_local_data`).**

| Kontroll | Förväntat |
|---|---|
| Varje tentamen i Nuläge har originaldatum och starttid | 1 255 av 1 255 (egenskapstest, även syntetiskt) |
| Platstopp, populationen som använder lokal | **1 586**, 2026-01-15 |
| Platstopp, alla 1 258 beräkningsbara behov (oberoende `historical_capacity_check`) | **1 604**, 2026-01-16. Skillnaden 18 platser är de tre hemma-tentorna |
| Registrerade tentander (lokal) / (alla beräkningsbara) | 46 604 / 46 698 |
| Dagar över 1 179 platser | 4 av 73; högst 407 platser över |
| Typfördelning (1 258) | Ordinarie 721, omtenta 497, dugga 22, hybrid 16, hemtenta 2 |
| Veckodagar (1 258) | Lördag 390, söndag 49, måndag-fredag 819 |
| Platstid i Nuläge = Σ (deltagare × längd) i källan | Exakt likhet |
| Faktiskt bokade platser jämförs per dag | Differens redovisas och förklaras (bokat ≈ 1,38 × registrerade); används inte i beräkningen |
| Monotoni | Simuleringens platstopp ≤ Nuläges |

---

## 4. Vad CP-SAT-modellen tillämpar och vad som saknas

**Tillämpas (steg A, tidsplacering):**

| Restriktion | Typ | Parameter |
|---|---|---|
| Varje tentamen får exakt ett tillfälle (datum + starttid) | Hård | - |
| Tillfälle inom fönstret (dagar tidigare/senare) | Hård | `window.*` |
| Flyttbar tentamen ligger på tillåten veckodag, även efter flytt; en flyttbar tentamen på otillåten dag måste flyttas | Hård | `calendar.weekdays` |
| Inte i spärrad period; tillåten starttid | Hård för flyttbara | `calendar.blocked_ranges`, `calendar.start_times` |
| Endast valda tentamenstyper får flyttas; övriga ligger på historiskt tillfälle | Hård | `flex.movable_types` |
| Samtidiga platser (längd + ställtid) ≤ `C` vid varje tänkbar starttidpunkt per ort | Hård | `calendar.turnaround_minutes` |
| Samma kurskod överlappar inte; ordningen mellan tentor i samma kurs bevaras | Hård | `rules.keep_course_order` |
| Valfritt platstak | Hård | `objective.capacity_cap_seats` |
| Längd och deltagarantal ändras inte av placeringen (antal skalas av efterfrågevariationen) | Fast | `demand.*` |

**Mål (lexikografiskt):** minimera platstoppen `C` (eller klara taket); givet `C ≤ C*·(1 + tolerans)` minimera antalet flyttade tentor; sedan flyttavstånd.

**Om fönstret är för litet.** Om flyttbara tentor ligger på otillåtna dagar utan tillåtet tillfälle inom fönstret får körningen status *kan inte uppfyllas* med orsak och antal berörda tentor, i stället för ett tyst resultat. Veckodagspolicy utan fönster påverkar ingenting; det visas som en kort anmärkning vid reglaget.

**Tillämpas inte (redovisas i panelen Förutsättningar och begränsningar):** studentkrockar (fotnot), diskreta salar och samlokaliseringsvillkor (platser är en gemensam pool; realisering i steg B), salskalendrar, digital kompatibilitet, tentamensperioder och omtentaintervall, kursslut, bemanning (steg C), kostnad, särskilt stöd, hemtentor, externhyra.

## 5. Från platsbehov till realistiskt lokalbehov

| Nivå | Vad | Beräkning | Statusord |
|---|---|---|---|
| N0 | Minsta samtidiga platsbehov under restriktionerna | CP-SAT, gap | Minsta platstopp |
| N1 | Realisering av det fasta schemat i vald lokalportfölj | Packning med salstillfällen, gemensam start, ställtid, delning över högst `rooms.max_rooms_per_exam` salar | Realiserbart / brist X platser vid tid T |
| N2 | Bemanning av salstillfällena | `plan_staffing` med trappa, pass, raster, vila, restid | Vaktpool, arbetad tid, restid, bomtid, betald tid |
| N3 | Schemat väljs för att minska realiserade salstillfällen och bemanning | Senare steg | - |

- N1 körs identiskt för Nuläge och simulering. Brist (Nuläge mot 1 179 platser: upp till 407) är ett **datagap**, inte något modellen fyller med antagna lokaler.
- Realiseringen redovisas mot en undre gräns (kapacitetssortering).
- Platstaket i steg A besvarar den omvända frågan: *"Hur få flyttar krävs för att schemat ryms inom X platser?"*
- Lokaler utan kapacitetsuppgift är inte alternativ förrän verksamheten angett kapacitet. Användaren kan lägga till en egen lokal med egen kapacitet (grund Experiment).

## 6. Reglage och parametrar

Fullständig katalog i [PARAMETERKATALOG.md](PARAMETERKATALOG.md). Principen: motorns parameterobjekt genereras ur katalogen; varje aktiv post har `honored_by` och ett effektfall som är ett automatiserat test; frontend ritar kontrollerna ur `/api/parameterkatalog` utan handskrivna fält. Parametrar utan motorstöd finns inte i appen utan i kravmatrisen.

## 7. Risk att optimera bort studenters och institutioners behov

Risken är verklig (till exempel gav ±14 dagar utan helger platstopp 435, vilket inte beskriver en genomförbar tentamensverksamhet; 435 är dessutom den största enskilda tentan). Prototypen och planen mildrar utan varningstext:

- Standard = inget fönster (en ny simulering är Nuläge).
- Andra målnivån minimerar antalet flyttade tentor; ordningen i samma kurs bevaras.
- **Påverkansmått** visas som vanliga nyckeltal: antal och andel flyttade tentor och tentander, flyttavstånd, tidigare/senare, till och från helg, per tentamenstyp, per institutionskod och kurs. Exempel (±3 dagar, bara vardagar): 503 av 1 255 tentor (40 %) måste flyttas för att ta bort helgtentorna och nå 911 platser; utan helgförbud räcker 112 flyttar för 598.
- **Flexibilitetskurvan** visar minskande avkastning och golvet (största enskilda tentan).
- Punkten *studentkrockar* hanteras med en fotnot, enligt B4.

**Textbudget i gränssnittet.** På resultatsidan finns högst: en fotnotsrad, en hopfälld panel "Förutsättningar och begränsningar" och en omfattningsrad med neutrala siffror. Inga bannrar, inga upprepade varningar. Måttens namn bär sin definition ("Minsta platstopp under valda förutsättningar").

## 8. Verifiering att den gamla koden försvinner

| # | Grind | Mekanism |
|---|---|---|
| R1 | Raderingsmanifest | Varje PR listar "raderad fil → ersättare → bevis" |
| R2 | Gravstensfil | `tools/removed_symbols.txt` genereras ur `git diff --name-status` + AST av raderade filer; kontroll söker igenom `src/`, `frontend/src/`, `docs/`, `config/`, `packaging/`, `README.md` |
| R3 | Importavsaknad | `find_spec` för varje raderad modul är `None` |
| R4 | Nåbarhet | `python tools/inventory.py`: inga moduler utan väg från API, CLI eller `desktop` utom listade testmoduler. Idag: `cost_model`, `synthetic_integrated` |
| R5 | Död kod | `vulture` + täckning från hela testsviten och E2E: inga produktionsmoduler med 0 % |
| R6 | Förbjudna termer | `scenario`, `legacy`, `optimizer_`, `integrated_`, `implemented_in_term_engine`, `unverified_replaceable` i `src/`, `frontend/src/`, OpenAPI, dokument |
| R7 | Ett API | OpenAPI-snapshot mot godkänd rutlista (idag 17 rutter ersätts) |
| R8 | Distribution | `tools/verify_clean_distribution.py` listar `dist/` mot allowlist |
| R9 | Beroenden | `deptry`, `knip` |
| R10 | Dokument | Länk- och sökvägskontroll; `FILOVERSIKT.md` mot `git ls-files` |
| R11 | Ren installation | Ny miljö, `npm ci`, paketerad `.exe` på ren Windowsprofil, tom `%LOCALAPPDATA%`, utan nätverk, E2E 1-8 |
| R12 | Filstorlek | `check_code_file_lengths.py` utökas till TS/TSX och radlängd |
| R13 | Kapacitetsförteckningen | Varje rad har en implementation eller en motiverad avveckling; "Flytta först"-funktioner har anropare och test |

---

## 9. Första vertikala leveransen: resultat vi ska kunna uppnå och testa

Uppmätt i ett förprov mot det verkliga underlaget (scratchpad, inte implementation). Population: 1 255 tentor, 46 604 tentander; ställtid 30; kursordning på; flyttbara tentor på otillåtna veckodagar måste flyttas. Värdena är optimistiska undre gränser och blir golden master för steg A (heltalsoptimum; mellan 0,1 och 36 sekunder).

| Fönster (±dagar) | Alla veckodagar | Måndag-fredag |
|---|---:|---:|
| 0 (Nuläge) | 1 586 | 1 586 (ingen flytt möjlig) |
| 1 | 917 | 1 434 |
| 2 | 717 | 1 238 |
| 3 | 598 | 911 |
| 4 | 513 | 717 |
| 5 | 449 | 598 |
| 7 | 435 | 502 |
| 10 | 435 | 435 |
| 14 | 435 | 435 |

Golvet 435 är den största enskilda tentan. Flyttar vid ±3 dagar: alla veckodagar 112 flyttade (97 ordinarie, 11 omtenta, 3 hybrid, 1 dugga; 47 flyttade till och 22 från helg); måndag-fredag 503 flyttade (110 ordinarie, 376 omtenta, 11 hybrid, 6 dugga; alla 439 helgtentor flyttas från helg). Antalet flyttar är bästa funna inom 60 sekunder.

**Acceptanstest för första leveransen.**
1. Nuläge: 1 586 platser (1 604 för 1 258 behov), 4 dagar över 1 179, varje tentamen på originaltillfälle.
2. Tabellens värden återskapas av steg A (samma optimum eller bästa funna med redovisat gap) för båda kolumnerna.
3. Efterfrågevariation −10 % med uppåtrundning ändrar platstoppen monotont och avrundningsregeln står i frusen specifikation.
4. Platstak under optimum ger *kan inte uppfyllas*; tak över optimum ger färre flyttar än optimum-läget.
5. Samma population, efterfrågedefinition och restriktioner i Nuläge och simulering (jämbarhetsnyckeln); jämförelse mellan olika nycklar avvisas med förklaring.
6. Realisering mot 1 179 platser: Nuläge redovisar brist, ±3 alla dagar (598) redovisas som realiserbart eller med brist.
7. Fristående validering: inga fritextfält styr regelstatus (regression G4); studentkrock `not_evaluated` med fotnot; kalenderregler `not_applicable` för oflyttbara.
8. Påverkansmått och flexibilitetskurva med fritt valda dagvärden.
9. Spårbarhet: varje körning har frusen specifikation, dataunderlagets hash, motorversion och frö; en ändring av simuleringen ändrar inte äldre körningar.
10. Avgörande acceptansfrågan: *ändra en förutsättning (till exempel veckodagar och fönster) → kör → få ett begripligt, korrekt och spårbart svar på hur platsbehov, lokalbehov och vaktbehov påverkas*, först headless (M1), därefter i användargränssnittet med en testperson (M2).

---

## 10. Genomförandesteg

Egen gren från `main`. Varje steg raderar det det ersätter. Varje PR anger vilket av användarstegen 1-8 den förbättrar och har ett test för det.

| Steg | Innehåll | Raderas | Tester | Acceptans |
|---|---|---|---|---|
| **S0** (klart för granskning) | Dokumenten och prototypen i tabellen överst; inventeringsverktyg; golden-master-värden registrerade | - | - | Du granskar prototypen och kapacitets- och kravmatrisen och godkänner fortsättning |
| **S1** | `PlanningProblem` (originaltillfälle, typ, kurskod, institution, `uses_room`), tillfällen, CP-SAT steg A med lexikografisk målfunktion, kursordning, platstak, diagnostik vid för litet fönster, Nuläge, flexibilitetskurva, nya valideringsregler; `canonical_demand` kopplas in som enda väg för behov (eller raderas) | `optimizer_time` (efter flytt), `integrated_inputs` | Syntetiska fall (bilaga B); effektfall per aktiv parameter; golden master (avsnitt 9); monotoni; krockregression | Headless körning återskapar avsnitt 9 |
| **S2** | Steg B (realisering, brist utan uppfunna lokaler), steg C (bemanning, betald tid), resultatmodell med påverkansmått, jämbarhetsnyckel och referenser, `CompareService` | `term_run`, `integrated_runs`, `integrated_config`, `scenario_consistency`, `cost_comparison` (ersätts) | Samma kod för Nuläge/simulering; brist utan lokaler som tillkommit; jämförelse avvisar olika nycklar; undre gräns ≤ uppnått | **M1:** automatiserat test från ändrad förutsättning till validerat, jämförbart resultat |
| **S3** | Domän, SQLite, tjänster, Dataunderlag (inkl. inbyggd mappväljare, populationsnivåer, kvalitetsvy), persistent jobb med förlopp och avbryt | `app_storage`, `job_manager`, `config/parameters.toml`, `config/scenarios/*`, `directory_picker` (omarbetas in) | Skapa/kopiera/döp om/radera; inaktuell-markering; avbruten körning; katalogtest | Åtta användaruppgifter via tjänstelagret |
| **S4** | API och CLI över tjänsterna | `api.py`, gamla CLI-kommandon, resterande `optimizer_*` | API-flöde 1-8; OpenAPI utan förbjudna termer | CLI och API ger samma resultat |
| **S5** | Frontend enligt prototypen | Hela `frontend/src/**` | Vitest, Playwright 1-8; textgranskning | **M2:** testperson ändrar förutsättning och förstår jämförelsen mot Nuläge |
| **S6** | Rensning (avsnitt 8), dokument, kravmatris, ren installation | Resterande historiska dokument, `reports/*` | R1-R13 | Alla grindar gröna |
| **S7** | Efter leverans 1: bemanning och realisering styr schemat; externhyra; kostnadsstruktur; helgnorm per vakt | - | Orakeljämförelse | Egen plan |

Relativ storlek: S0 klart; S1 stor, S2 stor, S3 medel, S4 liten, S5 stor, S6 medel.

---

## 11. Ekonomi i första leveransen

Kan beräknas: platsbehov, belastningskurva, antal dagar över given kapacitet, lokalbehov i vald portfölj och synlig brist, salstillfällen, vaktpool, arbetad tid, restid, bomtid och betald tid (utan dubbelräkning), samt modellkostnad enligt antaganden och dess skillnad mellan två *jämförbara* körningar (kostnadsvärden saknar förinställning och måste anges).

Kan inte beräknas utan kostnadsdata: teoretisk årlig potential i kronor, verifierad realiserbar besparing, externhyra och ersättningslokaler, personalkostnad i tid och bomtid, helgtillägg (avtalet om obekväm arbetstid saknas i underlaget), annualisering (underlaget är en termin). Differens mot internhyra beräknas aldrig.

## 12. Funktioner efter underlagskrav

**A, tillgängliga data:** Nuläge, datumfönster, veckodagspolicy, spärrade perioder, starttider, flexibilitet per tentamenstyp, kursordning, efterfrågevariation, platsbehov och belastning, flexibilitetskurva, påverkansmått, institution via kod, population och gap, realisering mot publicerade salar.
**B, antaganden:** ställtid, avrundning, fönster och policy, bemanningstrappa och pass, rastlängd, dygnsvila, restid, kostnadsproxyer.
**C, nya verksamhetsuppgifter:** kapacitet för Danmarksgatan 30 och Fyrishov D–F; verifierade salskapaciteter; student- eller programöverlapp; beslut om delade tillfällen; bemanningsregler per sal; centralt Villkorsavtal-T 4 kap. 5 §; avtal om obekväm arbetstid; anställningsform och lönenivåer; kod-till-namn för institutioner; tentamensperioder och omtentaintervall; digital kompatibilitet; verklig närvaro; fler terminer och Visby; avtals- och kostnadsdata.

## 13. Öppna frågor

| # | Fråga | Rekommendation |
|---|---|---|
| F1 | Ska första leveransen visa **Nuläge med brist** i lokaler (1 179 mot 1 586 som mest) som huvudbild, eller bara platsnivå? | Båda: platsnivå överst, realisering under, brist som datagap |
| F2 | Delade tillfällen: vem bekräftar om aktiviteterna i samma kurs (till exempel ordinarie och digital tentamen) är samma eller skilda deltagare? | Verksamhetsägare; tills dess utanför huvudberäkningen |
| F3 | `canonical_demand`: återanvänds som enda väg att bilda behov (rekommenderas) eller raderas? | Återanvänd i S1; radera annars |
| F4 | Radering: hård radering med bekräftelse (rekommenderas) eller papperskorg? | Hård med bekräftelse |
| F5 | Kod-till-namn för 48 institutionskoder | Ny uppgift från verksamheten |
| F6 | Bemanningsregler per sal och deltagarantal: källa? | Ny uppgift |
| F7 | Är vakterna anställda (omfattas av avtalet) eller timavlönade? | Ny uppgift; påverkar helgnorm och kostnad |
| F8 | Gränsen för *kan inte uppfyllas*: ska appen föreslå minsta fönster som gör en veckodagspolicy genomförbar? | Ja, som hjälptext vid felet |
| F9 | Vilka typer får vara flyttbara som standard? | Alla; fönstret är avstängt som standard |
| F10 | Tentamensperioder och omtentaintervall för realistiska standardfönster | Ny uppgift |

Besvarade: F2b (publicerad kapacitet), F4b (delade tillfällen utanför), F5 (avtalet analyserat), F6 (hemtentor/duggor), F8 (`canonical_demand`, beslut efter S1), F11 (kurvan fri), F12 (institution).

---

## Bilaga A. Kodinventering

Se [KAPACITETSFORTECKNING.md](KAPACITETSFORTECKNING.md). Sammanfattning: behåll datalager, bemanningsregler, bemanningskontroll och OR-Tools; bygg om `model_inputs`, `pipeline`, `term_calendar`, `term_rules`, valideringen, kostnadsspärren; ersätt `api`, `app_storage`, `job_manager`, frontend och parameterregistret; ta bort äldre motor, `term_run`, `integrated_runs`, `integrated_config`, `scenario_consistency`, `config/scenarios/*`, genererade rapporter och historiska dokument.

## Bilaga B. Syntetiska handräknade fall

1. Två tentor, 100 platser, samma start: fönster 0 → 200; ±1 dag → 100.
2. Samma kurs: aldrig överlapp; ordningen bevaras.
3. Lördagstenta, lördag förbjuden: flyttbar flyttas inom fönstret; fönster 0 ger *kan inte uppfyllas* med orsak; oflyttbar ligger kvar och kalenderregeln blir `not_applicable`.
4. Ställtid 30: 08:00-12:00 och 12:15-16:00 överlappar i belastning; ställtid 0 gör det inte.
5. Efterfrågevariation: 7 deltagare −10 % uppåt → 7; 1 deltagare −50 % → 1; regeln står i frusen specifikation.
6. Kapacitet: topp 250, känd portfölj 200 → brist 50 redovisas, ingen lokal läggs till.
7. Bemanning: trappa 1/2/3 vid 50/150/300; 51 deltagare i en sal → 2 vakter; samlokaliserade tentor delar vakter; pass under 120 minuter betalas som 120.
8. Krockregression: inget användarvärde gör kurs-/programkrockregeln `pass` när dataunderlaget saknar programrelationer.
9. Orakel: små instanser löses av CP-SAT i `tests/` och av kedjan; platstoppen ska vara lika.
10. Platstak: tak under optimum → *kan inte uppfyllas*; tak över → färre flyttar än optimum-läget.
11. Hemma-behov (bara hemma-placering) ingår inte i lokalbehov; dugga med lokalbokning ingår.
12. Flexibilitetskurva med dagvärden 4, 10 och 21 ger punkter exakt där; förvalen 0, 1, 2, 3, 5, 7 begränsar inget.
