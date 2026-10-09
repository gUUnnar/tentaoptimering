# Revision av förprovet (platstopp under flyttfönster) – A6

Alla skript och utdata ligger i samma mapp som den här filen. Repot är orört.
Förkortningar: alla = alla veckodagar tillåtna, mfr = måndag–fredag. N = fönster ±N dagar. Basfall = probe5.py:s semantik (population 1 255, ställtid 30 i belastningen, kursordning på, originaltillfälle tillåtet bara om dess veckodag är tillåten, ingen klippning av fönstret, starttid fast).

## 0. Metod

* Egen dataladdning (`common.py`, csv-modul, inte pandas). Populationen reproduceras: 1 255 tentor, 46 604 tentander. Alla 1 258: 46 698.
* Egen formulering (`model.py`): valfria intervall och `AddCumulative` på absolut minutaxel med C som kapacitet. Probe5 använder i stället kontrollpunkter vid starttider och en summa per punkt. Kursordning är kodad som parvisa förbud (BoolOr) i stället för T-variabler.
* Egen LP-relaxation (`lp.py`, GLOP, 15-minutersdiskretisering, utan kursordning) som nedre gräns.
* Eget kontrollskript (`check.py`): svepning över absolut tid, kontrollerar placering, fönster, veckodag, starttid, klippning och kursordning samt räknar toppbelastning.

## 1. Reproduktion av kurvan (uppgift 2)

Verifierat. Alla 18 punkter (9 N × 2 veckodagsregler) ger exakt samma värden i min formulering och i probe5 (`run1.json`).

* Varje enskild lösning har kontrollerats av `check.py`: toppbelastning lika med C och 0 regelbrott (`run4.json`, `run2.json`). Det gäller alla 16 punkter med N≥1, ±3-lösningarna med flyttminimering och probe5:s egna ±3-lösningar. Probe5:s lösningar kördes om ur dess egen kod och granskades med `check.py`: 598 och 911, 0 brott.
* Övre gräns är alltså bevisad genom konstruktion, oberoende av solvern.
* Nedre gräns är certifierad av LP-relaxationen (ceil(LP) = C) kombinerad med den analytiska gränsen max enskild tenta = 435 (`lp.json`):

| N | alla: LP | alla: C | mfr: LP | mfr: C |
|--:|--:|--:|--:|--:|
| 1 | 916,5 | 917 | 1 433,8 | 1 434 |
| 2 | 716,9 | 717 | 1 237,8 | 1 238 |
| 3 | 597,4 | 598 | 910,9 | 911 |
| 4 | 512,1 | 513 | 716,9 | 717 |
| 5 | 448,1 | 449 | 597,4 | 598 |
| 7 | 358,5 → max(.,435)=435 | 435 | 501,1 | 502 |
| 10 | 290,6 → 435 | 435 | 410,2 → 435 | 435 |
| 14 | 268,2 → 435 | 435 | 372,0 → 435 | 435 |

* Alla 18 värden är därför bevisat optimala för modellen, och LP-gränsen gäller även utan kursordning. Kursordning påverkar C inte alls i någon testad punkt (se avsnitt 4).
* "OPTIMAL" i loggen är riktigt. `BestObjectiveBound` är lika med målet och bevisar optimum i heltalsmodellen. "Bound" är solverns bästa nedre gräns. Det är inte en "teoretisk undre gräns" i verksamhetsmening.
* Nuläge 1 586 (2026-01-15) verifierat med egen svepning. 1 604 (2026-01-16) för 1 258 verifierat. Dagsvärdena i `orig_perday.json` stämmer: 0 av 73 avviker.

## 2. Kodgranskning av probe5.py (och probe3.py)

| # | Rad | Fynd | Status |
|---|---|---|---|
| K1 | probe5:9 | Populationen tar bort bara tentor vars samtliga placeringar är "hemma" (3 st, 94 platser). De 25 behoven med `missing_configured_demand_value` är utanför (`ready_provisional…`-filtret, rad 5) och inget behov med oavgjord deltagarbild (267 av 1 525 aktiviteter, varav 175 digitala i LIS) ingår. Belastningen är därför en undre skattning av verklig belastning. | Verifierat; storlek okänd |
| K2 | probe5:23 | Originaltillfället tillåts bara om dess veckodag är tillåten (N>0). Probe3 hade det alltid tillåtet. Oförenliga semantiker mellan filerna. Effekt: ±3 mfr 911 → 900 om originalet alltid tillåts (se tabell). I kolumnen mfr är dessutom raden "0 (Nuläge)" = 1 586 ett tillstånd som bryter den veckodagsregel kolumnen representerar (439 helgtentor ligger kvar). | Verifierat |
| K3 | probe5:21–22 | Fönstret klipps inte till terminen. Tentor flyttas till 9–11 jan, före första originaldatum 12 jan. Det är det största enskilda modellvalet i resultatet (avsnitt 4). Av ±3 alla-lösningen har 34 tentor (3 436 tentander) lagts före 12 jan, bl.a. på lör–sön 10–11 jan. Toppen i lösningen ligger på 2026-01-11 08:00 (söndag). | Verifierat |
| K4 | probe5:33–34 | Kontrollpunkter bara vid starttider: **tillräckligt**. Belastningen är styckvis konstant och ökar bara vid start, så maximum antas vid en start. Min cumulative-formulering och svepning ger samma värden. Intervallet [start, start+längd+ställtid) är halvöppet och konsekvent. Inga tentor korsar midnatt (senaste slut 21:30). | Verifierat |
| K5 | probe5:33 | `if len(terms)>0` är harmlöst. Kontrollpunkterna är unionen av alla alternativas starter (överskott, ej fel). Kvadratisk uppbyggnad, men inte ett korrekthetsfel. | Verifierat |
| K6 | probe5:39–41 | Kursordning: konsekutiva par efter (originaldatum, starttid), T[a]+dur[a] ≤ T[b]. Ordinaltalet toordinal-739000 ligger inom domänen 0..10^7 (≈ 888 000–900 000 för 2026). Inget gap mellan ordinarie och omtenta, inga duggor undantagna. Alla tentor i samma kurskod (även olika delmoment/tentamenskoder) tvingas i originalordning. Parvisa originalöverlapp: inga (nuläget är genomförbart med N=0). Kursordning ändrar aldrig C i testade punkter. | Verifierat; semantiskt svag |
| K7 | probe5:44–45 | Hintet är originalet. Det är genomförbart för stage 1 (Nuläge) men inte för stage 2 (C ≤ c1). Stage 2 startar utan genomförbar startlösning. Därför är antalet flyttar en heuristik. | Verifierat (se K8) |
| K8 | probe5:50–57 | Stage 2 kör 60 s och rapporterar sista lösningen som "bästa funna". Reproducerbarhet: ±3 alla 112 (originalkörning), 119 (omkörning av probe5), 125 (min körning, nedre gräns 105). ±3 mfr 503 / 502 / 506 (nedre gräns 499). ±1 alla 99 (OPTIMAL, bevisat). Alla flyttsiffror är övre gränser med osäkerhet, inte golden master. | Motbevisat som exakt tal |
| K9 | probe5:92–97 | "Flyttad" = tillfället (datum, starttid) skiljer från originalet. Helg räknas via isoweekday ≥ 6. Räkningen stämmer med lösningen (probe5.json: from_weekend 439 = 390 lör + 49 sön). `moved_by_type`-räknar tentor, inte tentamenstillfällen: 79 tentamenstillfällen delas av 166 aktiviteter (K10). | Verifierat |
| K10 | probe5:12 | En tenta = en Ladok-aktivitet. 79 tentamenstillfällen (166 aktiviteter) består av flera aktiviteter med gemensam sal och tid. Probe5 tillåter att dessa delas upp. Test med aktiviteter som grupperas per tillfälle ger identiska C (alla 6 testade punkter). Effekten på flyttantalet kvarstår (en delad flytt räknas flera gånger). | Verifierat (C), antalseffekt ej mätt |
| K11 | probe5:11 | Längd = slut − start ur `scheduled_time`; `booking_start_time` är lika med start i 100 % av raderna. Ställtid 30 min läggs i belastningsintervallet och inte i kursordningen. Starttid i originalet: 08:00 (785), 14:00 (411), övriga 59. | Verifierat |
| K12 | probe5:15 | `tl=40` i kurvan och `tl=60` i stage 2. Alla 18 kurvpunkter blev OPTIMAL inom 40 s. | Verifierat |

Övrigt:

* Probe3 saknades som slutlig källa (inga loggar sparade). Dess siffror (t.ex. "±7 d + pass 08/14") används inte i dokumenten. De dokumenterade siffrorna kommer från probe5 och reproduceras.
* Belastningsmåttet är registrerade tentander (`registered_count`), inte bokade platser (≈1,38 gånger fler, enligt DATAANALYS). Det är ett definitionsval, inte ett fel. Skalning ×1,38 (uppåtrundning per tenta) ger Nuläge 2 203 och ±3 alla 832 (−62 %, samma relativa minskning). Se tabell.

## 3. Analytiska nedre gränser (uppgift 3)

* Största enskilda tentan: `ladok-001216`, 435 tentander, 300 min, 2026-03-20 (fredag). 435 är en giltig nedre gräns för alla N. Den uppnås av heltalslösningen för N≥7 (alla) och N≥10 (mfr), med fönster utan klippning. Ingen starkare analytisk gräns finns i just dessa fall, eftersom gränsen uppnås.
* Areagräns (totala platsminuter 13,19 Mmin = 219 851 platstimmar): 116 platser i medel över 24 h × 79 dagar, 242 över 79 dagar × 11,5 h, 335 över 57 vardagar × 11,5 h. Alla svagare än 435. Areagränsen är alltså inte styrande.
* LP-relaxationen (avsnitt 1) är starkare än area för N≤5 respektive N≤7 (mfr) och ger C inom <1 plats. Gränsen blir bindande först när heltalsegenskapen (435) tar över.
* Enkel strukturgräns: för N=1 mfr måste alla lördagens tentor till fredagen före. Maxlördag (2026-01-17) har egen toppbelastning 980. Gränsen 980 < 1 434, så den förklarar inte siffran fullt ut. Kedjeeffekter (fredag ↔ torsdag ↔ måndag) tar resten.
* 435 som "golv" är korrekt men är **inte en tolkningsbar golvnivå för verksamheten**. Det är den punkt där inga två stora tentor behöver överlappa i tid över 11 veckor, med fria dagar utanför terminen.

## 4. Känslighet för modellval (uppgift 4)

Platstopp C. Alla värden OPTIMAL om inget annat anges (`run3.json`, `run3b.json`). Δ anges mot basfallet.

| Variant | ±1 alla | ±2 alla | ±3 alla | ±3 mfr | ±14 alla | ±14 mfr |
|---|--:|--:|--:|--:|--:|--:|
| Basfall (probe5) | 917 | 717 | 598 | 911 | 435 | 435 |
| Ställtid 0 (= turnaround ej i belastningen) | 917 | 717 | 598 | 911 | 435 | 435 |
| Ställtid 60 | 917 | 717 | 598 | 911 | 435 | 435 |
| Originaltillfälle alltid tillåtet | 917 | 717 | 598 | **900** | 435 | 435 |
| **Fönster klippt till 12 jan–31 mar** | **1 032** | **897** | **797** | **1 032** | 435 | **502** |
| Tentor får byta starttid (08/14, slut ≤19:30) | 844 | 671 (gap 2) | 558 (gap 1) | 844 | 435 | 435 |
| Kursordning av | 917 | 717 | 598 | 911 | 435 | 435 |
| Tentamenstillfälle grupperat (en beslutsenhet) | 917 | 717 | 598 | 911 | 435 | 435 |
| Population 1 258 (hemma-tentor med) | 923 | 721 | 601 | 916 | 435 | 435 |
| Platser ×1,38 (bokade/registrerade) | 1 276 | 998 | 832 | 1 268 | 601 | 601 |
| Klippt + originaltillfälle + grupperat | 1 032 | 897 | 797 | 1 032 | 435 | 449 |
| Klippt + byt starttid | 984 | 844 | 744 (gap 1) | 984 | 435 | – |

Slutsatser av tabellen:

1. **Det avgörande modellvalet är klippningen av fönstret.** Fönstret i basfallet sträcker sig utanför datafönstret 12 jan–31 mar, där veckan 12–16 jan är toppen (1 162–1 586). Med klippning blir ±3 alla 797 i stället för 598 (+33 %). Minskningen mot Nuläge är −50 % i stället för −62 %. Vid ±1 är det 1 032 i stället för 917 (+12,5 %). Klippt ±3 mfr = klippt ±1 mfr = 1 032 (samma blockerande vecka).
2. Ställtid, kursordning, grupperat tentamenstillfälle och inklusive hemma-tentor ändrar praktiskt taget inget (≤ 5 platser). Anledningen till ställtiden: starter ligger 6 h isär (08:00 / 14:00) och de flesta längder är ≤ 5,5 h, så 30–60 min påverkar sällan överlapp.
3. Starttidsflexibilitet ger −7 till −8 % (plus ytterligare med klippning). Det är ett verkligt hävstångsval men kräver pass- och bemanningsregler.
4. Originaltillfälle alltid tillåtet påverkar bara mfr (911 → 900).
5. Skalning ×1,38 ändrar nivån proportionellt men inte relativa slutsatser (±3 alla −62 % både med och utan).
6. Ingen variant ändrar slutsatsen "golv 435 för stora N". Den ändras bara av klippning för mfr N=14 (502).

## 5. Dokumentgranskning (uppgift 5)

Mot skripten:

| Påstående | Fil:rad | Utfall |
|---|---|---|
| 1 255 tentor / 46 604 tentander | ANALYS:62, 73; proto `DATA.pop` | Verifierat |
| Nuläge 1 586 (2026-01-15); 1 604 (2026-01-16) för 1 258 | ANALYS:71–72 | Verifierat |
| Tabell ±N alla/mfr (9 × 2 värden) | ANALYS:159–169; proto `DATA.curve` | Verifierat, alla 18 |
| Golv 435 = största tenta | ANALYS:171 | Verifierat |
| 112 flyttar (97/11/3/1; 47 till, 22 från helg) | ANALYS:171 | Siffrorna kommer ur en körning (probe5.json). Räkningen stämmer med den lösningen men talet är ej reproducerbart (119–125 i omkörningar) och ej bevisat minimum. Nedre gräns ≥105 |
| 503 flyttar (110/376/11/6; 439 från helg) | ANALYS:130, 171 | Idem; 502–506. Nedre gräns 499. Alla 439 helgtentor måste flyttas, så minimum ≥ 439 |
| Veckodagsfördelning (390/49/819) och typfördelning | ANALYS:78 | Verifierat |
| Kapacitetsbaslinje 1 179 platser, "åtta salar" | ANALYS:64, 74, 114, 174, 179, 222; DATAANALYS:91; proto 104 (`cap`), 252, 298–320 | **Fel**, se nedan |
| "4 av 73 dagar över 1 179, högst 407 över" | ANALYS:74, 114 | Räknat mot 1 179: stämmer. Mot 1 119: se nedan |
| "optimistiska undre gränser" | ANALYS:157 | Rimligt ord för klippt/oklippt tolkning men saknar att fönstret inte klippts (se K3) |
| "(mellan 0,1 och 36 sekunder)" | ANALYS:157 | Stämmer för probe5-körningarna (0,0–35,7 s); min formulering 0,9–51 s |
| "Antalet flyttar är bästa funna inom 60 sekunder" | ANALYS:171 | Korrekt men antalen är instabila (K8) |

### Kapacitetsbasen 1 179 är fel

`optimization_rooms.csv` har 8 rader med `eligible_for_exploratory_capacity_poc=True` och summa 1 179. En av dem är `uu-campus-gotland-b40` (Visby, 60 platser, `observed_in_booking_period=False`, tillgänglig "campus_gotland_from_spring_2027"). Uppsalas planeringsområde ger 1 119 platser i sju salar (206+229+200+80+96+128+180). Enligt AGENTS.md ska Uppsala och Visby hållas isär.

Omräknat med egen svepning (`cap.py`):

| Tak | Dagar över (av 73) | Högsta överskridande | Dagar |
|---|--:|--:|---|
| 1 179 (nuvarande doc) | 4 | 407 | 15 jan (+407), 16 jan (+389), 14 jan (+186), 13 jan (+68) |
| **1 119 (Uppsala)** | **5** | **467** | 15 jan (+467), 16 jan (+449), 14 jan (+246), 13 jan (+128), 12 jan (+43) |

För 1 258 behov: högst 485 över 1 119 (16 jan), 425 över 1 179.

Konsekvenser:

* "Dagar över kapaciteten", "högst 407 platser över", "1 179 mot 1 586" i ANALYS:74, 114, 174, 179, 222, DATAANALYS:91 och prototypen (`cap:1179`, rad 252, 298–320) ska bli 1 119, 5 dagar, 467.
* Prototypens text "8 salar · 1 179 platser" ska bli "7 salar · 1 119 platser (Uppsala)".
* Även 1 119 är en undre skattning av den faktiska kapaciteten. Klostergatan 3, Danmarksgatan 30 och Fyrishov D–F används men saknar kapacitet i registret (DATAANALYS: 68,3 % av bokade platser i de åtta salarna). Ett platstak jämfört med registrerade tentander är därför inte en realiseringsbaslinje.
* Acceptanstest 6 (ANALYS:179) "±3 alla dagar (598) redovisas som realiserbart" gäller summerad plats, inte packning i rum: ingen enskild sal rymmer största tentan (435 mot störst sal 229).

## 6. Robusthet och tolkning (uppgift 6)

* **Vad siffrorna är:** exakta minimum (bevisat optimala, certifierade av LP och av oberoende kontroll) av största samtidiga antal registrerade tentander för 1 255 tentor i fönstret 12 jan–31 mar 2026, i en modell där tentor får flyttas helt fritt inom fönstret, utan studentkrockar, utan lokal-, bemannings- eller digitala hinder, utan minsta avstånd mellan tentor av samma kurs, och (i basfallet) utan hänsyn till termingränserna. De är **teoretiska undre gränser för ett ointerfererat platsbehov**, inte genomförbara scheman.
* **"Platstopp minskar X % vid ±N":** −42 % (±1 alla), −55 % (±2), −62 % (±3), −73 % (≥7). Dessa är artefakter i den bemärkelsen att −62 % i hög grad drivs av att tentor flyttas före 12 jan. Med klippning −35 %, −43 %, −50 %. Alltså ligger verkligheten (om termingränserna är hårda) 10–15 procentenheter lägre. Vid mfr är minskningen vid ±3 −43 % utan och −35 % med klippning.
* Populationen är begränsad till 1 255 av 1 525 inlästa aktiviteter (267 oavgjorda, varav 175 digitala). Belastningen är därför för låg i absolut mening. Relativ minskning är mer robust (±1,38-skalan ger samma procent).
* Fönstret 12 jan–31 mar är ett extraktionsfönster ("terminen" i DATAANALYS:3), inte en hel termin. Om tentor utanför fönstret finns i verkligheten är en flytt dit inte modellerad. Det talar för klippt variant som huvudfall.
* "Golv 435" är inte en verksamhetsmässig gräns. Det är bara maxet av enskilda tentor och förutsätter att inga stora tentor behöver överlappa i hela fönstret, vilket kräver tentor flyttade ≥ 7–10 dagar (inkl. helger). Dokumentets egen fotnot ("beskriver inte en genomförbar verksamhet") bör kvarstå. Flexibilitetskurvan bör visas med klippning som standard, och bara upp till ~±7 för vardagar.
* 79 av 1 255 poster delar tillfälle. Det ändrar inte C men påverkar flyttantal och tolkning av "flyttad tenta".

## 7. Vad som INTE kunde verifieras

* Om 12 jan är terminens första tillåtna tentamensdag eller bara datafönstrets start (ingen källa i repot ger regeln). Den avgör om klippt eller oklippt är rätt huvudfall.
* Hur de 267 oavgjorda aktiviteterna (inklusive 25 med saknat antal) skulle förändra toppen.
* Om registrerade tentander är rätt belastningsmått (bokade ≈ 1,38 ×). Ingen oberoende mätning av verklig samtidig närvaro.
* Studentkrockar/programkrockar, minsta avstånd ordinarie–omtenta, tentamensperioder och spärrade dagar (finns inte i förprovet).
* Flyttantal: bevisat optimum saknas för ±2/±3 (nedre gräns 98–105 respektive 499 vs funna 116–125/502–506).
* Probe3/probe4 (äldre skript): ingen sparad logg att jämföra med.
* Rumsvis packning och kapacitet per sal (N1).

## 8. Återskapande

```
cd C:\Users\gunso745\AppData\Local\Temp\claude\C--lokalt-tentalokaler-PoC\b7d311db-b70e-4a23-b34f-c02537d53902\scratchpad\audit\a6
PY=C:\lokalt\tentalokaler\PoC\.venv\Scripts\python.exe
%PY% common.py          # population 1255 / 1258
%PY% run1.py            # alla 18 kurvpunkter, oberoende cumulative (run1.json)
%PY% lp.py              # LP-nedre gräns (lp.json)
%PY% run4.py            # lösning + oberoende kontroll för 16 punkter + klippt (run4.json)
%PY% run2.py            # stage 2 (flyttar) + kontroll + probe5:s egna lösningar (run2.json)
%PY% run3.py; %PY% run3b.py   # känslighet (run3.json, run3b.json)
%PY% cap.py             # kapacitet 1179 vs 1119, dagar över
%PY% docs_check.py      # probe5.json / proto-DATA
```
