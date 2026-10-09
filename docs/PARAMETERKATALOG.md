# Parameterkatalog v2

**Status:** Implementerad kontraktskälla för den nya gemensamma optimeringsmotorn.
**Maskinläsbar källa:** `config/joint_parameter_catalog.toml` (`catalog_version = "2.1.0"`).

Det tidigare S0-beslutet att dölja parametrar utan motorstöd är upphävt. Alla definierade verksamhetsparametrar finns i samma katalog för framtida GUI, lagring, validering och motoranslutning. Varje post har ett av två tydliga stödtillstånd:

- `implemented`: värdet läses av angiven adapter- eller solverfunktion och har ett automatiserat effektfall.
- `contract_only`: värdet kan visas, redigeras, frysas och sparas, men påverkar ännu inte beräkningen. En körning listar alltid dessa parametrar som begränsningar; de får aldrig tolkas som kontrollerade krav.

Varje definition innehåller id, verksamhetsgrupp, etikett, typ, enhet, standardvärde, standardgrund, hjälptext, motorstöd och – när stöd finns – `honored_by`. Körningskontraktet fryser dessutom värde, grund, motivering och motorstöd för varje parameter.

## Omfattning

Katalogen har 53 poster, varav 30 har motorstöd. Varje implementerad post har ett effektfall i `tests/test_joint_parameter_effects.py` som ändrar värdet och kräver att modellen optimeraren får ändras; en parameter som ignoreras fångas.

| Område | Parametrar med motorstöd | Definierade men utan motorstöd (`contract_only`) |
|---|---|---|
| Efterfrågan | variation, avrundning, efterfrågemått (endast registrerade) | säkerhetsmarginal |
| Kalender och flexibilitet | tidigare/senare dagar, veckodagar, starttider, tidigaste starttid, senaste sluttid, första/sista datum, spärrade perioder, ställtid, flyttbara typer | tentamensperioder, kursordning |
| Krockar | kurskod och explicita konfliktgrupper | individuella studentkrockar |
| Lokaler | urval, max salar per tenta, delning över salar, delning över byggnader | kapacitetsöverstyrning, egna lokaler, samlokaliseringsregler, tillgänglighetsläge |
| Digitalt | policy för salar med delvis digitalstöd, policy för okänd digital status | verifierad kompatibilitetsmatris, framtida digital andel |
| Bemanning | trappa, förberedelse och avslutning (anonym samtidig pool) | arbetspass, rast, arbetstid, vila, resa, minsta betalda pass |
| Kostnad | årskostnad per plats, årskostnad per pool, rörlig kostnad per vaktsalstillfälle | **externhyra per salstillfälle** (ingen datakälla för externa lokaler), annualisering, undvikbara kostnader |
| Mål och solver | tidsgräns, frö, antal trådar, reproducerbar parallell sökning | viktning av mål (motorn är lexikografisk) |
| Särskilt stöd | – | regler för särskilt pedagogiskt stöd |
| Examinationsvillkor | faktisk skrivtid per behov | experimentell maximal skrivtid |

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
