# Optimeringsmotor och körningskontrakt

PoC:n använder OR-Tools CP-SAT. Beräkningsmotorn, CLI:t, körningslagringen och den oberoende resultatvalideringen ligger i separata moduler.

## Modell

Varje körbar Ladokaktivitet blir exakt en efterfrågepost. Den kan placeras på ett tillåtet datum och en tillåten starttid eller markeras som oplacerad. Deltagarna fördelas på ett eller flera rum enligt scenariots delningsregel.

För varje överlappande tidssegment och rum gäller:

- summerade tilldelade deltagare får inte överstiga rumskapaciteten;
- flera tentamina får bara dela rum när `allow_co_location` är sant;
- en tentamen får bara använda flera rum när `allow_split` är sant;
- antalet rum per tentamen begränsas av `max_rooms_per_exam`;
- historisk stad respekteras när `enforce_historical_city` är sant.

Efterfrågan räknas en gång per `demand_id`. Historiska placeringsrader används endast för spårbarhet och omplaceringsmått.

När ingen datumförflyttning tillåts löses datumen som oberoende delproblem. Det ändrar inte kapacitets- eller tidsvillkoren mellan tentamina eftersom olika datum inte överlappar. Resultatet märks ändå `feasible`, inte globalt `optimal`, eftersom målet för unika rum kopplar samman dagarna.

Scenarier med starttidsflexibilitet använder två faser inom den angivna totala tidsbudgeten. En fas löser originaltiderna och en fas söker bland de flexibla tiderna. Den bättre giltiga lösningen behålls per datum, så extra flexibilitet kan inte ge ett sämre rapporterat resultat enbart på grund av söktiden.

## Mål och absoluta villkor

Kapacitet, tidsfönster, geografi, samlokalisering och delningsgräns är absoluta villkor. Följande mjuka mål viktas explicit i varje scenario:

- oplacerade deltagare;
- oplacerade tentamina;
- antal använda rum;
- öppna salminuter;
- outnyttjade platsminuter;
- tidsflyttade tentamina;
- nya rumstilldelningar jämfört med historiska placeringar.

Vikterna är en del av körningskonfigurationen och sparas tillsammans med resultatet. Inga intervall eller vikter hämtas implicit från koden.

## Scenarier

`config/scenarios/reference.toml` behåller historiska datum och starttider. Salbyte, samlokalisering och uppdelning tillåts som synliga PoC-antaganden.

`config/scenarios/flexible_start_60m.toml` behåller datum men tillåter startförskjutning med högst 60 minuter i steg om 60 minuter. Värdet är ett tekniskt jämförelsescenario, inte en beslutad verksamhetsregel.

Båda scenarierna:

- använder Ladoks `registered_count` utan säkerhetsmarginal;
- begränsar Uppsalaefterfrågan till Uppsalarum;
- antar att scenariorummen är tillgängliga utan kalendergaranti;
- modellerar ännu inte särskilt stöd eller tentamensformat som kompatibilitetsvillkor;
- tillåter oplacerad efterfrågan och redovisar den öppet.

## Solverstatus och fullständig placering

`optimal` betyder att CP-SAT bevisat optimalitet för det lösta problemet. `feasible` betyder att en giltig lösning hittats utan globalt optimalitetsbevis. `infeasible`, `model_invalid` och `unknown` redovisas utan att regler ändras automatiskt.

Vid fasta tider görs dessutom ett analytiskt kapacitetstest. Om samtidiga deltagare överstiger den sammanlagda kompatibla rumskapaciteten är fullständig placering bevisat omöjlig oberoende av solversökningen. För flexibla tider redovisas `not_determined` om körningen lämnar efterfrågan oplacerad utan ett sådant bevis.

## Oberoende validering

Innan en körning sparas valideras resultatet på nytt utanför CP-SAT-modellen. Valideringen kontrollerar:

- att varje körbar efterfrågepost är antingen placerad eller oplacerad;
- deltagarsumman per placerad tentamen;
- tillåtna rum, datum, tider och veckodagar;
- kapacitet i varje rum och minut;
- samlokalisering, delningsgräns och historisk stad.

En valideringsavvikelse stoppar körningen och ger ett strukturerat fel.

## CLI för ChatGPT Work

CLI:t skriver JSON som standard:

```powershell
python -m tentaoptimering.cli resources
python -m tentaoptimering.cli parameters
python -m tentaoptimering.cli validate-config --config config\scenarios\reference.toml
python -m tentaoptimering.cli optimize --config config\scenarios\reference.toml
python -m tentaoptimering.cli result --run-id <run-id>
python -m tentaoptimering.cli compare --run-ids <referens-id> <alternativ-id>
```

Varje körningskatalog innehåller scenariokopian, indatamanifestet, `result.json`, placeringsrader, oplacerade poster och en läsbar rapport. `result.json` innehåller solverversion, status, körtid, målfunktion, bästa gräns när sådan finns, optimalitetslucka, valideringsresultat, kapacitetsmått och osäkerheter.

## Tolkning

Resultaten beskriver teoretiskt kapacitetsbehov och optimerat lokalutnyttjande under valda antaganden. De visar inte verifierad kalendertillgänglighet, potentiellt avvecklingsbara avtalsobjekt eller realiserbar ekonomisk besparing.

