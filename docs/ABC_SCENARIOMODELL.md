# A, B och C: faktisk bokning, grundoptimering och egna körningar

Syftet med PoC:n är att undersöka hur mycket användningen av tentamenslokaler kan optimeras och vilken ekonomisk potential det innebär. Användaren ska kunna ändra ett verksamhetsvillkor, se effekten direkt och jämföra med både historiken och sina tidigare körningar. Utgångspunkten är verkliga bokningar och verksamhetens ursprungliga önskemål, inte ett antal på förhand konstruerade scenarier.

Det här dokumentet är den gällande begreppsmodellen. Där äldre dokument (till exempel `KONCEPTUELL_KRAVSPECIFIKATION.md`, `DOMANMODELL.md`) talar om *Nuläge*, gäller det som står här.

## De tre alternativen

| | A – Faktisk bokning | B – Grundoptimering | C – Egna körningar |
|---|---|---|---|
| Vad | Hur tentorna faktiskt bokades | Optimering utifrån verksamhetens önskemål med dokumenterade grundvärden | Optimering med parametrar som användaren själv valt |
| Optimeras det? | **Nej, aldrig** | Ja | Ja |
| Källa | `bookings.csv`, `exam_events.csv`, `exam_wishes.csv` | Scenariot `config/scenarios/joint_base.toml` | Valfri utgångspunkt plus användarens ändringar |
| Antal | En per urval | Normalt en (kan köras om) | Obegränsat |
| Kod | `profile_actual.py` (läser bara data) | `joint_*` (samma motor) | `joint_*` (samma motor) |

B och C använder **samma optimeringsmotor**. Skillnaden är bara parametervärdena: B använder de definierade grundvärdena, C använder det användaren valt. Det finns inga separata algoritmer och inga hårdkodade specialscenarier. Den som vill ha en särskild kombination, till exempel låsta historiska datum, ställer in den som parametrar.

### A – Faktisk bokning

A återger bokningsunderlaget som det är: bokat datum och tid, bokad sal eller salar, bokade platser och övriga uppgifter. Ineffektiva bokningar, bokningar som skulle vara omöjliga i modellen och salar som saknas i optimeringsmodellens lokalregister visas ändå fullt ut. Det som inte går att jämföra redovisas, det gör inte historiken ogiltig:

- en bokning som bara anger adress räknas inte som sal och sätts inte mot någon kapacitet;
- en namngiven sal som saknas i lokalregistret räknas som använd, med okänd kapacitet;
- en plats som inte är fysisk (till exempel ”Hemma”) visas men är ingen sal;
- avbokade tentor och tentor utan datum redovisas som *inte bokade* med sin status som orsak;
- bokade platser (reserverade) och anmälda tentander (Ladok) är olika mått och slås aldrig ihop;
- A har ingen kostnad i underlaget: faktisk kostnad finns bara som preliminär intern hyra för hela tentamenslokalverksamheten och kan inte fördelas på ett urval.

A beror inte på någon körning och ändras inte av någon parameter. Ett test (`tests/test_abc_actual.py`) säkerställer att modulen som bygger A inte importerar optimeraren.

> **Det som tidigare hette Nuläge var inte A.** Det var en optimering där de historiska datumen låstes (`flex.movable_types = []`) medan sal och bemanning fortfarande optimerades. Den är fortfarande användbar som en parameterinställning i C och används för besparingspotentialen, men den heter nu *referensoptimering med låsta datum* och förväxlas inte med A.

### B – Grundoptimering

B körs med scenariot `joint_base` (alla klara tentor i Uppsala i hela underlaget), katalogens standardvärden och fem dokumenterade antaganden, var och en med motivering i scenariofilen:

| Parameter | Värde | Varför |
|---|---|---|
| `wish.candidate_policy` | `wishes` | Verksamhetens önskemål är underlaget: önskat datum och reservdatum 1 och 2, inga andra dagar. Reservdatumen är prioriterade alternativ som verksamheten själv angav, inte godtyckliga dagar inom ett flexibilitetsintervall. |
| `wish.tiebreak` | `wish_priority` | Bland lika billiga lösningar väljs önskat datum före reservdatum 1, reservdatum 2 och annat datum. |
| `rooms.include_observed_unregistered` | `true` | Registrets sju salar i Uppsala (cirka 1 040 platser per pass) rymmer inte de bokade tentorna en toppdag (över 2 800 tentander). Salar som bokningarna använt men som saknar registerkapacitet (Fyrishovs hallar) tas med, med största bokade antal platser som kapacitet. Det är en underkant, inte en uppmätt kapacitet. |
| `cost.room_annual_per_seat_ore` | 1 000 kr | Explorativ proxy, inte avtalskostnad. |
| `cost.staff_annual_ore` | 50 000 kr | Explorativ proxy, inte avtalskostnad. |

Utan antagandet om observerade salar är B bevisat ogenomförbar (3 834 tentander önskar 16 januari mot cirka 2 078 platser). Det mättes: med de tre Fyrishovhallarna lades till blev B genomförbar. Antagandet är en parameter och kan stängas av i C; då visas B:s ogenomförbarhet med skäl i stället för en siffra.

Önskemålen anger bara datum, aldrig klockslag. `wish.time_policy` bestämmer om tentan får vilket tillåtet pass som helst på ett önskat datum (förval) eller bara sin bokade starttid.

### C – Användarstyrda körningar

C är inte ett scenario. Det är en valfri mängd körningar med olika parameteruppsättningar. Användaren väljer en utgångspunkt (B, en sparad parameteruppsättning eller en tidigare körning), ändrar vilka parametrar som helst (enskilt och fritt kombinerade) och kör. Varje körning:

- får ett namn (eget eller ett som säger vad som ändrades);
- sparas med samtliga använda parametervärden (`joint_scenario.toml` och `joint_input.json`);
- kan köras om eller användas som utgångspunkt för en ny körning (`scenario=run-<körnings-id>`);
- kan jämföras med A, B och andra körningar;
- skrivs aldrig över: varje start är en ny katalog.

En körning med samma värden som en tidigare är samma typ (B förblir B, C förblir C); varje ändrad parameter, vald period eller annan utgångspunkt gör den till C.

Parametrar som finns i modellen och som användaren kan ändra är bland annat: lokalval (`rooms.selection`, `rooms.include_observed_unregistered`), tillåtna datum och tider (veckodagar, starttider, spärrade perioder, start- och slutdatum), om bara önskemål får användas eller om flyttfönster tillåts (`wish.candidate_policy`, `window.*`), vad som avgör mellan lika billiga lösningar (`wish.tiebreak`), flyttbara tentatyper (och därmed låsta datum), bemanningstrappan och -reglerna, kostnadsantaganden och efterfrågevariation. Listan är inte uttömmande; hela parameterkatalogen (`config/joint_parameter_catalog.toml`) gäller.

Gränser finns bara där ett verkligt verksamhetskrav eller ett tekniskt villkor i modellen kräver det (till exempel att en procentandel ligger mellan 0 och 100).

## Hur önskemål, kostnad och lokalutnyttjande vägs

Motorn minimerar jämförbar årskostnad först. Bland lösningar med samma kostnad väljs den som har lägst *straff* (`joint_preference.py`): under `fewest_changes` 0 vid bokat tillfälle och 1 annars; under `wish_priority` 2 × önskemålsrang (0 önskat datum, 1 reservdatum 1, 2 reservdatum 2, 3 annat datum) plus 1 om det inte är det bokade tillfället. Samma vikter används i hela modellen, relaxationen och dagdelproblemen.

**Begränsning:** någon kronviktad avvägning mellan önskemål och kostnad finns inte. Önskemål kostar inte pengar i modellen, så de kan bara styra (a) vilka datum som är tillåtna (`wish.candidate_policy`) och (b) valet mellan lika billiga lösningar. Vill användaren hålla fler tentor på önskat datum ställer hen in strängare policy, inte en vikt. En kronviktad målfunktion kräver en ändring av alla tre lösningsvägarna och av valideringens kostnadsomräkning, och är inte gjord.

## Datakällor, verksamhetsvillkor, körningar och resultat hålls isär

| Lager | Vad | Var |
|---|---|---|
| Datakällor | Bokningsexport, Ladok-uttag, lokalhyror (originalet skrivskyddat) | `C:\lokalt\tentalokaler\underlag`, normaliserat till `data/processed` |
| Verksamhetsvillkor | Parametrar och antaganden, versionsspårade | `config/joint_parameter_catalog.toml`, `config/scenarios/` |
| Körning | En avslutad beräkning med frusna värden | `runs/<id>/` (`joint_scenario.toml`, `joint_input.json`, `joint_run.json`) |
| Resultat | Placering, kostnad, validering | `joint_result.json`, `joint_validation.json` |

### Önskemålen i underlaget

Exportens fält `scheduled_date` (bokat datum), `requested_date` (önskat datum), `reserve_date_1`, `reserve_date_2` och `no_reserve_date_reason` lästes redan in och normaliserades men användes inte av motorn. De förs nu till `exam_wishes.csv` (en rad per tentamenstillfälle, `wishes.py`), och därifrån in i körningens indata (`wish_dates`, `wish_status`, `wish_reason` per tentamensbehov).

Mätt på det förberedda underlaget (5 506 bokningsbeställningar):

- reservdatum angivna för 2 282; 2 098 saknar reservdatum men har en motiveringstext (varav 930 utan en enda bokstav, till exempel ”.” eller ”-”); **1 126 saknar både reservdatum och motivering**;
- önskemålen är konsekventa inom en beställning (inga motstridiga rader) och varje beställning ger ett tentamenstillfälle;
- bokat datum är önskat datum för 4 832, reservdatum 1 för 105, reservdatum 2 för 50 och inget av dem för 154; 365 saknar bokat datum.

Motiveringarna bevaras som skrivna och tolkas inte. Det enda som härleds ur texten är fakta om texten själv (finns den, innehåller den en bokstav). Önskemålen anger datum, aldrig klockslag.

### Ladok och rätt tentamen

Tentander (`demand_value`) kommer från Ladok-aktiviteter. En aktivitet kopplas till ett bokat tentamenstillfälle via den provisoriska kandidatkopplingen (kurskod, datum, starttid; `candidate_linkage.csv`, `activity_booking_candidates.csv`). Flera aktiviteter kan bilda samma tentamenstillfälle (samtenta); deras antal summeras då som disjunkta delgrupper och anges som sådant (`participant_group_basis`). Tvetydiga och saknade kopplingar redovisas i bokningsvyerna och i datakvalitetslagret och gissas aldrig. Tentamina med flera lokalbokningar räknas en gång som tentamen och en gång per sal i salstabellen (tester: `test_abc_actual.py`, `test_booking_overview_compare.py`).

### Underlag och modellversion per körning

Varje körning sparar i `joint_run.json` vilket underlag (`underlay_id`, `dataset_hash`) och vilken modellversion (motor, kontraktsversioner, parameterkatalogens version och kontrollsumma) den byggdes med. Uppdateras underlaget räknas äldre körningar inte om i tysthet: de märks *äldre underlag* i körningslistan och jämförs inte med den faktiska bokningen (som alltid läses ur nuvarande underlag) om kontrollsumman skiljer. Två körningar med olika underlag eller olika uppsättningar tentor jämförs inte heller.

## Jämförelse

`GET /api/abc/compare?left=&right=` (en referens är `actual` eller ett körnings-id) jämför A–B, A–C, B–C och C–C. A tas alltid för samma tentor som den körning den jämförs med. Jämförelsen visar:

- nyckeltal: placerade tentor, använda salar (i och utanför lokalregistret), adresser utan sal, vaktpool;
- fördelning på önskat datum, reservdatum 1, reservdatum 2 och annat datum;
- hur många tentor som fått ändrat datum, ändrad starttid eller ändrad sal (salbyte räknas bara där båda sidor anger salar i registret; annars *inte jämförbart*);
- salanvändning per sal (tillfällen, tid i bruk utan dubbelräkning av överlapp, högsta samtidiga platser och andel av känd kapacitet) och kapacitetsutnyttjande per dag;
- tentor som inte placeras och orsaken som körningen eller bokningen själv registrerade;
- kostnad, uppdelad så att sorterna aldrig blandas: *historisk kostnad* (A: saknas), *modellberäknad kostnad* (körningar) och *teoretisk skillnad mellan två modellkostnader* (bara när båda är verifierade, har samma kostnads- och efterfrågeantaganden och samma tentor; med osäkerheten från sökningens gap);
- *vad som skulle behöva förändras* för att en lägre modellkostnad ska bli lägre faktisk kostnad (salar som kan frigöras, mindre vaktpool). Avtal och uppsägningstider ingår inte i modellen;
- vilka parametrar som skiljer (A har inga).

En effektivare placering är därmed ingen besparing i sig, och om datatäckningen inte räcker för en rättvis jämförelse står det i jämförelsen.

## Gränssnitt

Sidan *Optimering* har tre flikar: **1. A, B, C och jämförelse** (de tre alternativen, körningshistoriken, hur komplett önskemålen är och jämförelsen), **2. Ställ in och kör** (utgångspunkt, namn, period, parametrar; knappen heter *Kör B* när inget ändrats och *Kör som egen körning (C)* annars) och **3. Resultat**. Från resultatet öppnas jämförelsen med A, B eller en annan körning. Test- och utvecklingsscenarier (`hidden = true` i scenariofilen) erbjuds inte som utgångspunkt.

## Kvarstående begränsningar

1. Ingen kronviktad avvägning mellan önskemål och kostnad (se ovan).
2. Lokalregistret saknar kapacitet för Fyrishovs hallar och för Danmarksgatan 30. Fyrishovs hallar tas med som underkant i B; Danmarksgatan 30 är bara en adress i bokningarna och tas inte med. Särskilt stöd (Klostergatan 3, 634 bokningar som bara anger adress) ligger utanför modellen och syns bara i A.
3. A har ingen kostnad; modellkostnaden för låsta datum är en separat modellberäkning (resultatvyn), inte A.
4. Önskemål anger bara datum. Hur ett klockslag på ett önskat datum ska tolkas är en parameter, inte ett faktum.
5. Verksamhetsmässig verifiering (`business_verification`) är fortfarande `not_evaluated` för alla körningar.
6. B kan vara bevisat ogenomförbar för vissa urval eller parametrar; då redovisas status och blockerande krav, aldrig en partiell placering.
7. Äldre körningar (före den här ändringen) saknar `joint_run.json` och visas som äldre körningar med scenario och starttid som namn.
