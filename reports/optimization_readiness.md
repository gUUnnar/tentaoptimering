# Optimeringsunderlag – databereddhet

Rapporten beskriver det maskinläsbara underlaget för en explorativ PoC-körning.
Den kör ingen optimering och redovisar ingen besparing.

## Mätvärden

| Mått | Värde |
|---|---:|
| `demand_measure_source_field` | registered_count |
| `booking_exam_events` | 5506 |
| `ladok_activities_total` | 1525 |
| `ladok_activities_with_candidate_key` | 1524 |
| `ladok_activities_without_candidate_key` | 1 |
| `ladok_activities_unambiguous_candidate` | 1285 |
| `ladok_activity_candidate_coverage_percent` | 84.3 |
| `ladok_activities_ambiguous_candidates` | 170 |
| `ladok_activities_without_booking_candidate` | 69 |
| `optimization_demands_ready_provisional` | 1259 |
| `optimization_demand_record_coverage_percent` | 82.6 |
| `optimization_demands_missing_configured_value` | 26 |
| `optimization_demand_sum_ready_provisional` | 46706 |
| `available_ladok_demand_sum` | 53076 |
| `available_ladok_demand_share_in_ready_inputs_percent` | 88.0 |
| `optimization_placements` | 2218 |
| `observed_booking_locations` | 18 |
| `published_room_reference_entries` | 13 |
| `published_room_capacities` | 8 |
| `published_total_places_claim` | 1446 |
| `sum_of_individually_listed_capacities` | 1220 |
| `published_capacity_reconciliation_gap` | 226 |
| `observed_rooms_with_published_capacity` | 7 |
| `rooms_with_verified_capacity` | 0 |
| `poc_policy_allows_current_published_capacity` | True |
| `optimization_rooms_ready_for_exploratory_poc` | 8 |
| `optimization_room_capacity_sum_ready_for_exploratory_poc` | 1179 |
| `poc_room_availability_mode` | candidate_inventory_without_calendar_guarantee |
| `capacity_optimization_readiness` | ready_for_exploratory_capacity_poc_with_explicit_uncertainty |
| `operational_scheduling_readiness` | blocked_missing_verified_availability_and_business_rules |
| `economic_savings_readiness` | blocked_missing_verified_cost_avoidability |
| `demands_with_any_identified_booking_room` | 1240 |
| `demands_with_published_room_capacity_reference` | 1098 |
| `ready_demands_with_published_room_capacity_reference_percent` | 87.2 |
| `ready_demands_with_any_identified_booking_room_percent` | 98.5 |

## Vad som nu kan användas i PoC:n

- 1259 Ladokaktiviteter (82.6 %) har en entydig kandidat till en provisorisk bokningshändelse och ett ifyllt `registered_count`.
- Dessa rader täcker 88.0 % av den tillgängliga summan i det provisoriska Ladokmåttet.
- Varje sådan efterfrågepost kan följas via `activity_id`, `exam_event_id` och `placement_id` till de historiska placeringarna.
- Det officiella referensregistret innehåller publicerad rumskapacitet för 8 rum; 7 av dem förekommer i bokningsperioden.
- `optimization_rooms.csv` innehåller 8 scenariorum med sammanlagt 1179 publicerade platser. De får användas för explorativ kapacitetsanalys enligt parameterregistret.
- Rummen är scenariokandidater utan kalendergaranti. En PoC får därför undersöka kapacitet, packning och känslighet men inte hävda att ett föreslaget schema är genomförbart.
- `room_inventory.csv` skiljer publicerad kapacitet från observerade bokade platser. De senare är historiskt utfall och aldrig en antagen kapacitet.

## Osäkerheter och kvarvarande spärrar för operativ användning

- De publicerade kapaciteterna kommer från en webbsida uppdaterad 2026-09-24 och är inte tidsverifierade för bokningsperioden 2025–2026. De används endast genom den uttryckliga PoC-regeln och är inte markerade som operativt verifierade.
- Webbsidan anger totalt 1446 platser, medan de individuellt angivna kapaciteterna summerar till 1220. Skillnaden på 226 platser måste förklaras av dataägaren.
- Bokningar visar historisk användning, inte en verifierad tillgänglighetskalender eller ett tillåtet framtida salbestånd.
- Kandidatkopplingen är teknisk och inte en verksamhetsverifierad nyckel; tvetydiga och omatchade aktiviteter exkluderas från efterfrågetabellen i stället för att fördelas godtyckligt.
- `registered_count` är ett provisoriskt registreringsmått enligt parameterregistret, inte faktisk närvaro.
- Lokal- och avtalsrader kopplas inte till rum utan en verifierad översättningstabell; inga kostnadsresultat kan härledas.

## Nästa konkreta steg

1. Kör och jämför versionshanterade scenarier mot `optimization_demands.csv` och `optimization_rooms.csv`, med antagandena synliga i varje resultat.
2. Utvärdera täckning, överkapacitet och ej placerbar efterfrågan som PoC-resultat, inte som ett operativt schema eller en besparing.
3. Bekräfta senare kapaciteternas giltighetsperiod, faktisk tillgänglighet och skillnaden mot sidans totalsumma före operativ användning.
4. Godkänn eller ersätt kandidatregeln och efterfrågemåttet när bättre verksamhetsdata finns.
5. Håll alla scenario- och verksamhetsregler justerbara i parameterregistret.

Kapacitetskälla: https://www.uu.se/medarbetare/stod-och-verktyg/lokaler/boka-tentamensplatser
