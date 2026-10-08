# Tentaoptimering – PoC

Detta repo innehåller en körbar, lokal PoC för analys och kapacitetsoptimering av tentamenslokaler. OR-Tools CP-SAT placerar provisorisk Ladokefterfrågan i scenariorum under en komplett, explicit körningskonfiguration. Resultaten är experimentella och utgör inte ett kalenderverifierat tentamensschema eller en beräkning av realiserbar besparing.

Se [filöversikten](docs/FILOVERSIKT.md) för ansvar per versionshanterad fil och för reglerna om kodfilers storlek.

## Funktioner

- projektstruktur och reproducerbar körning
- läsning av de tre källfilerna utan att ändra dem
- datavalidering med konkreta kvalitetsfynd
- normaliserade CSV-tabeller för placeringar, Ladok-aktiviteter och lokal-/kostnadsrader
- maskinläsbart parameterregister utan låsta värden
- genererad baslinjerapport
- struktur för kostnadsmodellen
- lista över blockerande datagap
- konfigurerbar kapacitetsoptimering med samlokalisering, uppdelning och tidsförskjutning
- oberoende eftervalidering av kapacitet, tid, geografi och fullständig efterfrågetäckning
- sparade körningar med unika ID:n, manifest, placeringar, oplacerad efterfrågan och rapport
- maskinläsbar jämförelse mellan scenarier

## Källdata

Originaldata ska ligga utanför repot och behandlas som skrivskyddad:

```text
C:\lokalt\tentalokaler\underlag\
```

Standardkörningen använder `..\underlag`. En annan sökväg kan anges med `--source-dir` eller miljövariabeln `TENTA_SOURCE_DIR`.

## Körning

Med Python 3.11 eller senare:

```powershell
python -m pip install -e .
python -m tentaoptimering.cli
python -m unittest discover -s tests -v
```

CLI:t använder JSON som standard för ChatGPT Work och andra lokala verktyg:

```powershell
# Bygg om alla underlag och returnera strukturerat resultat
python -m tentaoptimering.cli prepare

# Läs senaste beredskapsstatus utan att köra om pipelinen
python -m tentaoptimering.cli status

# Visa resurser eller parameterdefinitioner
python -m tentaoptimering.cli resources
python -m tentaoptimering.cli parameters

# Validera och kör referensscenariot
python -m tentaoptimering.cli validate-config --config config\scenarios\reference.toml
python -m tentaoptimering.cli optimize --config config\scenarios\reference.toml

# Hämta en sparad körning
python -m tentaoptimering.cli result --run-id <run-id>

# Jämför två eller flera körningar
python -m tentaoptimering.cli compare --run-ids <run-id-1> <run-id-2>

# Människoläsbar, kort utdata vid manuell körning
python -m tentaoptimering.cli prepare --format text
```

Alla kommandon använder JSON som standard och har ett stabilt `schema_version`. Lyckade kommandon returnerar `status: "ok"`. Förväntade indata-, konfigurations- eller resultatfel ger exitkod 2 och ett JSON-objekt med `status: "error"`. Oväntade fel ger exitkod 1.

Körningen skapar:

```text
data/processed/bookings.csv
data/processed/ladok_activities.csv
data/processed/lease_rows.csv
data/processed/candidate_linkage.csv
data/processed/exam_events.csv
data/processed/activity_booking_candidates.csv
data/processed/room_inventory.csv
data/processed/optimization_rooms.csv
data/processed/optimization_demands.csv
data/processed/optimization_placements.csv
data/processed/demand_scope.csv
reports/baseline.md
reports/data_quality.json
reports/candidate_linkage.md
reports/candidate_linkage.json
reports/optimization_readiness.md
reports/optimization_readiness.json
reports/demand_scope.md
reports/demand_scope.json
reports/run_manifest.json
runs/<run-id>/scenario.toml
runs/<run-id>/input_manifest.json
runs/<run-id>/result.json
runs/<run-id>/assignments.csv
runs/<run-id>/unplaced.csv
runs/<run-id>/report.md
```

De normaliserade tabellerna och körningskatalogerna ignoreras av Git eftersom de kan återskapas från originaldata och versionshanterade scenarier. Rapporterna under `reports` versionshanteras som en granskningsbar baslinje.

## Avgränsning

Baslinjen beskriver källdata och risker. Den antar inte att en bokningsrad är en unik tentamen, att `ANTAL_TOT` är faktisk närvaro eller att preliminär internhyra är en realiserbar besparing. Dessa frågor måste lösas innan en optimerare får tolka resultaten i kronor.

`candidate_linkage.csv` är en granskningsbar kandidatdiagnostik mellan bokningar och Ladok, baserad på kurskod, datum och starttid. Den skapar inte en verifierad sammanslagning och använder inte deltagarantal i analysen.

`optimization_demands.csv` använder det konfigurerade provisoriska Ladokmåttet från parameterregistret, men innehåller bara entydiga tekniska kandidater. `optimization_rooms.csv` innehåller de rumsspecifika publicerade kapaciteter som uttryckligen får användas för explorativ PoC. Läs [optimeringsunderlaget](docs/OPTIMERINGSUNDERLAG.md): kapacitetsanalys får genomföras, men historisk giltighet och salarnas kalendertillgänglighet är inte verifierade.

Referensscenariot behåller historiska datum och tider. Det alternativa scenariot tillåter ±60 minuters startförskjutning och är uttryckligen ett tekniskt experiment, inte en beslutad verksamhetsregel. Samlokalisering och uppdelning är aktiverade eftersom båda förekommer i historiska placeringar; särskilt stöd och digital kompatibilitet redovisas som ännu ej modellerade osäkerheter. Se [optimeringsmotorn](docs/OPTIMERINGSMOTOR.md) för modell, mål, CLI-kontrakt och resultattolkning.
