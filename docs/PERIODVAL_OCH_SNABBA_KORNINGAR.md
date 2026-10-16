# Valbar planeringsperiod, snabba körningar och redan lagda bokningar

**Dokumenttyp:** teknisk referens och kvarstående design.
**Status:** periodval och korta körningar är implementerade. Steg 3, hänsyn
till redan lagda bokningar utanför optimeringspopulationen, är **designat men
inte implementerat**.

Kravunderlag: `docs/KONCEPTUELL_KRAVSPECIFIKATION.md` (UX-9, §11.8, §11.9) och `docs/KRAV_OCH_STATUS.md`. Hela terminen är **inte** minsta planeringsenhet: datatäckningen och användarens val styr perioden.

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

Hur ett resultat får läsas (`planning_basis`) **härleds** i stället för att vara en konstant: resultatet är explorativt så länge något skäl gäller och tillförlitligt först när inget gör det. Skälen (`reasons`) kommer från motorn och datat: (1) motorn modellerar inte bokningar utanför de valda tentorna (`ENGINE_MODELS_EXTERNAL_BOOKINGS`), så ett resultat **inte visar att en sal är ledig i verkligheten**; (2) salar som inte är godkända för operativ planering i salsregistret (`eligible_for_operational_scheduling`), räknat på de salar körningen använde; (3) provisorisk efterfrågan. Idag gäller alla tre, så alla körningar är explorativa; ändras motorn eller registret ändras läget utan kodändring här. Skälen visas i resultatvyn.


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

## 3. Steg 3 – hänsyn till redan lagda bokningar (implementerat i `joint_reservations.py`, `joint_blocking.py`)

**Status:** implementerat för bokningar som identifierar en sal i modellen: de spärrar salen hel under sin tid plus ställtid och gör att salen räknas som använd (`reservations.policy`, standard `block_identified`). Oidentifierade bokningar spärrar ingenting och redovisas (antal, platser). Policyerna `sensitivity_bounds` och `refuse` nedan är inte implementerade. Texten nedan är den ursprungliga designen, kvar som motivering.

Detta avsnitt ersätter ett tidigare utkast som föreslog kapacitetsreduktion per adress när salnamn saknas. Det utkastet gjorde en datalucka till ett modellantagande och är struket. Utgångspunkten är `docs/ARKITEKTURPRINCIPER_DATAKVALITET.md`: modell och datakvalitet hålls isär, saknade uppgifter hanteras explicit, och inget antas tyst.

### Problemet

Vid planering av en kort period väljs en delmängd tentor ut för optimering. Andra bokningar i samma period tar plats i salarna. Idag modelleras varje sal som fri alla pass där den är öppen (`Room.available_slot_ids`, byggd av `_rooms` i `joint_inputs.py`). Därför kan ett resultat visa en lokal som ledig fast den är bokad. Det är acceptabelt för **explorativa snabbtester** (och märks som sådant, se avsnitt 1) men inte för **verklig korttidsplanering**.

### Grundregel

**Avsaknad av salnamn är en uppgift om datat, inte om verksamheten.** Den leder aldrig automatiskt till att en sal, flera salar eller en adress spärras eller får reducerad kapacitet, och den leder aldrig automatiskt till att en sal räknas som ledig. En bokning får bara påverka planeringen på den detaljnivå som data eller en verifierad uppgift faktiskt styrker.

### Vad modellen ska ta emot: reservationer

Optimeringen får inte läsa bokningsrader. Den tar emot **reservationer** som ett fristående lager (datakvalitets- och klassificeringslagret) byggt ur bokningarna:

`Reservation { resurs, tid, platser, grund }`

- `resurs` är `rum` (en identifierad sal), `adress` (endast när en **verifierad deklaration** säger att bokningen avser adressen eller en pool av platser där) eller `oidentifierad`.
- `grund` anger vad som styrker identifieringen: matchad sal i salsregistret, eller en namngiven verifierad regel i konfigurationen. En regel utan verifiering räknas inte som grund.

Lagret bedömer fyra **oberoende** dimensioner per bokning (de är inte ömsesidigt uteslutande tillstånd): resursidentifiering, datakvalitet, källtäckning och kopplingssäkerhet. Se arkitekturdokumentet och `src/tentaoptimering/booking_quality/`.

### Hur reservationer får påverka planeringen

| Reservation | Påverkan på planeringen |
|---|---|
| `rum`, identifierad sal | Salens kapacitet reduceras (eller salen spärras) under de pass som bokningen överlappar, inklusive för- och efterarbete. |
| `adress` med verifierad deklaration | Endast enligt deklarationens egen regel (till exempel en pool av platser på adressen). Regeln kommer från verksamhetsägaren, inte från att salnamn saknas. |
| `oidentifierad` (adress men ingen identifierad sal, namngiven sal som saknas i registret, adress saknas) | **Ingen spärr och ingen reduktion.** Upptagenheten är okänd och redovisas: antal bokningar, platser och tid. Resultatet märks med att okänd upptagenhet finns. |
| Bokningar som inte avser en fysisk lokal enligt en verifierad regel | Ingen spärr. |

### Okänd upptagenhet: policy, inte antagande

Hur okänd upptagenhet hanteras är en **policyparameter** per planeringsläge, inte en inbyggd modellregel (`bookings.unidentified_policy`):

- `ignore_flagged` (standard, explorativt läge): ingen spärr; resultatet bär en redovisning av vad som är okänt.
- `sensitivity_bounds` (explorativt läge, valfritt): resultatet beräknas även mot ett *känslighetsfall* där de oidentifierade bokningarna spärrar alla salar på sin adress under sin tid. Det är en redovisad gräns för hur mycket okänd data kan betyda, inte en tolkning av verksamheten och aldrig det resultat som kallas planeringen.
- `refuse` (tillförlitligt läge): körningen nekas över en tröskel som verksamhetsägaren fastställer.

Planeringsläget (`planning_basis`, härlett i avsnitt 1) bestämmer vilken policy som får användas. Ett resultat kallas tillförlitligt först när alla villkor för det läget är uppfyllda.

### Vad som inte antas

- Att bokningar utan salnamn på en viss adress är adressbokningar. Det kräver en verifierad deklaration från dataägaren.
- Att en viss bokningsstatus (till exempel "Under behandling") betyder att sal tilldelas senare. Statusar klassas bara enligt verifierad konfiguration.
- Att lokala registreringsmönster i dagens uttag är generella verksamhetsregler.

### Förutsättningar innan implementation

1. Klassificeringslagret är på plats och granskat mot ett bättre bokningsuttag.
2. Verksamhetsägaren har besvarat frågorna i `docs/FRAGOR_TILL_DATAAGARE.md`.
3. Policyparametrarna är beslutade (trösklar, vilket läge som krävs för vilken användning).
4. Testmatrisen i arkitekturdokumentet (S-A–S-F) körs mot lagret, och sedan mot motorn när den börjar läsa reservationer.

Motorn ändras inte förrän dessa punkter är uppfyllda.

## 4. Verifiering

- Python: `tests/test_joint_period.py` (täckning, kontroll, kantfall, scenariokopia, unika id:n) och `tests/test_joint_period_run.py` (dag och vecka mot riktigt underlag med oberoende räkning, märkning, ojämförbara perioder, avvisning).
- Frontend: `frontend/src/lib/period.test.ts`.
