# Parameterkatalog v1 (utkast för godkännande)

**Status:** S0-utkast. Innehåller bara parametrar som den första leveransens motor faktiskt läser (regel P-1 i kravspecifikationen §11.3). Varje post har ett effektfall som blir ett automatiserat test i S1/S2. Parametrar som kraven nämner men som saknar motorstöd listas i avsnitt 8 och visas inte i appen.
**Ersätter:** `config/parameters.toml`, `_TERM_PARAMETER_BINDINGS`, `[[assumption]]`-blocken och scenariofilernas nycklar.

## 1. Regler för katalogen

1. **En definition per parameter.** id, grupp, etikett, enhet, typ, gränser, hjälptext, standardvärde, standardgrund, `honored_by`, effektfall.
2. **Värde och grund.** Grund är *Verifierad*, *Hämtat ur data*, *Antagande* (motivering krävs) eller *Experiment*. Användaren kan aldrig sätta *Verifierad*.
3. **Ändring av ett verifierat värde** ger automatiskt grunden *Experiment*; återställning ger tillbaka *Verifierad*. Samma gäller *Hämtat ur data*.
4. **Nya simuleringar startar som Nuläge.** Standardvärdena för flexibilitet är avstängda, så en ny simulering är identisk med Nuläge tills användaren ändrar något.
5. **En parameter visas bara om motorn läser den.** `honored_by` anger modul och funktion. Ett katalogtest kräver ett effektfall per aktiv post.
6. **Grupperingen följer verksamhetsfrågor**, inte moduler: *Efterfrågan*, *Tidsflexibilitet*, *Regler*, *Mål*, *Lokaler*, *Bemanning*, *Kostnadsantaganden*.

## 2. Efterfrågan

| id | Etikett | Typ, enhet | Gränser | Standard (grund) | Läses av | Effektfall |
|---|---|---|---|---|---|---|
| `demand.variation_pct` | Förändrat antal tentander | heltal, % | -90..+200 | 0 (Experiment) | `planning_problem.scale_demand` | 100 tentander -10 % → 90; platstoppen ändras monotont |
| `demand.rounding` | Avrundning | val: uppåt / närmaste / nedåt | - | uppåt, minst 1 (Antagande: konservativt, ingen tentamen försvinner) | `scale_demand` | 7 tentander -10 % → 7 (uppåt), 6 (närmaste), 6 (nedåt) |

Efterfrågemåttet är fast **registrerade tentander** och redovisas som information (*Hämtat ur data*), inte som parameter. Bokade platser och närvaro är inte efterfrågemått (kravspecifikationen N-8).

## 3. Tidsflexibilitet

| id | Etikett | Typ, enhet | Gränser | Standard (grund) | Läses av | Effektfall |
|---|---|---|---|---|---|---|
| `window.earlier_days` | Får tidigareläggas | heltal, dagar | 0..365 | 0 (Antagande: ingen flytt) | `time_placement.occasions_for` | Två lika tentor samma tid: fönster 0 → topp 200; ±1 → 100 |
| `window.later_days` | Får senareläggas | heltal, dagar | 0..365 | 0 (Antagande) | samma | Asymmetriskt fönster ger bara senareläggning |
| `calendar.weekdays` | Tillåtna veckodagar för flyttade tentor | mängd av 1..7 | minst en dag | alla sju (Antagande: ingen policy angiven) | samma | Lördagstenta flyttas till tillåten dag inom fönstret |
| `calendar.blocked_ranges` | Spärrade perioder | lista av datumintervall | inom termin | tom (Antagande) | samma | Tenta i spärrad period flyttas ut |
| `calendar.start_times` | Tillåtna starttider vid flytt | lista av klockslag | 06:00..20:00 | tom = bara originalstart (Antagande) | samma | Tenta byter 14:00 till 08:00 när det sänker toppen |
| `flex.movable_types` | Tentamenstyper som får flyttas | mängd: ordinarie, omtenta, dugga, hybrid, hemtenta | - | alla (Antagande; fönstret styr) | samma | Bara omtenta flyttbar → ordinarie ligger kvar |
| `calendar.turnaround_minutes` | Ställtid mellan tentor i samma sal | heltal, minuter | 0..180 | 30 (Antagande, ej verifierad) | `time_placement.load_windows`, `room_realization` | 08:00-12:00 och 12:15-16:00: ställtid 30 → överlapp, 0 → inte |

Tentor som inte är flyttbara behåller sitt historiska tillfälle. Studentkrockar styr inte optimeringen (kravspecifikationen N-4).

## 4. Regler

| id | Etikett | Typ | Standard (grund) | Läses av | Effektfall |
|---|---|---|---|---|---|
| `rules.keep_course_order` | Behåll ordningen mellan tentor i samma kurs | ja/nej | ja (Antagande) | `time_placement.constraints` | Omtenta hamnar aldrig före ordinarie tenta i samma kurs |

Samma kurskod får aldrig överlappa i tid (fast regel, ingen parameter).

## 5. Mål

| id | Etikett | Typ, enhet | Gränser | Standard (grund) | Läses av | Effektfall |
|---|---|---|---|---|---|---|
| `objective.mode` | Mål | val: minimera platstopp / klara givet platstak med färre flyttar | - | minimera platstopp | `time_placement.objective` | Läge 2 med tak över optimum ger färre flyttar än läge 1 |
| `objective.capacity_cap_seats` | Platstak | heltal, platser | 1..20 000 | tomt | `time_placement.constraints` | Tak under optimum → "kan inte uppfyllas" med bästa möjliga topp |
| `objective.peak_tolerance_pct` | Accepterad marginal på platstoppen | heltal, % | 0..50 | 0 (Antagande) | `time_placement.objective` | 5 % marginal ger ≤ antal flyttar jämfört med 0 % |
| `solver.time_limit_seconds` | Längsta beräkningstid | heltal, sekunder | 5..3 600 | 60 | `time_placement.solve` | Kort gräns ger status "bästa funna" med redovisat gap |
| `solver.seed` | Slumpfrö | heltal | - | 20261009 | `time_placement.solve` | Samma frö → identiskt resultat |
| `analysis.curve_days` | Dagvärden i flexibilitetskurvan | lista av heltal, dagar (symmetriska fönster) | 0..365, fritt antal | **0, 1, 2, 3, 5, 7 som förslag, fritt ändringsbara** | `analysis.flexibility_curve` | Egna värden (till exempel 4, 10, 21) ger kurvpunkter exakt där; förvalen begränsar inget |

Flexibilitetskurvan är en analysfunktion: för varje angivet dagvärde körs samma kedja med fönstret satt symmetriskt till det värdet, övriga parametrar oförändrade. Förvalda punkter är bara förslag.

## 6. Lokaler

| id | Etikett | Typ, enhet | Standard (grund) | Läses av | Effektfall |
|---|---|---|---|---|---|
| `rooms.selection` | Lokaler som får användas | mängd ur Dataunderlaget | de åtta salar med publicerad kapacitet (Hämtat ur data: publicerad, ej verifierad för perioden) | `room_realization.rooms` | Bort-valda salar används inte; brist visas om kapaciteten inte räcker |
| `rooms.capacity_override` | Egen kapacitet för vald sal | per sal, heltal | ingen (Experiment/Antagande, motivering krävs) | samma | Höjd kapacitet minskar brist |
| `rooms.custom_rooms` | Egen lokal | namn, ort, kapacitet | inga (Experiment) | samma | Tillagd lokal kan användas av realiseringen |
| `rooms.max_rooms_per_exam` | Högsta antal salar per tentamen | heltal | 8 (Antagande) | `room_realization.pack` | 1 → tenta större än största sal kan inte realiseras |

Lokaler utan publicerad kapacitet (Danmarksgatan 30, Fyrishov hall D-F) är ett datagap och finns inte som alternativ förrän verksamheten angett kapacitet. Observerad största bokning visas som kontext per lokal.

## 7. Bemanning

| id | Etikett | Standard (grund) | Källa / anmärkning |
|---|---|---|---|
| `staffing.ladder` | Antal vakter per deltagare i en sal (tabell) | 1 till 50, 2 till 150, 3 till 300 (Antagande) | Avtalet reglerar inte bemanning |
| `staffing.shifts` | Arbetspass (tabell) | 07:30-18:30 (Antagande) | Ej i avtalet |
| `staffing.preparation_minutes` | Förberedelse före tenta | 30 (Antagande) | Ej i avtalet |
| `staffing.closing_minutes` | Avslut efter tenta | 30 (Antagande) | Ej i avtalet |
| `staffing.min_break_minutes` | Rastens längd | 30 (Antagande) | Längd anges inte (§2.5) |
| `staffing.max_continuous_minutes` | Längsta pass utan rast | **300 (Verifierad)** | UFV-PA 2023/4939 §2.5: rast ska läggas ut vid pass längre än fem timmar |
| `staffing.max_daily_minutes` | Längsta arbetstid per dygn | 660 (Antagande) | Centralt Villkorsavtal-T 4 kap. 5 §, ej i underlaget |
| `staffing.min_daily_rest_minutes` | Minsta dygnsvila | 660 (Antagande) | Samma |
| `staffing.travel_minutes` | Restid mellan byggnader | 30 (Antagande) | Ej i avtalet |
| `staffing.min_paid_shift_minutes` | Kortaste betalda pass | **120 (Verifierad)** | UFV-PA 2023/4939 §2.2; påverkar betald tid, inte närvarotid |

Alla läses av `staffing.plan_staffing` eller resultatmodellens tidsredovisning. Effektfallen finns i `test_staffing` och utökas med betald tid.

## 8. Kostnadsantaganden (valfria)

| id | Etikett | Standard | Läses av | Effektfall |
|---|---|---|---|---|
| `cost.annual_per_seat` | Årskostnad per lokalplats, kr | **ej angiven** | `result.cost_profile` | Utan värde visas ingen modellkostnad; med värde visas "modellkostnad enligt antaganden" |
| `cost.annual_per_staff` | Årskostnad per vakt, kr | **ej angiven** | `result.cost_profile` | Samma |

Kostnadsvärden har ingen förinställd siffra; de tidigare proxyerna (1 000 kr per plats, 50 000 kr per vakt) tas inte med. Modellkostnad är ett efterberäknat mått, inte optimeringsmål.

## 9. Utanför katalogen (saknar motorstöd)

Visas inte i appen. Redovisas i `docs/KRAVUPPFYLLNAD.md` som *saknas*, med förutsättning:

| Behov | Förutsättning |
|---|---|
| Digital andel, digital kompatibilitet per sal | Kompatibilitet per sal; klassning av tentor |
| Externhyra, ersättningslokaler | Hyresdata, kapacitet och tillgänglighet |
| Max skrivtid, ändrade examinationsvillkor | Motorstöd för varierande längd |
| Studentkrockskontroll | Student- eller programöverlapp |
| Tentamensperioder, omtentaintervall | Fastställda regler |
| Personalkostnad i tid och bomtid, helggränser per vakt | Avtal om obekväm tid, lönenivåer, vakternas anställningsform (se `ANALYS_KOLLEKTIVAVTAL.md`) |
| Årsfaktor, annualisering | Efterfrågeprofil för övriga terminer |
| Särskilt stöd | Utanför omfattningen enligt kravspecifikationen |

## 10. Omfattning (information, inte parametrar)

Följande visas i Dataunderlagets omfattningspanel men kan inte ändras i en simulering: efterfrågemått (registrerade), beräkningsbar population (1 258 tentor), delade tillfällen (separat redovisade), kvarstående datagap, regeln "lokal används" (härledd ur bokningen).
