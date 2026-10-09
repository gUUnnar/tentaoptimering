# Målarkitektur och leveransplan, revision 3

**Datum:** 2026-10-09
**Status:** Beslutsunderlag för godkännande. Ingen produktionsimplementation är påbörjad.
**Ersätter:** revision 2. Beslut från användaren (B1-B6, F1-F4) är infogade.
**Underlag:** tidigare granskning samt nya analyser av `data/processed/` (bokningar 2025-09-01 till 2026-08-29, 8 466 rader; 1 525 Ladokaktiviteter; 1 283 behovsposter; 20 rumsposter), en AST-baserad beroendeanalys och engångsprov av CP-SAT (bilaga B, endast i scratchpad).
**Ej läst:** `Lokalt kollektivavtal tentamensvakter.pdf` är en skannad bild utan textlager. Ingen siffra i planen bygger på den.
**Rättelse mot revision 2:** Klostergatan 3 beskrevs som "700 bokade platser". Det var antalet placeringsrader. Klostergatan 3 är specialtentamenscentret (högst 30 platser per bokning, facilitetskapacitet 41) och ligger utanför omfattningen (särskilt stöd). Lokalanalysen i avsnitt 4 är omräknad.

---

## 1. Beslut som gäller

| # | Beslut |
|---|---|
| B1 | Alternativ B. Ingen migrering, ingen bakåtkompatibilitet. Ersatt kod raderas när ersättaren fungerar. Originaldata rörs aldrig. |
| B2 | Fem begrepp (Dataunderlag, Simulering, Förutsättning, Körning, Resultat), SQLite plus filer, en parameterkatalog, verifiering härleds. |
| B3 | Första leveransen: korrekt nuläge, därefter datumflexibilitet, veckodagspolicy, flexibilitet per tentamenstyp och efterfrågevariation. Optimerar inte total kostnad. |
| B4 | **Studentkrockar** begränsar inte optimeringen. Resultatvyn har en diskret fotnot: "Simuleringen tar inte hänsyn till individuella studenters eventuella tentamenskrockar." Antaganden och begränsningar visas tydligt men får inte dominera. Verktyget undersöker möjligheter, det godkänner inte ett schema. |
| B5 | **Lokaler:** inga lokaler uppfinns. Historiskt samtidigt platsbehov skiljs från den kända lokalportföljen. Saknad kapacitet är ett synligt datagap. |
| B6 | **Efterfrågan:** registrerade tentander är grundmått. Registrerade, bokade och närvarande platser blandas aldrig. |
| B7 | **Omfattning:** oavgjorda aktiviteter exkluderas inte automatiskt ur potentialbedömningen. Inläst, beräkningsbar och kvarstående gap redovisas skilda. |
| B8 | Platsnivåerna från optimeringen är **optimistiska undre gränser under angivna restriktioner**. Lokalrealisering och bemanning förväxlas inte med platsmåttet. |

---

## 2. Population: inläst, beräkningsbar, kvarstående gap (B7)

Överlappet mellan de 25 aktiviteterna med saknat värde och de 267 oavgjorda är fullständigt: de 25 är en delmängd. Ingen dubbelräkning av bortfall. Fördelningen av de 267 följer exakt orsakskoderna i `demand_scope.csv`:

| Nivå | Aktiviteter | Registrerade | Andel av inläst | Status |
|---|---:|---:|---:|---|
| **Inläst population** (Ladok) | 1 525 | 53 076 | 100 % | Källa |
| **Beräkningsbar, direkt** (entydig koppling till bokning, värde finns) | 1 258 | 46 698 | 88,0 % | Ingår i första leveransen |
| **Beräkningsbar under antagande** (flera Ladokaktiviteter delar samma bokade tentamenstillfälle: 170 aktiviteter i 82 tentamenstillfällen) | 170 | 5 038 | 9,5 % | Valbar nivå 2, se nedan |
| **Kvarstående gap: ingen bokning hittad** | 71 | 1 339 | 2,5 % | Datum och starttid finns i Ladok, längd och sal saknas |
| **Kvarstående gap: saknat värde** | 25 | 0 registrerade (värde saknas) | - | Bokning finns, deltagarantal saknas |
| **Kvarstående gap: ingen kandidatrelation** | 1 | 1 | <0,1 % | |

Kontrollsumma: 1 258 + 170 + 71 + 25 + 1 = 1 525; 46 698 + 5 038 + 1 339 + 1 = 53 076.

**Nivå 2 är beräkningsbar men inte säker.** Dessa 170 aktiviteter pekar på 82 bokade tentamenstillfällen (66 med två aktiviteter). Deltagarantalet per tillfälle ligger mellan största aktiviteten (3 583 platser) och summan (5 203). Stöd för "största aktiviteten" i datat: för entydiga tentor är registrerade tentander 72,6 % av bokade platser; för nivå 2 är *största aktiviteten* 73,2 % av bokade platser medan *summan* är 106 %. Mönstret är förenligt med att aktiviteterna (till exempel ordinarie och digital variant) till stor del avser samma deltagare. Det är ett antagande, inte ett faktum, och därför:
- Nivå 2 är en uttrycklig omfattningsparameter ("Inkludera tentor med flera aktiviteter: ingen / största aktivitet / summa"), standard *ingen*.
- Det är samma kod, samma restriktioner och samma efterfrågemått oavsett nivå; bara populationen skiljer.
- Resultatet redovisar potentialen för varje vald nivå och ett intervall (största ↔ summa) när nivå 2 används.

**Notering om digitala tentor:** 175 av de 267 oavgjorda är "Digital (omtentamen) (LIS)" och står för 4 581 av 6 378 oavgjorda registrerade. Den inkluderade populationen underrepresenterar därmed digitala tentor, vilket påverkar framtida analyser av digital andel.

Resultatsidan visar alltid raden "Inläst 1 525 · Beräkningsbar 1 258 (88 % av registrerade) · Kvarstående gap 267 (se detaljer)" och gör ingen slutsats om hela verksamheten av första nivån.

**Hemtentor och liknande.** I bokningarna ligger 115 "hemma|hemtenta"-rader (3 087 bokade platser under året, 1,1 % under terminen) som inte upptar lokal. Omfattningen bör klassa tentor efter *om de använder lokal*. Det är en fråga till verksamheten (F6).

---

## 3. Nuläge: beräkning och kontroll mot historiken

### 3.1 Definition

**Nuläge = samma kedja som en simulering, med alla flexibilitetsparametrar satta till "ingen".** Varje tentamen ligger på historiskt datum och historisk starttid. Samma population, samma efterfrågemått (registrerade), samma ställtid, samma lokalportfölj, samma bemanningsregler, samma kod. Nuläge är därmed en modell av det historiska schemat, inte historiens faktiska lokalanvändning.

Tre tydliga avgränsningar:
1. **Historiskt samtidigt platsbehov** (modellerat, registrerade tentander) är något annat än **faktiskt bokad kapacitet** (1,38 × registrerade) och **faktisk närvaro** (okänd). De redovisas som tre separata mått med definition. Bokade platser visas som kontext, aldrig som baslinje.
2. **Nuläges lokalrealisering** görs mot den kända lokalportföljen (avsnitt 6) och kan därför visa brist. Ingen lokal läggs till för att få Nuläge att gå ihop.
3. Oflyttbara tentor behåller sitt historiska tillfälle även när kalenderreglerna skulle förbjuda det. Kalenderregeln redovisas då `not_applicable` för dem.

### 3.2 Kontroll mot historiken

| Kontroll | Förväntat resultat (golden master mot lokalt underlag) |
|---|---|
| Varje tentamen i Nuläge har originaldatum och originalstart | 1 258 av 1 258 (egenskapstest, även syntetiskt) |
| Platstopp i Steg A | **1 604** platser, **2026-01-16**, identiskt med den oberoende `historical_capacity_check` |
| Totalt efterfrågade platser | 46 698 |
| Dagar där platsbehovet överstiger 1 179 (kända publicerade salar) | 4 av 73 dagar (16/1: 1 604; 15/1: 1 586; 14/1: 1 365; 13/1: 1 247) |
| Median av dagliga toppar | 312 |
| Fördelning per tentamenstyp | Ordinarie 721, Omtenta 497, Dugga 22, Hybrid 16, Hemtenta 2 |
| Veckodagar | Lördag 390, söndag 49, resten 819 |
| Abstrakt kontroll: summan av platstid i Nuläge = Σ (deltagare × längd) i källan | Exakt likhet |
| Jämförelse med faktisk bokning per dag (kontext) | Differensen redovisas, förklaras (bokade ≈ 1,38 × registrerade; ej identifierade rader) och används inte i beräkningen |

Kontrollerna körs på två nivåer: syntetiska fall i CI och lokal golden master mot det riktiga underlaget (`requires_local_data`).

---

## 4. Lokalbeståndet: vilka lokaler saknas i registret? (B5)

Bokningarna identifierar lokaler med bättre precision än registret, men kapaciteten saknas för några av dem. Under terminsfönstret (12 januari-31 mars 2026; 67 961 bokade platser):

| Plats | Andel av bokade platser | Registerstatus | Observerad största enskilda bokning | Största samtidiga bokning | Publicerad kapacitet |
|---|---:|---|---:|---:|---:|
| Bergsbrunnagatan 15 sal 2 | 24,3 % | Match, publicerad | 280 | 280 | 229 |
| Bergsbrunnagatan 15 sal 1 | 18,1 % | Match | 254 | 280 | 206 |
| Råbyvägen 95 sal 3 | 13,8 % | Match | 210 | 253 | 180 |
| Fyrislundsgatan 80 sal 1 | 12,1 % | Match | 200 | 218 | 200 |
| **Danmarksgatan 30** | 7,3 % | **Identifierad av adress, ingen kapacitet** | 344 | 344 | saknas |
| Råbyvägen 95 sal 2 | 6,7 % | Match | 150 | 160 | 128 |
| Råbyvägen 95 sal 1 | 4,2 % | Match | 127 | 127 | 96 |
| Klostergatan 3 (specialtentamenscenter) | 3,1 % | Match, facilitet | 30 | 42 | 41 (anläggning) |
| **Fyrishov hall D** | 2,9 % | **Match i register, ingen kapacitet** | 300 | 322 | saknas |
| **Fyrishov hall F** | 2,8 % | **Match i register, ingen kapacitet** | 260 | 330 | saknas |
| **Fyrishov hall E** | 2,7 % | **Match i register, ingen kapacitet** | 330 | 330 | saknas |
| Hemma (hemtenta) | 1,1 % | Ingen lokal | - | - | - |
| Fyrislundsgatan 80 (rum ej angivet) | 0,8 % | Ofullständig adress | 22 | 57 | saknas |

**Slutsatser.**
1. De åtta salar som har publicerad kapacitet täcker **68,3 %** av bokade platser under terminen. Cirka 16 % ligger i lokaler som *finns i bokningsdata men saknar kapacitetsuppgift*: Danmarksgatan 30 (7,3 %) och Fyrishov hall D, E, F (8,4 %). De är identifierade av adress och rumsnamn, inte okända. De saknas som kapacitetsuppgift i lokalregistret.
2. **Publicerad kapacitet är inte ett tillförlitligt tak för historiken.** I fem av åtta salar är den största enskilda bokningen större än den publicerade kapaciteten (till exempel Bergsbrunnagatan 15 sal 2: 280 mot 229; Råbyvägen 95 sal 3: 210 mot 180). Antingen har kapaciteten ändrats, eller så har salarna överbokats/använts med annan sittordning. Underlaget anger själv att publicerad kapacitet "inte är verifierad för bokningsperioden". Vilken kapacitet som är det fysiska taket är en öppen fråga (F2b) som direkt avgör om Nuläge kan realiseras.
3. Fyrishovhallarna visar samtidiga bokningar på 330 platser den 16 januari, den dag som också är Nulägets toppdag.

**Hantering i modellen (utan att uppfinna lokaler).** Lokalportföljen är en parameter med tre uttryckligen skilda nivåer. Varje nivå är en lista över verkliga, identifierade lokaler:

| Portfölj | Innehåll | Kapacitetsgrund |
|---|---|---|
| **P1: Publicerade salar** | De åtta salarna | Hämtat ur data (publicerad kapacitet, "ej verifierad för perioden") |
| **P2: P1 + identifierade lokaler med observerad minimikapacitet** | Dessutom Danmarksgatan 30, Fyrishov D/E/F | Observerad största samtidiga bokning, märkt *Observerad minimikapacitet, inte verifierad* |
| **P3: Egen lista** | Användaren väljer lokaler och kan skriva egen kapacitet (märks Antagande med motivering) | Experiment/Antagande |

Observerade minimikapaciteter beräknas av dataunderlagsbygget ur bokningarna; de är härledda, spårbara och ersätts när kapacitetsuppgift finns. Inget standardantagande om "extra lokal" finns.

**Kapacitetsbasen är en parameter:** *Publicerad kapacitet* eller *Observerad största bokning* (där observerad är större). Standard: publicerad, med synligt gap när historiken överskrider den.

Verksamhetsuppgifter som tar bort gapet: kapacitet och tillgänglighetskalender för Danmarksgatan 30 och Fyrishov, bekräftelse av salskapaciteter för perioden, och vilka av dessa som är långtidsdisponerade respektive externt hyrda.

---

## 5. CP-SAT-modellen: vad den tillämpar och vad som saknas

### 5.1 Tillämpas (steg A: tidsplacering)

| Restriktion | Typ | Parameter |
|---|---|---|
| Varje tentamen får exakt ett tillfälle (datum + starttid) | Hård | - |
| Tillfället ligger inom fönstret (tidigare/senare dagar) | Hård | `window.earlier_days`, `window.later_days` |
| Tillfället ligger på tillåten veckodag | Hård för flyttbara | `calendar.weekdays` |
| Tillfället ligger inte i spärrad period | Hård för flyttbara | `calendar.blocked_ranges` |
| Starttiden är en tillåten starttid (eller originalstart) | Hård för flyttbara | `calendar.start_times` |
| Endast valda tentamenstyper får flyttas, övriga ligger fast | Hård | `flex.movable_types` |
| Längd och deltagarantal ändras inte av placeringen; deltagarantal skalas av efterfrågevariationen | Fast | `demand.variation_pct`, `demand.rounding` |
| Samtidiga platser (aktiv tid = längd + ställtid) ≤ `C` vid varje tänkbar starttidpunkt per ort | Hård | `calendar.turnaround_minutes` |
| Tentor i samma kurs (kurskod) överlappar inte | Hård | - |
| Tentor i samma kurs behåller sin inbördes ordning (ordinarie före omtenta) | Hård, på som standard | `rules.keep_course_order` |
| Valfritt platstak: `C ≤ tak` | Hård | `objective.capacity_cap_seats` |

**Målfunktion (lexikografisk):** (1) minimera platstoppen `C` (eller, om platstak anges, uppfyll taket); (2) givet `C ≤ C*·(1 + tolerans)`, minimera antal flyttade tentor; (3) minimera sammanlagt flyttavstånd. Nuläget används som startlösning. Resultatet redovisar status, bästa gräns och gap.

### 5.2 Tillämpas inte (och redovisas som sådant)

| Saknas | Konsekvens | Hur det visas |
|---|---|---|
| Enskilda studenters och programs tentamenskrockar | Flyttar kan skapa krockar | Fotnot enligt B4 |
| Sals diskretisering: platser behandlas som ett delbart pool | Platsbehovet är en **undre gräns**; en verklig lokalplan kräver mer | Märkning "optimistisk undre gräns" + lokalrealisering (avsnitt 6) |
| Samlokalisering utan villkor: tentor får dela platser fritt | Dito | Dito |
| Salskalendrar och tillgänglighet | Lokaler antas fria alla tider | Begränsningar-panelen |
| Digital kompatibilitet per sal | Ingen digital prövning | Begränsningar-panelen |
| Intervall omtenta-ordinarie, fastställda tentamensperioder, kursslut | Fönstret är användarens val | Begränsningar-panelen (F10) |
| Bemanningstillgänglighet och kostnad | Ingår inte i steg A | Steg C redovisar efteråt |
| Kostnad | Målfunktionen är platser, inte kronor | Kostnadsprofilen är ett separat, märkt efterberäkning |
| Särskilt stöd, hemtentor | Utanför omfattning | Omfattningspanelen |

Dessa punkter redovisas i en hopfällbar panel "Förutsättningar och begränsningar", skild från nyckeltalen. På resultatsidan syns bara fotnoten om studentkrockar och en rad "Optimistisk undre gräns för platsbehov under angivna restriktioner."

---

## 6. Från platsbehov till realistiskt lokalbehov

Fyra nivåer, alltid skilda i resultatet och aldrig sammanblandade:

| Nivå | Vad | Beräkning | Statusord |
|---|---|---|---|
| **N0** | Platsbehov: minsta möjliga samtidiga platser under restriktionerna (steg A) | CP-SAT, optimalitetsgap | *Optimistisk undre gräns* |
| **N1** | Lokalrealisering för *det fasta schemat från steg A* mot vald lokalportfölj (P1/P2/P3) | Deterministisk packning med salstillfällen, gemensam start, ställtid, delning över högst `rooms.max_rooms_per_exam` salar | *Realiserbart / Brist X platser vid tid T / Kapacitet saknas* |
| **N2** | Bemanning av salstillfällena | Befintlig `plan_staffing` med trappa, pass, raster, vila, restid | Vaktpool, arbetad tid, restid, bomtid |
| **N3** | Gemensam optimering (schema väljs för att minska realiserade salstillfällen och bemanning) | Framtida steg, kräver kostnads- och kapacitetsdata | Ej i första leveransen |

**Regler.**
- N1 körs identiskt för Nuläge och simulering. Om kapacitet saknas (till exempel Nuläge mot P1: brist upp till 425 platser vid toppen) visas **bristen** som ett datagap, utan att något läggs till.
- Realiseringens kvalitet redovisas mot en undre gräns (kapacitetssortering): antal salar och salstillfällen som *minst* krävs.
- Platstaket i steg A gör det möjligt att ställa den omvända frågan: *"Vilka minsta förändringar krävs för att schemat ska rymmas inom kapaciteten X?"* Med taket satt till portföljens kapacitet blir N0 och N1 konsistenta.
- Resultatsidan visar N0 överst, därefter N1 under rubriken "Realisering i kända lokaler", därefter N2.

---

## 7. Användarreglage kopplade till verkliga beräkningsparametrar

Reglaget renderas ur katalogen. Varje katalogpost har `honored_by` (modul och funktion), en effektfixtur och ett förväntat utfall. En parameter som inte läses av motorn får inte finnas i katalogen som aktiv.

| Reglage (svensk etikett) | Katalog-id | Läses av | Effektfall (syntetiskt, kontrolleras i CI) |
|---|---|---|---|
| Tillåten tidigareläggning, dagar | `window.earlier_days` | `time_placement.occasions_for` | Två lika tentor, fönster 0 → topp 200; ±1 dag → topp 100 |
| Tillåten senareläggning, dagar | `window.later_days` | samma | Som ovan, asymmetriskt |
| Tillåtna veckodagar | `calendar.weekdays` | `occasions_for` | Lördagstenta flyttas till närmaste tillåtna dag |
| Spärrade perioder | `calendar.blocked_ranges` | `occasions_for` | Tenta i spärrad period flyttas ut |
| Tillåtna starttider | `calendar.start_times` | `occasions_for` | Tenta byter 14:00 till 08:00 när det sänker toppen |
| Flyttbara tentamenstyper | `flex.movable_types` | `occasions_for` | Endast omtenta flyttbar → ordinarie ligger kvar |
| Bevara ordning inom kurs | `rules.keep_course_order` | `time_placement.constraints` | Omtenta hamnar aldrig före ordinarie |
| Ställtid, minuter | `calendar.turnaround_minutes` | `time_placement.load_windows`, `room_realization` | 08:00-12:00 och 12:15-16:00: ställtid 30 → överlapp i belastning, 0 → inte |
| Efterfrågevariation, % | `demand.variation_pct` | `planning_problem.scale_demand` | 7 deltagare −10 % med uppåtrundning → 7; 1 deltagare −50 % → 1 |
| Avrundning | `demand.rounding` | samma | Uppåt/närmaste/neråt ger skilda tal |
| Optimeringsmål | `objective.mode` | `time_placement.objective` | Minimera platstopp ↔ klara givet platstak |
| Tolerans för platstopp, % | `objective.peak_tolerance_pct` | `time_placement.objective` | Tolerans > 0 minskar antal flyttar |
| Platstak | `objective.capacity_cap_seats` | `time_placement.constraints` | Tak under optimum → "kan inte uppfyllas" med bästa möjliga topp |
| Inkludera tentor med flera aktiviteter | `scope.multi_activity` | `planning_problem.build` | Ingen / största / summa ger 1 258 / 1 340 / 1 340 tentor och olika efterfrågan |
| Lokalportfölj | `rooms.portfolio` (P1/P2/P3) | `room_realization.rooms` | Portfölj utan tillräcklig kapacitet → brist redovisas |
| Kapacitetsbas | `rooms.capacity_basis` | `room_realization.rooms` | Publicerad ↔ observerad största bokning |
| Högsta antal salar per tentamen, tillåt delning | `rooms.max_rooms_per_exam` | `room_realization` | 1 → stor tenta utan sal ryms inte |
| Bemanningstrappa, arbetspass, raster, vila, restid, förberedelse, avslut | `staffing.*` | `staffing.plan_staffing` | Befintliga tester (`test_staffing`) |
| Beräkningstid, slumpfrö (avancerat) | `solver.*` | `time_placement.solve` | Samma frö → identiskt resultat |
| Kostnadsantaganden (årskostnad per plats och vakt) | `cost.*` | `result.cost_profile` | Endast "modellkostnad enligt antaganden" |

**Mekanismer som gör kopplingen verklig.**
1. Motorns parameterobjekt genereras ur katalogen. Motorn läser parametrar bara därigenom; ett statiskt test förbjuder andra konfigurationsläsningar (inga fritextsträngar, inga `.get("...")` på råa dictar).
2. Katalogtest: varje aktiv post har en effektfixtur. En post utan fixtur gör CI rött.
3. Frontend renderar kontroller ur `/api/parameterkatalog`. Inga handskrivna fält. Playwright-test: ändra ett reglage på syntetiskt underlag → begäran bär rätt id → resultatet ändras som katalogens effektfall säger.
4. Oanvända katalogposter upptäcks av täckningstest: en post vars värde aldrig påverkat någon motorväg under effekttesterna flaggas.

Parametrar som kraven nämner men som saknar motorstöd (digital andel, externhyra, ersättningslokaler, max skrivtid, årsfaktor, kostnadsstruktur) finns inte i appen. De listas i `docs/KRAVUPPFYLLNAD.md` som `saknas`.

---

## 8. Risk att modellen optimerar bort studenters och institutioners behov

Risken är verklig. Förprovet visar att fritt fönster och fria veckodagar kan pressa ned platstoppen från 1 604 till 435, vilket knappast är en genomförbar tentamensverksamhet. Modellen minimerar ett enda mått (samtidiga platser) och ser inte det som gör ett schema bra för dem som berörs.

| Risk | Hur den uppstår | Motåtgärd (utan att låta reservationer dominera) |
|---|---|---|
| Orimliga flyttar | Stora fönster ger stora vinster som inte är verklighetsnära | Standard = inget fönster. Resultatet visar en **flexibilitetskurva** (platstopp som funktion av fönster, till exempel 0, ±1, ±2, ±3, ±5, ±7) så att minskande avkastning syns. Användaren ser vilken frihet vinsten kräver |
| Onödiga flyttar | Många lösningar är optimala för toppen | Andra målnivån minimerar antal flyttade tentor; tolerans anges uttryckligen |
| Omtenta före ordinarie | Båda flyttbara och fönstret stort | Hård regel `rules.keep_course_order` (på som standard) |
| Tentor flyttas före kursslut | Kursavslut saknas i data | Flyttar *tidigareläggning* redovisas separat (antal och längd). Fönstrets tidigareläggning är en egen parameter |
| Orimliga tider och helgdagar | Fria veckodagar/starttider | Parametrarna är användarens val; påverkan redovisas (flyttar till helg, ändrad starttid) |
| Belastning på enskilda institutioner/kurser | Optimering fördelar flyttar ojämnt | Påverkansmått per institution (`org_code` finns i bokningarna) och per kurs: antal flyttade, andel flyttade, största flytt |
| Studentkrockar | Ej modellerade | Fotnot (B4); framtida data kan läggas till som hård regel |
| Platstopp ensamt som kvalitetsmått | Annat än platser ignoreras | Resultatet visar flyttlista, antal berörda kurser och institutioner, fördelning av flyttavstånd |
| Optimistisk bild | Platsmått antar delbar pool | Skild N1-realisering; text "optimistisk undre gräns" |
| Falsk precision | Gap, antaganden och ofullständig population | Population, gap och grund visas diskret men alltid |

Dessa är informations- och styrmått. De ändrar inte optimeringens frihet, men gör dess pris synligt. Studentkrock- och institutionsbehov kan senare bli hårda regler när data finns.

---

## 9. Arkitektur (fastställd) och komponentklassning

Arkitekturen från revision 2 gäller: fem begrepp, SQLite plus filer, en parameterkatalog, tjänstelager som både CLI och API använder, ett motorgränssnitt, fristående validerare, OpenAPI-genererade frontendtyper, tomt datakatalog vid start.

Motorns kedja: `PlanningProblem` → steg A (CP-SAT tidsplacering) → steg B (lokalrealisering mot portfölj) → steg C (bemanning) → resultatbyggare → validerare. Nuläge och simulering delar kedjan.

| Klass | Komponenter |
|---|---|
| **Behåll** | `loaders`, `normalize`, `validation`, `linkage`, `provenance`, `paths`, `staffing`, `staffing_validation` (regelkärna), `app_paths`, `directory_picker`, OR-Tools |
| **Bygg om** | `model_inputs` (bär historiskt datum, start, typ, kurskod och `org_code` vidare; bygger också observerade minimikapaciteter och nivå 2), `pipeline` (skriver ett Dataunderlag), `canonical_demand` (nivå 2 visar att delgrupp-/tentamenstillfälle-modellen behövs, se F8), `term_calendar` (tillfälle = datum + starttid), `term_rules`, `integrated_validation` (nya regler, ingen fritext), `cost_model`/`cost_comparison` (blir resultatmodellens kostnadsprofil), `job_manager` (persistens, förlopp, avbryt), `cli`, `desktop` (ledig port) |
| **Nytt** | Steg A, steg B, referenskedja och jämbarhetsnyckel, domän/lagring/tjänster, parameterkatalog, API, frontend |
| **Radera** | `optimizer_config/model/hint/validation`, `optimization_runs`, `optimizer_time` (efter flytt av `clock_minutes`, `duration_minutes`, `historical_capacity_check`), `term_run`, `integrated_runs`, `integrated_config`, `integrated_inputs`, `scenario_consistency`, `api`, `app_storage`, `config/parameters.toml`, `config/scenarios/*`, `frontend/src/**`, `reports/*`, historiska dokument |
| **Flytta till `tests/`** | `synthetic_integrated`, CP-SAT-delen av `integrated_term` (orakel) |

Bilaga A ger kompletterande detaljer.

---

## 10. Verifiering att den gamla koden försvinner

Verifieringen är mekanisk och körs i CI från första steget.

| # | Grind | Mekanism |
|---|---|---|
| R1 | Raderingsmanifest per PR | PR-beskrivningen listar "raderad fil → ersättare → bevis (test eller anrop)" |
| R2 | Gravstensfil | `tools/removed_symbols.txt` genereras ur `git diff --name-status` och AST av raderade filer. `tools/check_removed.py` söker igenom `src/`, `frontend/src/`, `docs/`, `config/`, `packaging/`, `README.md` och fallerar vid träff |
| R3 | Importavsaknad | Test: `importlib.util.find_spec` för varje raderad modul är `None` |
| R4 | Nåbarhet | AST-importgraf från produktionsingångar (API-app, CLI `main`, `desktop.main`): inga moduler utanför, utom uttryckligen listade under `tests/` |
| R5 | Död kod | `vulture` samt täckning från hela testsviten och E2E: inga produktionsmoduler med 0 % |
| R6 | Förbjudna termer | `scenario`, `legacy`, `optimizer_`, `integrated_`, `implemented_in_term_engine`, `unverified_replaceable` får inte finnas i `src/`, `frontend/src/`, OpenAPI eller dokument (med listad undantagsfil) |
| R7 | Ett API | OpenAPI-snapshot jämförs mot godkänd rutlista |
| R8 | Distribution | `tools/verify_clean_distribution.py` listar `dist/` mot en allowlist. Inga `config/scenarios`, inga fixturer, ingen `tests/` |
| R9 | Beroenden | `deptry` (Python) och `knip` (frontend) |
| R10 | Dokument | Länk- och sökvägskontroll; `FILOVERSIKT.md` jämförs mot `git ls-files` |
| R11 | Ren installation | Ny virtuell miljö från `pyproject.toml`, `npm ci`, paketerad `.exe` på ren Windowsprofil (Sandbox) med tom `%LOCALAPPDATA%` och utan nätverk. Playwright-flöde 1-8. Inga filer skrivs i installationsmappen |
| R12 | Filstorlek | `check_code_file_lengths.py` utökas till TS/TSX och radlängd |

Preliminär beroendeanalys (körd): äldre motor nås från kvarvarande kod bara via `integrated_inputs → optimizer_time → optimizer_config`. Tester ensamma använder `cost_model`, `synthetic_integrated`, `integrated_term.solve_integrated_term` och `canonical_demand.build_canonical_exam_demands`.

---

## 11. Första fungerande vertikala leveransen: resultat vi ska kunna uppnå och testa

**Syntetiska fall (körs alltid, CI).** Handräknade fall enligt bilaga C. Alla reglagens effektfall i avsnitt 7.

**Golden master mot lokalt underlag, population nivå 1 (1 258 tentor, 46 698 platser, ställtid 30, registrerade tentander).** Förprovets värden är acceptanskrav för steg A: implementationen ska uppnå samma optimum (eller, för fall som tidsbegränsas, ett värde mellan redovisad bästa lösning och bästa gräns) och förklara varje avvikelse.

| Fall | Förväntad platstopp | Anmärkning |
|---|---:|---|
| Nuläge | 1 604 (16 jan) | Oberoende kontroll |
| ±1 dag, alla veckodagar | 923 | |
| ±2 dagar, alla veckodagar | 721 | |
| ±3 dagar, alla veckodagar | 601 | |
| ±3 dagar, måndag-fredag | 916 | Helgpolicyns effekt: +315 |
| ±3 dagar + starttid 08/14, måndag-fredag | 846 | |
| Endast omtentor/övriga flyttbara, ±3 eller ±7 | 1 570 | Ordinarie ligger fast |
| Nuläge, efterfrågan −10 % (uppåt, minst 1) | 1 467 | Avrundningseffekt |
| ±3 dagar, måndag-fredag, −10 % | 834 | |
| Samma kurs: ordning bevarad | ≥ ovanstående (ny restriktion; värdet fastställs vid S1) | |

Förprovet saknade ordningsregeln. Värden med den ska fastställas och därefter ingå i golden master.

**Realisering (N1) och bemanning (N2), uppmätt först i S2 och därefter bevarat:**
- Nuläge mot P1: brist redovisas (högst 425 platser vid toppen; dagar med brist: 4).
- ±3 dagar, alla veckodagar (601) mot P1: realiseras eller bristen redovisas; antalet salstillfällen och vaktpool redovisas.
- Samma kedja, samma kod för Nuläge och simulering (instrumenteringstest).

**Jämförbarhet.** Jämförelse accepteras bara mellan körningar med samma population, efterfrågemått, lokalportfölj, bemanningsregler och ställtid (jämbarhetsnyckeln). Annars svarar API:t med vad som skiljer.

**Påverkansmått.** Antal och andel flyttade tentor, flyttavstånd, flyttar till helg, ändrad starttid, tidigareläggningar, fördelning per institution och kurs. Flexibilitetskurvan visas för fönstervärdena 0 till ±7.

**Valideringsregler.** Tillfälle inom fönster och regler; oflyttbara på original; efterfrågan omräknad från basvärden; platstopp omräknad oberoende; kurskrock och kursordning; kapacitet per sal och ort; bemanning; studentkrock `not_evaluated`. Regressionstest: ingen kombination av användarvärden kan göra krockregeln `pass` utan data.

**Det avgörande acceptanstestet (M1, utan UI, M2 med UI):** ändra veckodagspolicyn och fönstret → kör → få ett resultat som visar (a) befolkningsnivåer, (b) Nuläge och optimerat platsbehov med samma definition, (c) hur många tentor som flyttats och till var, (d) realisering mot kända lokaler med eventuell synlig brist, (e) vaktbehov, (f) antaganden och begränsningar i en panel och studentkrockfotnoten.

---

## 12. Utvecklingssteg

Egen gren `feature/omtag-simuleringsmodell`. Varje steg raderar det det ersätter. Varje PR anger vilket av användarstegen 1-8 den förbättrar och har ett test för det.

| Steg | Innehåll | Raderas | Tester | Acceptans |
|---|---|---|---|---|
| **S0** | Parameterkatalog v1, domänmodell, klickbar prototyp, `tools/inventory.py` med kapacitetsförteckning, golden master frysta | - | - | Katalog och prototyp godkända; en person utan programmeringsbakgrund genomför steg 1-8 i prototypen |
| **S1** | `PlanningProblem` (historiskt datum, start, typ, kurskod, institution, nivå 1/2), tillfällen, CP-SAT steg A med lexikografisk målfunktion, kursordning, platstak, Nuläge, nya valideringsregler, flexibilitetskurva | `optimizer_time` (efter flytt), `integrated_inputs` | Syntetiska fall; effektfall per aktiv parameter; Nuläge 1 604; golden master-tabellen; monotoni (simulering ≤ Nuläge); krockregression | Headless körning reproducerar tabellen i avsnitt 11 |
| **S2** | Steg B (lokalrealisering mot P1/P2/P3 med brist), steg C (bemanning), resultatmodell med påverkansmått, jämbarhetsnyckel och referenser, `CompareService` | `term_run`, `integrated_runs`, `integrated_config`, `scenario_consistency`, `cost_comparison` (ersätts) | Samma kod för Nuläge/simulering; brist utan uppfunna lokaler; jämförelse avvisar olika nycklar; undre gräns ≤ uppnått | **M1:** automatiserat test från ändrad veckodag/fönster till validerat, jämförbart resultat |
| **S3** | Domän, SQLite, tjänster, Dataunderlag (inkl. observerad minimikapacitet och nivå 2), persistent jobb med förlopp och avbryt | `app_storage`, `job_manager`, `config/parameters.toml`, `config/scenarios/*` | Skapa/kopiera/döp om/radera; inaktuell-markering; avbruten körning efter omstart; katalogtest | Åtta användaruppgifter via tjänstelagret |
| **S4** | API och CLI över tjänsterna | `api.py`, gamla CLI-kommandon, resterande `optimizer_*` | API-flöde 1-8 utan sökvägar; OpenAPI utan förbjudna termer | Identiskt resultat via CLI och API |
| **S5** | Frontend: skapa, förutsättningar, kör, resultat (nivåer, population, panel, fotnot), flexibilitetskurva, jämförelse | Hela `frontend/src/**` | Vitest, Playwright 1-8; textgranskning mot förbjudna termer | **M2:** testperson ändrar veckodagspolicy och fönster, förstår jämförelsen mot Nuläge |
| **S6** | Rensning enligt avsnitt 10, dokument, kravmatris, ren installation | Resterande historiska dokument, `reports/*` | R1-R12 | Alla grindar gröna |
| **S7** | Efter leverans 1: bemanning och realisering styr schemat (N3); externhyra; kostnadsstruktur | - | Orakeljämförelse | Egen plan |

Relativ storlek: S0 liten, S1 stor, S2 stor, S3 medel, S4 liten, S5 stor, S6 medel.

---

## 13. Ekonomi i första leveransen

| Kan beräknas | Förutsättning |
|---|---|
| Platsbehov, belastningskurva, antal dagar över given kapacitet | Data + valda parametrar |
| Lokalbehov i vald portfölj och synlig brist | Portföljens kapacitetsgrund |
| Salstillfällen, vaktpool, arbetad tid, restid, bomtid (separat, utan dubbelräkning) | Bemanningsregler (Antagande tills kollektivavtalet verifierats) |
| Modellkostnad enligt antaganden och dess skillnad mellan två jämförbara körningar | Valfria kostnadsantaganden, alltid märkta |

| Kan inte beräknas utan kostnadsdata |
|---|
| Teoretisk årlig potential i kronor (annualisering, faktisk hyra, avtal) |
| Verifierad realiserbar besparing (undvikbarhet, uppsägningstid, engångskostnader) |
| Externhyra och ersättningslokaler, personalkostnad per timme, kontraktsform |
| Differens mot internhyra (aldrig) |

Underlaget gäller en termin (12 jan-31 mar 2026). Årsvärden kräver antagen annualisering.

---

## 14. Funktioner efter underlagskrav

**A. Kan byggas med tillgängliga data:** Nuläge, datumfönster, veckodagspolicy, spärrade perioder, starttider, flexibilitet per tentamenstyp, kursordning, efterfrågevariation, platsbehov och belastningskurva, flexibilitetskurva, påverkansmått per kurs/institution, population och gap, observerade minimikapaciteter, kurskrock, realisering mot P1/P2.

**B. Kräver uttryckliga antaganden:** bemanningsregler (kollektivavtal ej läst), ställtid, avrundningsregel, nivå 2 (största aktivitet), kapacitetsbas, kostnadsproxyer.

**C. Kräver nya verksamhetsuppgifter:** kapacitet och kalender för Danmarksgatan 30 och Fyrishov; verifierade salskapaciteter för perioden; kurs-/studentöverlapp; tentamensperioder och omtentareglerna; digital kompatibilitet per sal; verklig närvaro; avtal och kostnadsdata; underlag för Visby (ingen efterfrågan i underlaget) och fler terminer; klassning av hemtentor och duggor.

---

## 15. Öppna frågor

| # | Fråga | Rekommendation |
|---|---|---|
| F2b | **Fysiskt kapacitetstak.** Publicerad kapacitet (ej verifierad) eller observerad största bokning? I fem av åtta salar överskrider bokningarna publicerad kapacitet | Standard publicerad, observerad som val; verifiera mot verksamheten |
| F4b | **Nivå 2.** Antagandet "största aktiviteten" som standard av eller på? | Av som standard, valbart, intervall redovisat |
| F5 | Avskrift av kollektivavtalet (skannat) | Verksamhetsägare/HR |
| F6 | Klassning av hemtentor, duggor, hybrid: tar de lokalplats? | Fråga verksamheten |
| F7 | Radering: hård radering med bekräftelse (visar vad som tas bort)? | Ja |
| F8 | Delgrupp-/tentamenstillfälle-modellen i `canonical_demand` behövs för nivå 2 | Behåll och koppla in |
| F9 | Kostnadsstruktur (fast/rörlig) | Avgörs i S7 |
| F10 | Tentamensperioder och omtentareglerna som realistiska standardfönster | Tills dess: inget standardfönster |
| F11 | Flexibilitetskurvans fönstervärden (0, 1, 2, 3, 5, 7) | Godkänn eller ändra |
| F12 | Institution som granskningsdimension (`org_code`) | Godkänn |

Studentkrockar (B4), extra lokaler (B5), efterfrågemått (B6) och omfattning (B7) är avgjorda.

---

## Bilaga A. Kodinventering

| Komponent | Klass | Anmärkning |
|---|---|---|
| `loaders`, `normalize`, `validation`, `linkage`, `provenance`, `paths`, `reporting` | Behåll (reporting: Dataunderlagets kvalitetssammanfattning) | Pipeline skriver idag globalt |
| `pipeline`, `model_inputs`, `canonical_demand` | Bygg om | Dataunderlag; historiskt datum/typ/institution; nivå 2; observerade minimikapaciteter |
| `term_calendar`, `term_rules` | Bygg om | Tillfälle = datum + starttid |
| `staffing`, `staffing_validation` | Behåll | `_staffing_tasks` flyttas ur `term_run` |
| `integrated_term` | Dela | Dataklasser → motorn; CP-SAT → `tests/` som orakel |
| `synthetic_integrated` | Flytta till `tests/` | |
| `integrated_inputs`, `term_run`, `integrated_runs`, `integrated_config`, `scenario_consistency` | Radera | Ersätts |
| `integrated_validation` | Bygg om | Läser inte `conflict_policy`, `program_conflict_data_status` eller antagandetext |
| `cost_model`, `cost_comparison` | Bygg om | Principen och testerna för spärren flyttas |
| `api`, `app_storage`, `job_manager` | Radera, ersätt | |
| `app_paths`, `desktop`, `directory_picker` | Behåll/justera | Ledig port, enkel-instans-lås |
| `cli` | Bygg om | Tre kommandon över tjänsterna |
| `optimizer_config`, `optimizer_model`, `optimizer_hint`, `optimizer_validation`, `optimization_runs` | Radera | Flytta först `_input_manifest` (hashar), parameterdiff |
| `optimizer_time` | Radera | Flytta först `clock_minutes`, `duration_minutes`, `historical_capacity_check` |
| `config/parameters.toml`, `config/scenarios/*` | Radera | `reference`, `flexible_start_60m` raderas; värden i `integrated_term_exploratory` kan bli mall-källa |
| `config/room_register.toml`, `config/source_files.toml` | Behåll | |
| `reports/*` | Radera ur Git | Genererat |
| `frontend/src/**` | Radera | Verktygskedjan behålls |
| Tester | `test_optimizer`: radera; `test_api`, `test_app_storage`, `test_cli`: ersätt; övriga behåll eller bygg om enligt komponent |
| Historiska dokument | Radera | `FORSTA_TERMSKORNING`, `GAP_ANALYS_…`, `KODGRANSKNING_…`, `Uppdrag_Claude_Codex_…`, `Slutsatser_…` |

## Bilaga B. Förprov (skiss, scratchpad, inte implementation)

Population nivå 1 (1 258 tentor), registrerade tentander, ställtid 30, utan studentkrockar, utan lokalbestånd, utan kursordning. Heltalsoptimum, CP-SAT, 8 trådar. **Värdena är optimistiska undre gränser under respektive restriktionsuppsättning.**

| Fall | Platstopp | Status | Tid |
|---|---:|---|---:|
| Nuläge | 1 604 | optimalt | <0,1 s |
| ±1 dag, alla dagar | 923 | optimalt | 0,4 s |
| ±2 dagar, alla dagar | 721 | optimalt | 0,6 s |
| ±3 dagar, alla dagar | 601 | optimalt | 0,7 s |
| ±3 dagar, mån-fre | 916 | optimalt | 2,6 s |
| ±3 dagar + starttid 08/14, mån-fre | 846 | optimalt | 15,5 s |
| ±7 dagar + starttid 08/14, mån-fre | 461 (gräns 459) | bästa funna | 40 s |
| ±14 dagar + starttid 08/14, mån-fre | 435 | optimalt | 33 s |
| Endast icke-ordinarie flyttbara, ±3/±7 | 1 570 | optimalt | <1 s |
| Nuläge, −10 % | 1 467 | optimalt | <0,1 s |
| ±3 dagar, mån-fre, −10 % | 834 | optimalt | 1,8 s |

## Bilaga C. Handräknade syntetiska fall

1. Två tentor, 100 platser, samma start, fönster 0 → 200; ±1 dag → 100.
2. Samma kurs, ±1 dag: överlappar aldrig; ordningen bevaras.
3. Lördagstenta, lördag förbjuden: flyttbar flyttas inom fönster; oflyttbar ligger kvar, kalenderregeln `not_applicable`.
4. Ställtid 30: 08:00-12:00 och 12:15-16:00 överlappar i belastning; 0 → gör det inte.
5. Efterfrågevariation: 7 deltagare −10 % uppåt → 7; 1 deltagare −50 % → 1; regeln står i frusen specifikation.
6. Kapacitet: topp 250, känd portfölj 200 → brist 50 redovisas, ingen lokal läggs till.
7. Bemanning: trappa 1/2/3 vid 50/150/300; 51 deltagare i en sal → 2 vakter; samlokaliserade tentor delar vakter.
8. Krockregression: inget användarvärde gör kurs-/programkrockregeln `pass` när dataunderlaget saknar programrelationer.
9. Orakel: små instanser löses av CP-SAT i `tests/` och av kedjan; platstoppen ska vara lika.
10. Platstak: tak under optimum ger "kan inte uppfyllas" med bästa möjliga topp; tak över optimum ger färre flyttar än optimum-läget.
