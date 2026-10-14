# Hur verksamhetsunderlaget 2 oktober påverkar modellen (2026-10-12)

> **Historisk analys.** Statuspåståenden gäller den 12 oktober 2026. Aktuell
> status finns i [kravstatusen](../KRAV_OCH_STATUS.md); källuppgifterna finns i
> [verksamhetsunderlaget](../VERKSAMHETSUNDERLAG_2026-10-02.md).

**Underlag:** [`VERKSAMHETSUNDERLAG_2026-10-02.md`](https://github.com/gUUnnar/tentaoptimering/blob/docs/verksamhetsunderlag-2026-10-02/docs/VERKSAMHETSUNDERLAG_2026-10-02.md) och [`OVERLAMNING_CLAUDE_2026-10-12.md`](https://github.com/gUUnnar/tentaoptimering/blob/docs/verksamhetsunderlag-2026-10-02/docs/OVERLAMNING_CLAUDE_2026-10-12.md) (PR #12, ännu inte mergad). Presentationens siffror är *återgivna uppgifter*, inte verifierade regler. **Inget i detta dokument har gjort en av dem till en verifierad regel eller ett standardvärde.** Allt som provas är ett experiment med uttryckligt värde.

## Sammanfattning

| # | Fråga | Läge | Kan experimenteras nu | Kräver verksamhetsbeslut |
|---|---|---|---|---|
| 1 | Bemanningstrappa, minst två vakter | Modellen hanterar trappan och minimum; skillnad mot dagens 1/2/3 är mätt | Ja, som parametern `staffing.ladder` | Vad "per pass" avser, gränsen 250, regler över 300 |
| 2 | Perioden (mars mot januari–juni) | **Efterfrågekällan (Ladok) slutar 31 mars; lokalbokningarna går till augusti** | Nej: efterfrågan för april–juni saknas | Ladok-uttag för april–juni |
| 3 | Tre pass per dag | Går att pröva med `calendar.start_times`; 5-timmarstentorna sätter gränsen | Ja | Om tre pass är tillåtet i praktiken, och vad bokad längd innehåller |
| 4 | Lokalbestånd och RPS | Registret har 7 Uppsalasalar, 1 119 platser; RPS-lokalen modelleras inte | Delvis (val av salar) | Salsidentiteter, 1 109 mot 1 119, RPS, giltighetstid |
| 5 | Överbeställning mot modellkostnad mot realiserbar besparing | Hålls isär i modellen och i texterna; "pengar i sjön" ingår inte | Nej | Definition och källa för de två beloppen |
| 6 | Jämförbarhet mot Nuläge | Saknas i gränssnittet. **Förhandsvisningen med låsta tider är ogenomförbar med dagens lokalregister** (historisk last upp till 1 604 platser mot 1 119 registrerade) | Förhandsvisning går att köra men svarar "ogenomförbart" | Lokalbeståndet för Nuläge, och vilka lokaler som användes historiskt |

Granskningsanmärkningarna på PR #11 är åtgärdade (avsnitt 7).

## 1. Bemanningstrappan och minst två vakter

**Så använder modellen trappan.**
- Vakter per salstillfälle bestäms av antalet deltagare *i den salen*: det första steget vars gräns inte överskrids. Gränsen räknas alltså till sitt eget steg (250 deltagare ger steget "upp till 250").
- Ett första steg med två vakter ger minst två vakter per salstillfälle. Det första steget kan ha vilket antal som helst.
- En sal rymmer aldrig fler deltagare än trappans högsta gräns. Det är ett modellantagande, inte en regel: en tenta på 320 går inte in i en 400-platssal om trappan slutar vid 300, utan måste delas.
- Kostnad, placering och den oberoende eftervalideringen använder samma trappa, eftersom valideraren läser den ur den sparade indatan. Handräknat test: `tests/test_joint_staffing_ladder.py` (5 tester, båda strategierna).

**Skillnad mot nuvarande standard (50/150/300 → 1/2/3 vakter).** Samma tenta kräver fler vakter med trappan ur underlaget, till exempel 40 deltagare: 2 mot 1 vakt, 100: 3 mot 2, 200: 4 mot 3. Kostnaden för samma plan blir därför högre. **En sådan kostnadsskillnad beror på antagandet, inte på planeringen**, och jämförelsen redovisar den därför inte som en skillnad (`assumption_changes`, N-5).

**Underlagets trappa i data.** Av 1 170 tentor som behöver sal har 222 fler än 65 deltagare, 46 fler än 135, 17 fler än 220, 11 fler än 250 och **8 fler än 300** (störst 435). Största salen har 229 platser, så trappans övre steg gäller bara tentor som delas över flera salar, om trappan är *per sal*.

**Öppet, kräver verksamhetsbeslut.**
- Gäller trappan *per sal*, *per tenta* (alla salar sammanlagt) eller *per pass*? Modellen räknar per sal. Är den per tenta ändras bemanningen för de 46 tentor som delas.
- Gränsen 250 ligger i två intervall (221–250 och 250–300). Modellen läser 250 som steget 221–250 (5 vakter); 251 blir 6.
- Regler över 300 (8 tentor) saknas.
- "Alltid minst två vakter per arbetspass" och "arbetspass" (32/64 per dag) är odefinierade; de används inte som gräns.

**Experiment som går att göra nu.** Ställ in `staffing.ladder` till 65/2, 135/3, 220/4, 250/5, 300/6 och kör. Det är en känslighetsprövning med ett uttryckligen angivet värde, inte ett nytt standardvärde. Resultat: se avsnitt 8.

## 2. Perioden

Scenariot "Alla tentor i underlaget (12 jan–31 mars 2026)" är det som finns. Orsaken är nu utredd i det förberedda underlaget:

| Källa | Period |
|---|---|
| Lokalbokningar (`bookings.csv`) | 2025-09-01 – 2026-08-29, **inklusive april (550), maj (547) och juni (951)** |
| Examinationstillfällen (`exam_events.csv`) | 2025-09-01 – 2026-08-29 |
| **Ladok-aktiviteter (efterfrågan, `ladok_activities.csv`)** | **2026-01-12 – 2026-03-31** |

Efterfrågan (antal anmälda per tentamen) kommer från Ladok-uttaget, och det slutar 31 mars. Därför finns inga april–juni-tentor med deltagarantal i modellen, fast bokningarna finns. **Det är ett uttag som behöver kompletteras, inte ett urval som kan ändras.** Att ta bokningar utan Ladok-antal skulle kräva ett antagande om deltagarantal och vore ett påhittat underlag.

**Täckning inom perioden.** Av 1 525 Ladok-aktiviteter är 1 259 klara för modellering och 266 (17 %) oklara. Av de 1 259 finns 1 172 i Uppsala. Resultaten ska visa det (täckning, saknade grupper), vilket gränssnittet ännu inte gör (se "Återstår").

**Kräver beslut/uppgift:** Ladok-uttag för april–juni (och skälet till att det slutar 31 mars), och om oklara aktiviteter ska lösas före en helterminssimulering.

## 3. Tre pass per dag

**Det som redan går.** `calendar.start_times` är en lista utan övre gräns, så tre pass kan matas in utan kodändring. Senaste sluttid (`calendar.latest_end_time`, 20:00), ställtid, för- och efterarbete (`staffing.preparation_minutes`/`closing_minutes`) och salars tillgänglighet (`available_from/to`) ingår i prövningen av vilka pass en tenta får använda. Tentans längd är den bokade tiden i datan och saknas inte (1 259 av 1 259 har längd).

**Hur många tentor ryms i ett pass?** (flyttbara tentor, före sluttid 20:00): 08:00–11:00: alla (1 170); 12:00 och 13:00: 1 168; 14:00: 1 156; 15:00: 1 138; **18:00: bara 65**. Längderna: 4 timmar 403, **5 timmar 498**, 3 timmar 172, 2 timmar 53, övriga 44.

**Experiment (alla tentor i underlaget, samma antaganden, start från samma körning):**

| Körning | Starttider | Utfall |
|---|---|---|
| A (grund) | 08:00, 14:00 | genomförbar, 1 823 000 kr, undre gräns 1 773 000 kr |
| B | 08:00, 13:00 | **ogenomförbar** (bevisat på 21 s) |
| C | 08:00, 13:00, 14:00 | genomförbar, 1 823 000 kr, undre gräns 1 689 000 kr (större gap) |
| D | 08:00, 13:00, 18:00 | **ogenomförbar** (bevisat på 16 s) |

B och D saknar 14:00. En 5-timmarstenta från 08:00 slutar 13:00 och salen är fri först 13:30, så den kan inte följas av ett pass 13:00 i samma sal. Då räcker inte lokalkapaciteten på de tätaste dagarna. D har dessutom bara 65 tentor som ryms 18:00. **Ett tredje pass (C) gav ingen lägre kostnad än grunden i den här omgången**, men gapet är större, så det är inte bevisat att det inte finns någon vinst. Det är **inte** ett standardscenario: tre pass ska fortsatt vara ett prövningsalternativ.

**Kräver beslut/uppgift:** om tre pass är tillåtet i praktiken (vakter, studenter, raster) och om den bokade längden (t.ex. 5 timmar) innehåller extra tid som inte är skrivtid.

## 4. Lokalbeståndet och RPS

| | Presentationen | Registret i modellen (`optimization_rooms.csv`) |
|---|---|---|
| Ordinarie salar | 7 salar, 1 109 platser | 7 salar i Uppsala, **1 119 platser** (Bergsbrunnagatan 15 sal 1 och 2: 206 + 229, Fyrislundsgatan 80 sal 1 och 2: 200 + 80, Råbyvägen 95 sal 1–3: 96 + 128 + 180) |
| RPS-lokal | 1 lokal, 41 platser | Klostergatan 3 (Specialtentamenscenter) finns i bokningsregistret med **2 267 observerade placeringar** (flest av alla) men **inte som modellerad sal** och utan verifierad kapacitet |
| Övrigt | – | Campus Gotland B40 (60 platser, Visby, gäller från 2027-01-01) ingår inte i Uppsalaurvalet. Fyrishov hall C–F och Danmarksgatan 30 saknar kapacitet i registret. |

**Registret räcker inte för att återskapa historiken.** Med varje tenta på sin ursprungliga tid överstiger lasten de 1 119 registrerade platserna vid 6 av 108 kombinationer av dag och starttid, som mest **1 604 platser** (2026-01-16 08:00), alltså 485 platser (43 %) över. Fler lokaler än de sju användes alltså historiskt (bokningsregistret visar bland annat Klostergatan 3, Fyrishov och Danmarksgatan 30). Det påverkar tolkningen av varje lokalbehovsresultat: en modell som får flytta tentor ±1 dag klarar sig med sex av de sju salarna, men en jämförelse mot en historik som kräver mer än registret innehåller är inte rättvisande.

Skillnaden **10 platser** (1 119 mot 1 109) och vilken sal den gäller är inte utredd. Inga salar eller kapaciteter har lagts till. Kapaciteterna är publicerade nuvarande värden utan verifierad giltighet för 2025/2026 (`capacity_temporal_status`).

**Konsekvens för modellen.** Tentor som i verkligheten läggs i RPS-lokalen kan inte placeras där i modellen, och 41 platser × 2 pass saknas i kapacitetsbilden. Hur många tentor det rör är inte bestämt (specialstöd är inte modellerat). Det är en bidragande osäkerhet i alla lokalbehovsresultat.

**Experiment nu:** Val av salar i gränssnittet är under uppbyggnad (`rooms.selection`).
**Kräver beslut/uppgift:** vilka sju salar och vilken RPS-lokal som avses, deras kapacitet och giltighetstid, och vilka enheter som faktiskt kan avvecklas.

## 5. Överbeställning, modellkostnad och realiserbar besparing

Fyra olika storheter får inte blandas:

| Storhet | Vad den är | Var | Användning |
|---|---|---|---|
| **Modellkostnad** | Summan av proxypriser (lokalkostnad per plats och år, kostnad per vaktresurs) för en körning | Resultatet i gränssnittet | Jämförelse mellan körningar *med samma antaganden* |
| **"Pengar i sjön"** | Kostnad för gapet mellan beställda platser och anmälda i Ladok: 1 687 819 kr (vänster tabell) respektive 1 779 583 kr (höger tabell), orsaken till skillnaden okänd | Presentationen | Mått på beställningsprecision. **Ingår inte i modellen** och är inte målfunktionens facit. |
| **Personalrelaterad observation** | Bomtid 250 000 kr och mertid 44 000 kr för 2025 | Presentationen | Historisk observation, inte garanterat reducerbar |
| **Realiserbar besparing** | Den del som går att avveckla: kräver avtalsobjekt, uppsägningstid, engångskostnader och referensberäkning | Ingen | **Redovisas inte någonstans i dag** |

Gränssnittet säger redan att siffran är modellkostnad och inte faktisk kostnad, att undre gräns–verifierad kostnad är ett intervall och att kostnadsskillnader vid ändrade antaganden inte redovisas. Att modellens kostnadsantaganden inte är samma som "pengar i sjön" är ännu inte uttryckligt i gränssnittet (se "Återstår").

**Kräver beslut/uppgift:** vilka kostnadsposter som ingår i respektive belopp, och varför tabellerna skiljer.

## 6. Jämförbarhet mot Nuläge

**Läge.** Gränssnittet jämför mot föregående körning av samma scenario. **Nuläge enligt N-1 saknas.** Jämförelsen är ändå skyddad mot de fel som handoveren nämner:
- olika dataunderlag eller tentamängd: ingen jämförelse;
- olika kostnads-, **bemannings-** eller efterfrågeantaganden: ingen kostnadsskillnad redovisas (N-5, och bemanningsreglerna räknas nu som antaganden);
- körning utan verifierad lösning: ingen jämförelse.

**Förhandsvisning av Nuläge.** Samma modell, data, period och antaganden, men flexibiliteten avstängd: flyttfönster 0 dagar och inga flyttbara tentatyper (`window.earlier_days = 0`, `window.later_days = 0`, `flex.movable_types = []`). Alla tentor ligger då kvar på sin ursprungliga tid. Bara de uttryckliga flexibilitetsparametrarna skiljer, så en jämförelse skulle vara tolkningsbar. **Körningen är dock ogenomförbar** med dagens lokalregister (avsnitt 4 och 8): modellen bevisar att tentorna på sina ursprungliga tider inte ryms i de sju registrerade salarna. Nuläge kan därför inte beräknas i modellen förrän lokalerna som användes historiskt finns i registret eller Nuläge definieras på annat sätt.

**Det som behöver bestämmas innan Nuläge byggs in som funktion.**
- Ska lokalbeståndet i Nuläge vara det *minsta bestånd som den historiska tidtabellen kräver* (vad förhandsvisningen ger) eller *alla salar som är kontrakterade i dag*? Skillnaden avgör vad "besparing" betyder.
- N-3: vid ändrad efterfrågan behövs två Nulägesberäkningar (med och utan ändrad efterfrågan) för att skilja efterfrågeeffekt från planeringseffekt.
- N-9 och N-1 hänvisar till samma kod, data och antaganden. Funktionen "beräkna Nuläge för den här körningen" kan göras med samma körningsmekanism (en körning med flexparametrarna avstängda och övriga parametrar lika), men inte förrän ovan är avgjort.

## 7. Är granskningsanmärkningarna på PR #11 åtgärdade?

Ja, alla åtta (commits `7a3d1f7`, `1958d7e`, `47ba8d4`, `a7d2e2c`, `bebb798`), med tester:

| Anmärkning | Åtgärd |
|---|---|
| "Hela terminen" var bara mars | Scenariot döpt om till underlagets period; orsaken (Ladok slutar 31 mars) utredd i avsnitt 2 |
| Kostnadsjämförelse blandade antaganden | Ingen kostnadsskillnad vid ändrade kostnads-, bemannings- eller efterfrågeparametrar |
| Kostnad visades utan verifiering | Ingen kostnad utan verifierad lösning; validering körs vid läsning |
| Felobjekt kraschade gränssnittet | Felet är text; klienten normaliserar |
| Misslyckad slutlagring rapporterades som lyckad | Loggen avslutas med `failed` |
| Olika kontrakt för ändrade parametrar | Lista med id; delat kontrakt med riktiga svar som ögonblicksbilder i båda sidors tester |
| Sparad status användes | Ny oberoende validering vid läsning |
| Nuläge saknas | Öppen, se avsnitt 6 |

Ytterligare kontroller från handoveren: teknisk status mot eftervalidering vid avbruten eller korrupt körning (testat), parameterändringar med samma kontrakt (testat), påverkansmått och ekonomisk potential hålls isär (modellkostnad redovisas aldrig som besparing).

## 8. Körda experiment

Alla körningar gjordes mot hela underlaget (1 172 tentor, 12 jan–31 mars 2026) med 8 trådar och tidsgräns 300 s. Siffrorna är modellkostnad med proxypriser, inte faktisk kostnad, och varje körning är en enstaka körning.

**Känslighet: bemanningstrappan ur underlaget.** Trappan 65/2, 135/3, 220/4, 250/5, 300/6 (minst två vakter) mot standardens 50/1, 150/2, 300/3. Allt annat lika, start från grundkörningen.

| | Standardtrappa (grund) | Trappa ur underlaget |
|---|---|---|
| Verifierad kostnad / undre gräns | 1 823 000 kr / 1 773 000 kr | 2 139 000 kr / 2 073 000 kr |
| Bemanningspool | 16 | **22** (+6) |
| Salar som används | 6 | 6 |
| Utfall | genomförbar, gap 2,7 % | genomförbar, gap 3,1 % |

Skillnaden i kostnad (+316 000 kr) beror på **antagandet** om hur många vakter som behövs, inte på planeringen, och redovisas därför inte som en skillnad i jämförelsen. Poolen och antalet salar jämförs däremot. Pool 22 mot 16 visar hur mycket bemanningsbehovet ökar med den trappan; det är en uppskattning med ett overifierat värde.

**Förhandsvisning av Nuläge (tider låsta).** Utfall: **ogenomförbar** (bevisat). Orsak: se avsnitt 4. Ingen kostnad kan redovisas.

**Tre pass per dag och starttider:** se avsnitt 3.

## Återstår, som inte är gjort

- **Täckning i resultatet:** visa antal Ladok-aktiviteter, klara/oklara/exkluderade och planeringsområde per körning (uppgifterna finns redan i `joint_input.json`).
- **Kostnadsbegrepp i gränssnittet:** en kort ruta som skiljer modellkostnad från "pengar i sjön" och realiserbar besparing.
- **Nuläge som funktion** (efter beslutet i avsnitt 6).
- **Val av salar och tentamenstyper** (pågår).
- **Windowsdistribution och mappväljare (PR #5):** ej verifierat efter ombyggnaden.
