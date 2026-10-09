# Parameterkatalog v2

**Status:** Implementerad kontraktskälla för den nya gemensamma optimeringsmotorn.
**Maskinläsbar källa:** `config/joint_parameter_catalog.toml` (`catalog_version = "2.0.0"`).

Det tidigare S0-beslutet att dölja parametrar utan motorstöd är upphävt. Alla definierade verksamhetsparametrar finns i samma katalog för framtida GUI, lagring, validering och motoranslutning. Varje post har ett av två tydliga stödtillstånd:

- `implemented`: värdet läses av angiven adapter- eller solverfunktion och har ett automatiserat effektfall.
- `contract_only`: värdet kan visas, redigeras, frysas och sparas, men påverkar ännu inte beräkningen. En körning listar alltid dessa parametrar som begränsningar; de får aldrig tolkas som kontrollerade krav.

Varje definition innehåller id, verksamhetsgrupp, etikett, typ, enhet, standardvärde, standardgrund, hjälptext, motorstöd och – när stöd finns – `honored_by`. Körningskontraktet fryser dessutom värde, grund, motivering och motorstöd för varje parameter.

## Omfattning

| Område | Parametrar med stöd i första kärnan | Definierade men ännu utan motorstöd |
|---|---|---|
| Efterfrågan | variation, avrundning | – |
| Kalender och flexibilitet | tidigare/senare dagar, veckodagar, starttider, ställtid, flyttbara typer | spärrade perioder, tentamensperioder, kursordning |
| Krockar | kurskod och explicita konfliktgrupper i indatakontraktet | individuella studentkrockar |
| Lokaler | urval, max salar per tenta, delning över byggnader | kapacitetsöverstyrning, egna lokaler |
| Digitalt | krav per tentamen och kompatibilitet per sal i indatakontraktet | framtida digital andel |
| Bemanning | trappa, förberedelse och avslutning som samtidig anonym pool | individuella pass, rast, arbetstid, vila, resa och minsta betalda pass |
| Kostnad | fast årskostnad per sal, extern kostnad per salstillfälle, årlig poolkostnad, rörlig kostnad per vaktsalstillfälle | annualiseringsfaktor |
| Solver | tidsgräns och slumpfrö | – |
| Examinationsvillkor | faktisk skrivtid per behov | experimentell maximal skrivtid |

## Grund och motivering

Tillåtna grunder är `verified`, `source_data`, `assumption` och `experiment`. Ett ändrat verifierat eller källhämtat värde fryses som `experiment`; ett justerat antagande förblir ett motiverat `assumption`. Att ett värde har grunden `verified` betyder inte att en resultatregel automatiskt är godkänd; regelstatus måste härledas av eftervalidering från databevis och faktiskt resultat.

Kostnadsstandarderna är noll för att undvika ett dolt ekonomiskt påstående. Den reproducerbara verkliga delmängdskörningen anger uttryckliga proxyer och motiveringar i `config/scenarios/joint_real_subset.toml`. De är modellantaganden, inte faktisk kostnad eller verifierad besparing.

## Effektfall

`tests/test_parameter_catalog.py` kontrollerar att både stödda och ostödda parametrar exponeras och fryses med rätt stödstatus. `tests/test_joint_optimizer.py` visar bland annat att:

- efterfrågan inte kan lämnas delvis oplacerad;
- delgrupper räknas en gång även när en delgrupp har flera källaktiviteter;
- lokal- och bemanningskostnad kan ge ett annat optimum än billigaste lokalbeståndet ensamt;
- ekonomiskt likvärdiga lösningar väljer ursprungligt pass;
- digital kompatibilitet, kurskrock, salkapacitet och ställtid är hårda villkor.
