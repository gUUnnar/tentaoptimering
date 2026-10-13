# Valbar planeringsperiod, snabba körningar och redan lagda bokningar

Status: steg 1–2 är genomförda på `feature/valbar-period-snabbkorning` (från PR #11). Steg 3 (hänsyn till redan lagda bokningar) är **designat men inte implementerat**.

Kravunderlag: `docs/OVERLAMNING_CLAUDE_2026-10-12.md` och `docs/KONCEPTUELL_KRAVSPECIFIKATION.md` (UX-9, §11.8, §11.9) i PR #12. Hela terminen är **inte** längre minsta planeringsenhet: datatäckningen och användarens val styr perioden.

## 1. Vad som är genomfört

### Periodval i gränssnittet (utan scenariofiler)

- Under "2. Välj planeringsperiod" väljs start- och slutdatum, eller en genväg: en dag, en vecka, en månad eller hela underlaget. Genvägarna utgår från underlaget (dagen med flest tentor, första dagen) och stannar inom täckningen.
- Gränssnittet visar täckningen per källa: deltagarantal (Ladok) 12 januari–31 mars 2026 och lokalbokningar 1 september 2025–29 augusti 2026. Bokningar visas som information men ger ingen efterfrågan och kan inte optimeras utan deltagarantal.
- Servern kontrollerar perioden (`GET /api/joint-runs/period`) och gränssnittet visar antal tentor som kan planeras, antal utan deltagarantal (de ingår inte, men döljs inte) och varningar. Start är spärrad tills perioden går att planera.
- Utan val gäller scenariots egen period som förut.

### Regler för perioden (`src/tentaoptimering/joint_period.py`)

| Fråga | Regel |
|---|---|
| Vilka tentor ingår? | De vars historiska datum ligger i perioden (inklusive gränsdagarna), klara för modellering i scenariots planeringsområde. |
| Tentor vars flyttfönster passerar periodgränsen | Kalendern skärs till perioden. En tenta flyttas aldrig ut ur perioden, så en tenta nära gränsen har mindre rörelsefrihet. Det anges som varning vid valet. |
| Period delvis utanför efterfrågeunderlaget (till exempel 1 januari–30 april när Ladok täcker 12 januari–31 mars) | Systemet begränsar **inte** beräkningen på egen hand. Kontrollen visar vilken kortare period som kan planeras och körningen kan startas först när användaren uttryckligen kryssat i godkännandet av den kortare perioden (`accept_partial`); utan godkännande avvisas begäran (HTTP 422). Godkännandet nollställs när ett datum ändras. Körningens frusna scenario och sammanfattningen sparar både vald och planerad period (`[period]`), och resultatvyn visar "Delvis planerad period … gäller inte hela den valda perioden". Resten är okänd, inte tom. |
| Period helt utanför underlaget | Avvisas med besked om täckningen (HTTP 422), ingen körning startas. |
| Inga tentor med känt deltagarantal | Avvisas med besked. |
| Scenario med namngivna tentor (`exam_event_ids`) | Tar inget periodval; felet förklarar varför. |
| Period och `calendar.start_date`/`calendar.end_date` som parametrar samtidigt | Avvisas; perioden sätter dessa datum. |
| Periodens plats i körningen | Perioden skrivs in i körningens frusna scenariokopia och indata (`subset.date_from/date_to`, `calendar.*`). Den visas i sammanfattningen (`period`). |
| Jämförelse mellan perioder | Körningar med olika uppsättningar tentor är ej jämförbara (befintlig kontroll), så olika perioder jämförs inte. |

### Explorativ planering, märkt i varje resultat

Modellen känner inte till bokningar som ligger utanför de valda tentorna. `planning_basis` i sammanfattningen (`mode = "exploratory"`, `fixed_bookings_considered = false`) och en text i resultatvyn säger att ett resultat **inte visar att en sal är ledig i verkligheten**. Detta gäller alla körningar i nuvarande motor, inte bara perioder.


### Kostnadsbegreppet: modellerad årlig kapacitetskostnad för valt urval

Kostnaden i resultatet är inte kostnaden för perioden. Den är summan av de salar som behövs (platser gånger årspris, `annual_room_cost_ore`) och vaktpoolen, som dimensioneras efter toppbelastningen (`staff_pool_size` gånger årskostnad per vakt, `annual_staff_pool_cost_ore`), plus eventuella pass- och externkostnader. Posterna är kontrollerade mot resultatet i `tests/test_joint_period_run.py`: totalen är summan av delposterna och vaktpoolskostnaden är poolstorleken gånger årskostnaden.

Namnet **"Modellerad årlig kapacitetskostnad för valt urval"** används därför konsekvent i sammanfattningen, kostnadsfältet, jämförelsetabellen, förklaringsrutan och i `planning_basis.cost_name`. En dag (508 tkr) kan kosta mer än en vecka (379 tkr) eftersom kapaciteten dimensioneras efter toppen och en endagsperiod har en kalender på en enda dag: tentorna kan inte flyttas till andra dagar för att jämna ut toppen. Det är en rimlig förklaring som inte är separat testad; det som är testat är att kostnaden följer av salarna och vaktpoolen. Kostnader för olika urval jämförs inte och skalas inte upp till en årlig besparing.

### Korrigering som korta körningar avslöjade

Körnings-id består av tidsstämpel i hela sekunder plus scenario-id. Två körningar inom samma sekund gav `FileExistsError`. Korta perioder avslutas på under en sekund, så detta kan inträffa i vanlig användning. Ett nytt id får nu närmaste lediga sekund (formatet och ordningen bevaras, `_new_run_directory`).

## 2. Mätning av snabba körningar

Skript: `python tools/measure_period_runs.py` (tillfällig lagringsmapp med en kopia av `data/processed`; samma väg som gränssnittet: `start_joint_run` → motor → oberoende eftervalidering → `run_summary`). Ingen varmstart (`warm_start = none`), tidsgräns 120 s, scenario `joint_underlay_period`.

Dator: Intel Core Ultra 7 165U, 14 logiska kärnor, 31 GB RAM, Windows 11. Mätningen är en enda körning per fall och ska läsas som storleksordning, inte som garanti.

| Urval | Period | Tentor | Utfall | Tid till första verifierade lösning | Total körtid | Gap |
|---|---|---|---|---|---|---|
| Dag | 2026-02-09 | 7 | optimal, verifierad (teknisk eftervalidering `pass`) | under 1 s | 0,5 s | 0 % |
| Vecka | 2026-02-09–15 | 60 | optimal, verifierad | under 1 s | 0,9 s | 0 % |
| Månad | 2026-02-01–28 | 339 | optimal, verifierad | 28 s | 29,8 s | 0 % |
| Hela underlaget | 2026-01-12–03-31 | 1 172 | `feasible_not_proven`, verifierad (tidsgränsen 120 s nåddes) | 90 s | 122,9 s | 2,7 % |

Alla fyra körningarna har fullständig placering och teknisk eftervalidering `pass`; verksamhetsmässig verifiering är `not_evaluated` (modellen har ingen sådan bedömning). Hela underlaget är en tidsbegränsad körning och inte bevisat optimal: gapet visar hur långt från bevisad optimal kostnad den är. Mätvärdena är en körning per fall på en dator som inte gjorde annat; en tidigare körning av samma fall under samtidig annan belastning gav för hela underlaget 96 s respektive 120,7 s, så skillnaden mellan körningar är några sekunder.

"Tid till första verifierade lösning" är `first_solution_seconds` i sammanfattningen. För den nedbrytande strategin (`decomposed`) levereras en fullständig, kontrollerad lösning först när alla dagar är lösta, så den tiden är lika med lösningstiden; basen anges som `solver_start`. Total körtid är hela jobbet inklusive indatabyggnad, sparande och eftervalidering.

Inga tidsmål har fastställts; målen ska sättas efter dessa mätningar (kravspecifikation §11.9).

## 3. Steg 3 – design: hänsyn till redan lagda bokningar (inte implementerat)

> **Ersätts delvis.** Den här utkast-designen utgår från dagens datauttag och föreslår "kapacitetsreduktion per adress och pass" som modell när sal saknas. Det gör en datalucka till ett modellantagande och strider mot principerna i `docs/ARKITEKTURPRINCIPER_DATAKVALITET.md` (modell och datakvalitet hålls isär, saknade uppgifter hanteras explicit, inga tysta antaganden). Gällande riktning är den arkitekturen: bokningsrader klassificeras till resurstillstånd i datainläsningen och undantagspolicy väljs per planeringsläge. Avsnittet nedan ska skrivas om innan steg 3 påbörjas; läs det som en beskrivning av dagens data, inte som modell.

### Problemet

Vid planering av en kort period väljs en delmängd tentor ut för optimering. Andra bokningar i samma period (andra tentor, tentor som inte ingår i populationen, eventuellt annan verksamhet) tar plats i salarna. Idag modelleras varje sal som fri alla pass där den är öppen (`Room.available_slot_ids`, byggd av `_rooms` i `joint_inputs.py` ur `available_from/available_to`). Därför kan ett resultat visa en lokal som ledig fast den är bokad. Det är acceptabelt för **explorativa snabbtester** men inte för **verklig korttidsplanering**.

### Vad underlaget tillåter (kontrollerat mot `data/processed/bookings.csv`)

- 8 466 bokningsrader (1 sep 2025–29 aug 2026), av dem 2 442 inom Ladokperioden. Kolumner: datum, tid (`scheduled_time` som intervall), längd, adress, sal, `booked_places`, status (`Klar`, `Avbokad`, `Under behandling`, `Andring begard`).
- **Salkolumnen är i många rader tom**: bokningen gäller en adress och ett antal platser, inte alltid en namngiven sal. Spärrning per sal är därför bara möjlig där sal är angiven; i övrigt går det bara att reducera **platskapaciteten per adress och pass**.
- Avbokade rader (364) ska inte spärra. Status "Under behandling" och "Andring begard" är tvetydiga och behöver ett beslut.
- Bokningar saknar kopplingen till optimeringspopulationen utom via länkningen mot Ladok (`linkage.py`), som är provisorisk och ibland tvetydig.

### Föreslagen modell

1. **Fasta bokningar** = bokningsrader i den valda perioden som inte tillhör de tentor som optimeras. Tillhörighet avgörs av länkningen (`candidate_linkage.csv`). Rader med oklar koppling hanteras enligt läget nedan, aldrig tyst.
2. **Tidsöverlapp**: en bokning upptar `[start, slut + efterarbete]` på sin dag. Ett kandidatpass (`CandidateSlot`) påverkas om dess intervall inkl. för- och efterarbete överlappar.
3. **Kapacitetsreduktion per pass**: för pass som påverkas minskas tillgänglig kapacitet med bokade platser. I modellen blir det antingen
   - `Room.slot_capacity[slot_id]` (reducerad kapacitet för just det passet), när sal är angiven i bokningen, eller
   - en adressgemensam kapacitetsrestriktion `sum(platser i byggnaden och passet) ≤ byggnadens kapacitet − fast bokade platser`, när bara adress är känd.
   Sal- och formatvillkor (digital kompatibilitet, delning mellan byggnader) gäller som förut för resten.
4. **Tre lägen som användaren väljer och som står i resultatet** (`planning_basis`):
   - `exploratory` (nuvarande): inga externa bokningar. Märkt som explorativt.
   - `bookings_respected`: fasta bokningar spärrar enligt ovan. Bokningar med oklar koppling behandlas som fasta (försiktigt: de tar plats), och antalet redovisas.
   - `bookings_unavailable`: bokningsdata saknas för perioden eller adressen. Körningen är tillåten bara som explorativ, och **ingen sal kallas tillgänglig**.
5. **Täckning**: bokningar finns till augusti men deltagarantal bara till mars. Bokningsläget kräver bokningsdata för hela perioden; saknas den är läget `bookings_unavailable`. Saknad bokning betyder okänd, inte tom.
6. **Eftervalideringen** (`joint_validation/`) får en regel som kontrollerar att ingen placering överskrider den reducerade kapaciteten, med samma indata som motorn och oberoende kontroll av överlappet. Utan fasta bokningar i indata blir regeln `not_applicable` med skälet, inte `pass`.
7. **Jämförbarhetsnyckel**: läge, bokningsdatas hash och periodens datum ingår, så att körningar med olika förutsättningar inte jämförs.
8. **Resultatvisning**: resultatet visar fasta bokningar per sal/pass som skild kategori från optimerade tentor och ett uttryckligt "Verifierad mot bokningar: ja/nej/delvis".

### Begränsningar och öppna beslut (för verksamhetsägaren)

- Status "Under behandling" och "Andring begard": spärra eller inte?
- Vad som är tillgängligt utöver tentamensbokningar (undervisning, andra bokningar) finns inte i underlaget; då kan inte en sal kallas ledig. Kravet är därför "inte i konflikt med kända bokningar", aldrig "ledig".
- Bokningar utan sal: acceptabelt med adressnivå?
- Hur ändrade eller flyttade bokningar efter dataexporten hanteras (aktualitet på bokningsdata).
- Reservdatum (`reserve_date_1/2`) är önskemål, inte bokning, och ska inte spärra.

### Föreslagen ordning vid implementation

1. Bygga fasta bokningar ur `bookings.csv` med länkning och status, med enhetstester på syntetiska rader (överlapp, avbokad, ingen sal, oklar koppling).
2. Kapacitetsreduktion i indata och motor; differentialtest mot eftervalideringen.
3. Läge i gränssnittet och i `planning_basis`; ändra texten "Explorativ planering" till det faktiska läget.
4. Mätning om körtiden påverkas (kapacitetsrestriktioner per adress och pass).

## 4. Verifiering

- Python: `tests/test_joint_period.py` (täckning, kontroll, kantfall, scenariokopia, unika id:n) och `tests/test_joint_period_run.py` (dag och vecka mot riktigt underlag med oberoende räkning, märkning, ojämförbara perioder, avvisning).
- Frontend: `frontend/src/lib/period.test.ts`.
