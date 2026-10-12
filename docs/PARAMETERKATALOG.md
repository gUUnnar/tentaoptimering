# Parameterkatalog v2

**Status:** Implementerad kontraktskälla för den nya gemensamma optimeringsmotorn.
**Maskinläsbar källa:** `config/joint_parameter_catalog.toml` (`catalog_version = "2.3.0"`).

Det tidigare S0-beslutet att dölja parametrar utan motorstöd är upphävt. Alla definierade verksamhetsparametrar finns i samma katalog för framtida GUI, lagring, validering och motoranslutning. Varje post har ett av två tydliga stödtillstånd:

- `implemented`: värdet läses av angiven adapter- eller solverfunktion och har ett automatiserat effektfall.
- `contract_only`: värdet kan visas, redigeras, frysas och sparas, men påverkar ännu inte beräkningen. En körning listar alltid dessa parametrar som begränsningar; de får aldrig tolkas som kontrollerade krav.

Varje definition innehåller id, verksamhetsgrupp, etikett, typ, enhet, standardvärde, standardgrund, hjälptext, motorstöd, för valparametrar (`value_type = "choice"`) de tillåtna värdena i `choices` och – när stöd finns – `honored_by`. Körningskontraktet fryser dessutom värde, grund, motivering och motorstöd för varje parameter.

## Omfattning

Katalogen har 55 poster, varav 32 har motorstöd. Varje implementerad post har ett effektfall i `tests/test_joint_parameter_effects.py` som ändrar värdet och kräver att modellen optimeraren får ändras; en parameter som ignoreras fångas.

| Område | Parametrar med motorstöd | Definierade men utan motorstöd (`contract_only`) |
|---|---|---|
| Efterfrågan | variation, avrundning, efterfrågemått (endast registrerade) | säkerhetsmarginal |
| Kalender och flexibilitet | tidigare/senare dagar, veckodagar, starttider, tidigaste starttid, senaste sluttid, första/sista datum, spärrade perioder, ställtid, flyttbara typer | tentamensperioder, kursordning |
| Krockar | kurskod och explicita konfliktgrupper | individuella studentkrockar |
| Lokaler | urval, max salar per tenta, delning över salar, delning över byggnader | kapacitetsöverstyrning, egna lokaler, samlokaliseringsregler, tillgänglighetsläge |
| Digitalt | policy för salar med delvis digitalstöd, policy för okänd digital status | verifierad kompatibilitetsmatris, framtida digital andel |
| Bemanning | trappa, förberedelse och avslutning (anonym samtidig pool) | arbetspass, rast, arbetstid, vila, resa, minsta betalda pass |
| Kostnad | årskostnad per plats, årskostnad per pool, rörlig kostnad per vaktsalstillfälle | **externhyra per salstillfälle** (ingen datakälla för externa lokaler), annualisering, undvikbara kostnader |
| Mål och solver | tidsgräns, frö, antal trådar, reproducerbar parallell sökning, lösningsstrategi (`decomposed`/`monolithic`), tillräckligt gap för tidigt stopp | viktning av mål (motorn är lexikografisk) |
| Särskilt stöd | – | regler för särskilt pedagogiskt stöd |
| Examinationsvillkor | faktisk skrivtid per behov | experimentell maximal skrivtid |

## Redigering i gränssnittet

Gränssnittet hämtar katalogen med `GET /api/joint-runs/parameters?scenario=<id>`. Varje parameter levereras med standardvärde, scenariots värde och gällande värde, och bara parametrar med `engine_support = "implemented"` är redigerbara. Parametrarna listas i sex fasta grupper (tid och kalender, lokaler och digitalt, bemanning, kostnader, körning, efterfrågan och övrigt); gruppindelningen och ordningen ligger i `joint_parameters.py`, medan själva katalogen är oförändrad. Tekniska sökparametrar (frö, trådar, strategi, reproducerbarhet, gap) är markerade `advanced`.

- **Tillåtna val.** Varje `choice`-parameter anger sina val som en lista `choices = [{value = "up", label = "Uppåt ..."}, ...]` (svenska etiketter). Katalogen laddas inte om en valparameter saknar val eller om standardvärdet inte finns bland dem. Testerna kontrollerar att motorn godtar varje listat val och att den avvisar andra.
- **Validering.** `validate_overrides(katalog, ändringar)` (`parameter_validation.py`) används av körningsrutten och av rutten som sparar scenarier. Den avvisar okända parametrar, parametrar som är `contract_only` ("Stöds inte av motorn än"), värden av fel typ och orimliga intervall (heltal under noll, veckodagar utanför 1-7, klockslag som inte är HH:MM, en bemanningstrappa som inte stiger, ett första datum efter det sista) och svarar med `[{id, message}]`. Scenariofiler som läses från disk valideras inte på det sättet; deras värden är de tidigare frusna scenariovärdena.
- **Ändringar i en körning.** En körning kan få `parameters: {id: värde}` (bara ändringar jämfört med scenariot). De slås ihop med en kopia av scenariot, med motiveringen "Ändrat i gränssnittet." per ändrad parameter. Scenariofilen ändras aldrig och scenariots id behålls, så att jämförelse och varmstart mot föregående körning av samma scenario fungerar. Den scenariofil som faktiskt användes sparas i körningsmappen som `joint_scenario.toml`.
- **Egna scenarier.** `POST /api/joint-runs/scenarios` sparar ett scenario i mappen `joint_scenarios/` under appens datamapp (inte i den mapp som den äldre scenariosidan läser). Urvalet kopieras från basscenariot.
- **Jämförelse.** `GET /api/joint-runs/{run_id}/compare` visar vilka parametrar som skiljer och hur kostnad, undre gräns, gap, ändrade tentor, pool och salar skiljer. Kostnadsskillnaden tolkas bara om den är större än det största gapet av de två körningarnas gap. Körningar på olika dataunderlag eller olika tentamängd jämförs aldrig. Alla belopp är modellkostnad med scenariots proxypriser.

## Spårning mot det tidigare registret

Varje parameter i det tidigare registret (`config/parameters.toml`) och i terminsmotorns bindningar har en post här, angiven i `legacy_ids`. `test_catalog_keeps_every_legacy_parameter_or_a_declared_counterpart` kontrollerar att ingen försvinner. Ingen parameter har tagits bort för att motorstöd saknas.

## Grund och motivering

Tillåtna grunder är `verified`, `source_data`, `assumption` och `experiment`. Ett ändrat verifierat eller källhämtat värde fryses som `experiment`; ett justerat antagande förblir ett motiverat `assumption`. Att ett värde har grunden `verified` betyder inte att en resultatregel automatiskt är godkänd; regelstatus måste härledas av eftervalidering från databevis och faktiskt resultat.

Kostnadsstandarderna är noll för att undvika ett dolt ekonomiskt påstående. Den reproducerbara verkliga delmängdskörningen anger uttryckliga proxyer och motiveringar i `config/scenarios/joint_real_subset.toml`. De är modellantaganden, inte faktisk kostnad eller verifierad besparing.

## Effektfall

`tests/test_parameter_catalog.py` och `tests/test_joint_parameter_effects.py` kontrollerar att både stödda och ostödda parametrar exponeras och fryses med rätt stödstatus. `tests/test_joint_optimizer.py` visar bland annat att:

- efterfrågan inte kan lämnas delvis oplacerad;
- delgrupper räknas en gång även när en delgrupp har flera källaktiviteter;
- lokal- och bemanningskostnad kan ge ett annat optimum än billigaste lokalbeståndet ensamt;
- ekonomiskt likvärdiga lösningar väljer ursprungligt pass;
- digital kompatibilitet, kurskrock, salkapacitet och ställtid är hårda villkor.
