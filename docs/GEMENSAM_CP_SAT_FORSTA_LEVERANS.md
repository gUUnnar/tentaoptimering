# Första leverans – gemensam CP-SAT-kärna

Detta dokument beskriver kärnan efter kodgranskningen av PR #7. Det anger faktisk omfattning, uppmätt prestanda och kvarstående begränsningar.

## Levererat

Kärnan använder ett versionsmärkt kontrakt (`joint-optimization-input-v2`, `joint-optimization-result-v2`) och optimerar i samma CP-SAT-problem:

- val av datum och starttid bland uttryckliga kandidater;
- hela deltagarvolymen för varje tentamensbehov;
- användning och kostnad för faktiska salar;
- fysisk kapacitet, ort, digital kompatibilitet och rumstillgänglighet;
- samlokalisering, uppdelning, byggnadsregel och ställtid;
- regelberäknat vaktbehov per aktivt salstillfälle och dimensionerande anonym samtidig pool;
- fast lokalårskostnad, årlig poolkostnad och rörlig kostnad per vaktsalstillfälle. Externa salstillfällen kostnadssätts i optimeraren men saknar datakälla och är `contract_only`.

Kostnaden minimeras först. Endast när minsta kostnad är bevisad låses den och en andra solve minimerar antalet ändrade tentamenstillfällen. En lösning kan aldrig få lägre kostnad genom oplacerad efterfrågan.

## Rättelser efter granskningen

| Fynd | Åtgärd | Test |
|---|---|---|
| `calendar.start_times` påverkade inte kandidatpassen (passen låg i en dold `[[calendar.pass]]`-tabell) | Kandidater genereras ur `calendar.start_times`, `calendar.earliest_start_time`, `calendar.latest_end_time`, `calendar.start_date/end_date`, `calendar.weekdays` och `calendar.blocked_ranges`. Dolda pass är borttagna | `test_slots_follow_start_times_not_a_hidden_pass_table` |
| Historiskt tillfälle lades tyst till som kandidat, och 73 av 1 259 verkliga tentor gav `ValueError` | Det historiska tillfället bevaras som referens (`original_date`, `original_start_minute`). Det är kandidat bara om det uppfyller användarens inställningar. Oflyttbara tentor behåller sitt historiska tillfälle som markerat referenspass (`reference_only`). En flyttbar tentamen utan tillåtet tillfälle ger ett `infeasible`-resultat med blockerande krav, inte ett krasch | `test_original_occasion_outside_user_settings_is_a_reference_not_a_candidate`, `test_fixed_exam_keeps_history_…`, `test_movable_exam_without_any_allowed_occasion_blocks_…` |
| `supports_e_exam` tolkades som saknat digitalstöd; okänd digital status blev papper | Salar har `digital_support_basis` (`all_places`, `some_places_unquantified`, `unknown`). Salar med `supports_e_exam` tar digitala tentor under `digital.partial_support_policy` (standard `allow_unverified`). Saknad eller blandad digital status kräver digitalkapabel sal (`digital.unknown_demand_policy`) och flaggas. Resultatet påstår aldrig verifierad kompatibilitet | `DigitalAndGroupTests` |
| Externhyresparametern var `implemented` men adaptern satte kostnaden till noll | Parametern är `contract_only`. Ett ändrat värde ignoreras och listas i resultatets begränsningar | `test_contract_only_parameters_never_change_the_model_but_are_reported_when_edited` |
| Sammanslaget källvärde `Ja \| Nej` tolkades som okänt och kunde bli papper | Värdet delas i token (`\|`, `,`, `;`, `/`) innan klassning. `Ja` och `Nej` tillsammans är alltid `e_exam` med grund `observed_mixed`, oavsett policy. Okänt eller oigenkännligt följer den uttryckliga policyn och märks `unobserved`. Rader som uttalar både Ja och Nej och ett enda sammanslaget värde behandlas lika | `DigitalValueParsingTests`, `merged_ja_nej_is_digital_even_when_unknown_is_paper` |
| Samtentor summerade aktiviteter utan att visa antagandet | Deltagare summeras, men behovet märks `assumed_disjoint_groups_sum` och resultatet anger att disjunkthet inte är verifierad. Underlag: i huvudpopulationen har alla 79 samtentor olika kurskoder och summan registrerade är 0,74 av bokade platser (4 av 79 överstiger bokade platser, 12 platser sammanlagt). Det stöder summering men bevisar inte att grupperna är disjunkta | `test_shared_exam_sums_groups_but_records_unverified_disjointness` |
| Parametrar försvunnit mellan gammalt och nytt register | Varje gammal parameter har en katalogpost via `legacy_ids`. Katalogen har 53 poster (30 `implemented`). Nya poster: tidigaste/senaste tid, datumgränser, efterfrågemått, delning över salar, digitala policyer, mål, särskilt stöd, undvikbara kostnader m.fl. | `test_catalog_keeps_every_legacy_parameter_or_a_declared_counterpart` |
| `implemented` utan bevis | Två nivåer. (1) Indata: ett effekttest per implementerad parameter kräver att modellen optimeraren får ändras. (2) Resultat: `tests/test_joint_optimization_effects.py` har handräknade optimeringsfall (tvåtentafallet, facit 7 000 / 8 000 / 13 000 / 14 000 öre eller `infeasible`) och ett test som kräver att varje implementerad parameter bevisats på ett optimeringsresultat. Kontrollerat med 17 konstgjorda fel i optimerare och adapter; alla fångas (en första körning missade förberedelse- och avslutstid var för sig, vilket rättades med gränsfall på 15 och 16 minuter) | `test_every_implemented_parameter_has_an_effect_case_and_changes_the_model` |
| Ramverk läste råa scenarionycklar | Adaptern läser bara frusna värden; ett test kräver exakt en läsning av `config["parameters"]` | `test_frozen_values_not_raw_scenario_keys_…` |
| Föråldrad paketinstallation | `.venv` hade en gammal kopia av paketet i `site-packages`. Ersatt med `pip install -e .`; testerna körs nu mot `src` utan `PYTHONPATH` | `tentaoptimering.__file__` pekar på `src` |

Heltalsavrundning av deltagarantal sker med exakt heltalsaritmetik.

## Verifieringsstatus i varje resultat

Varje resultat har ett block `verification`:

- `solver`: `optimal_proven` eller `feasible_not_proven` (solverns eget påstående, inget oberoende bevis);
- `independent_validation`: **`not_performed`**. Resultatet är solververifierat men inte oberoende eftervaliderat; den fristående valideraren för den nya resultattypen återstår;
- `digital_compatibility`: `assumed_not_verified: …` när digitala behov ligger i salar med okvantifierat stöd, annars `consistent_with_published_room_support_not_verified_for_period`;
- `group_disjointness`: `assumed_not_verified` för samtentor;
- `student_overlap`: `not_evaluated`.

Samma status skrivs i `joint_report.md`.

## Solverstatus

| Utfall | Betydelse |
|---|---|
| `optimal` | Fullständig lösning finns och minsta jämförbara kostnad är bevisad. |
| `feasible_not_proven` | Fullständig lösning finns men kostnadsoptimum är inte bevisat. |
| `infeasible` | Hela modellerade efterfrågan kan inte placeras, bevisat av CP-SAT eller före lösning (tentamen utan tillåtet tillfälle). |
| `no_feasibility_conclusion` | Varken fullständig lösning eller bevis på ogenomförbarhet. |

## Skalbarhet: vad orsakar gapet?

**Principen:** ett gap på 56 procent betyder att solvern inte kunnat utesluta väsentligt billigare lösningar. Det säger inte att den funna lösningen är 56 procent för dyr. Gapet består av två delar: lösningen kan ligga över optimum, och gränsen kan ligga under optimum. Mätningarna skiljer dem åt.

**Mätuppställning:** Uppsala, sju salar med publicerad kapacitet (1 119 platser), första vecka 12–16 januari 2026, fönster ±1 dag, starttider 08:00 och 14:00, tio kandidatpass, ställtid 30 minuter, kostnadsproxyer 1 000 kr per plats och 50 000 kr per vakt. Mått tagna med skript i scratchpad (`scale.py`, `product_run.py`) mot modellbyggaren; ingen ändring av optimeringskraven.

**Modellstorlek är inte flaskhalsen.**

| Tentor | Variabler | Restriktioner | Byggtid |
|---|---:|---:|---:|
| 60 | 5 148 | 17 501 | 0,1 s |
| 120 | 9 633 | 33 410 | 0,2 s |
| 246 | 19 218 | 67 449 | 0,5 s |
| 1 172 (hela terminen, ±1 dag, 158 pass) | cirka 90 000 (uppskattat) | – | 3,9 s för indata + validering (ingen lösning körd) |

**Gapets sammansättning (60 tentor).** Bevisat optimum med gränsskär och åtta trådar: 50,9 M öre.

| Körning (90 s) | Funnet mål | Bästa gräns | Gap | Lösning över optimum | Gräns under optimum |
|---|---:|---:|---:|---:|---:|
| 1 tråd, utan skär | 55,8 M | 27,0 M | 51,6 % | +9,6 % | −47 % |
| 8 trådar, utan skär (3 frön) | 53,0–55,8 M | 42,0–42,4 M | 20–25 % | +4…+10 % | −17 % |
| 8 trådar + skär (3 frön) | 50,9 M (bevisat optimum i 2 av 3) | 50,9 M | 0 % | 0 % | 0 % |

Av ett gap på 51,6 procent (1 tråd) beror 8,8 procentenheter på att lösningen ligger över optimum och 42,8 på att gränsen ligger under. Cirka 83 procent av gapet är alltså en svag gräns, inte ett dåligt schema. Lösningen hittas inom sekunder (första fullständiga lösning efter 3–5 s; bättre lösningar efter 10–30 s).

**Större fall (optimum okänt, resultat från samma körningar).**

| Tentor | Konfiguration | Första lösning | Funnet mål | Bästa gräns | Gap |
|---|---|---:|---:|---:|---:|
| 120 | 1 tråd, 180 s | 31 s | 156,3 M | 0 | 100 % |
| 120 | 8 trådar utan skär, 120–180 s (3 körningar) | 8–9 s | 116,5–119,3 M | 74–103 M | 14–36 % |
| 120 | 8 trådar + skär, 120–180 s (4 körningar) | 8–10 s | 119,3–123,4 M | 94–103 M | 16–23 % |
| 160 | 8 trådar utan skär, 150 s | 37 s | 159,0 M | 86,6 M | 45 % |
| 160 | 8 trådar + skär, 150–240 s | 24 s | 145,9 M | 132,0 M | 9,5 % |
| 246 | 8 trådar | – | – | – | **infeasible** bevisat på 14–21 s |

Lösningarna för samma storlek ligger inom några procent av varandra (120 tentor: 116,5–123,4 M mellan frön och konfigurationer), medan gränsen varierar kraftigt. Det tyder på att resterande gap vid 120–160 tentor till stor del är en gränsfråga, men optimum är inte bevisat där, så fördelningen kan inte kvantifieras.

**246 tentor (hela veckan) är ogenomförbart av kapacitetsskäl, inte av skalning.** Veckan har 11 704 deltagare att placera, och sju salar med 1 119 platser i tio pass rymmer högst 11 190. Det speglar att historiken även använde Danmarksgatan 30 och Fyrishov, som saknar kapacitetsuppgift i registret (datagap).

**Vad som hjälpte och vad som inte gjorde det.**

| Åtgärd | Effekt |
|---|---|
| Åtta trådar i stället för en | Bästa gräns 27,0 M → 42 M (60 tentor) och 0 → 103 M (120 tentor). Standard `solver.workers = 8` |
| Linjära bemanningsskär (`joint_optimizer.staffing_cut_edges`): nedre konvex hölje av trappan i `staff ≥ …·occupancy` | Giltiga olikheter (testade för varje beläggning). Bevisat optimum i 2 av 3 frön för 60 tentor; gap 45 % → 9,5 % för 160 tentor. Neutral för lösningskvaliteten vid 120 |
| Reproducerbar parallell sökning (`interleave_search`) | 2–4 gånger sämre gräns och lösning vid 120–160 tentor (gap 34,7 % mot 9,5 % för 160). Därför är `solver.deterministic = false` standard; sant ger identiskt resultat för samma indata, frö och trådantal (bekräftat på 40 tentor) |
| Fasta originaltillfällen (alla tentor oförändrade) | Löses bevisat optimalt på 6 s men ger 93,3 M mot optimum 50,9 M. Visar att flexibiliteten ger cirka 45 procent lägre modellkostnad i 60-tentorsfallet, med proxykostnader |

**Slutsats om väg framåt.** Lösningsfas och modellstorlek är inte begränsande upp till minst 160 tentor; bevisfasen är det. Hela terminen (cirka 1 170 tentor) är inte löst i denna PR och ingen sådan körning har gjorts; det som är mätt är att indata och validering byggs på 4 sekunder och att den uppskattade modellstorleken är runt 90 000 variabler. Närmast prövbara steg: veckovis nedbrytning med gemensam lokalportfölj, startlösning från föregående vecka, fler skär för poolen. Inget av detta är mätt ännu.

## Handräknade referensfall

`tests/test_joint_optimizer.py` innehåller oberoende småfall med exakta svar:

- två 40-personers tentor väljer en större sal för 600 öre och en vaktpool för 1 000 öre (1 600 totalt), eftersom två småsalar skulle kräva två samtidiga vakter (2 200);
- 25 deltagare i två delgrupper placeras som exakt 25;
- lika ekonomisk kostnad bevarar originalpasset;
- 60 deltagare, en 50-platsers sal och max en sal ger `infeasible`, aldrig en dellösning;
- digitalt krav använder bara digital sal; samma kurs tvingas till icke överlappande pass;
- 30 minuters ställtid accepterar nästa start exakt vid gränsen och avvisar en minut för tidigt;
- bemanningstrappa med flera steg: två 60-platsers salar (2 vakter, 2 110) mot en 120-platsers sal (3 vakter, 3 100); skären ändrar inte optimum.

## Avgränsat verkligt datafall

```powershell
.\.venv\Scripts\python.exe -m tentaoptimering.cli optimize-joint --config config\scenarios\joint_real_subset.toml
```

Konfigurationen namnger tolv verkliga bokningshändelser och tillåter tillfällen den 12–14 januari 2026 (datumgränser som parametrar). Endast Uppsalasalar med publicerad kapacitet används; Campus Gotland B40 filtreras bort av planeringsområde och tillgänglighetsdatum. Efter rättningarna är resultatet oförändrat: `optimal`, mål och gräns 37 900 000 öre, tre samtidiga anonyma resurser, fyra ändrade behov, 2,3 s.

Beloppen följer proxyer (1 000 kr per plats och år, 50 000 kr per poolresurs och år). De är varken faktisk kostnad, teoretisk besparing mot nuläge eller verifierad realiserbar besparing.

## Kvarstående begränsningar

- Omfattningen är ett utvalt delurval (12 tentor) och mätningar på upp till 160 tentor; ingen hel termin är löst.
- Ingen oberoende eftervalidering för den nya resultattypen (nästa steg).
- Bemanningen är en anonym samtidig pool; individuella pass, raster, vila, resor, bomtid, minsta betalda pass och helgregler är `contract_only`.
- Studentöverlapp, tentamensperioder, kursordning, annualisering och maximal skrivtid är `contract_only`.
- Digital kompatibilitet vilar på publicerade salstatusar (alla platser eller delvis) och är inte verifierad per plats.
- Samtentor: disjunkta deltagargrupper är ett antagande.
- Lokalinventariet (sju Uppsalasalar, 1 119 platser) är ett datagap för toppveckor (se 246-tentorsfallet).
- Tidsgränsen är väggtid; avbrutna körningar kan skilja mellan datorer.
- Den äldre konstruktiva motorn ligger kvar tills nödvändiga funktioner flyttats och ersättningen verifierats.
