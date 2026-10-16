# Tentaoptimering – proof of concept

## Syfte

PoC:n ska uppskatta den långsiktiga **årliga besparingspotentialen** i Uppsala universitets tentamensverksamhet genom samordnad planering av **tentamenstillfällen, lokaler och tentamensvakter**.

Målet är den lägsta **totala årskostnaden** för en fullt genomförbar verksamhet. Samtliga tentamina och tentander inom den uttryckligen valda omfattningen ska få plats. Användaren väljer själv planeringsperiodens start- och slutdatum inom den tid som finns representerad i dataunderlaget, även kortare än en termin. Datum, tentamensperioder och pass är justerbara verksamhetsparametrar. Kostnader som ska tolkas som årsvärden kräver en särskild och tydligt angiven beräkningsgrund.

## Dokumentation

Utgå från [dokumentationsingången](docs/README.md). Där finns läsordning,
styrande dokument, tekniska referenser, verksamhetsunderlag och avskild
historik. [Krav och aktuell status](docs/KRAV_OCH_STATUS.md) är den enda
aktuella kravuppfyllnadsmatrisen; äldre planer och granskningsrapporter får inte
användas som nulägesbeskrivning.

## Valbar period och granskning i gränssnittet

PoC:n ska visa tillgängliga dataperioder och låta användaren välja start- och slutdatum. Nästa dataleverans avses omfatta **1 januari–30 september** inklusive uppgifter om **verklig beläggning**; årtal, fältdefinitioner och täckning fastställs vid import, och denna leverans är ännu inte inläst. Källdata ska gå att utforska separat från optimeringen: användaren ska kunna se hur en viss lokal nyttjas under en vald period och hur en identifierad bokad tentamen är schemalagd (datum, tid, salplacering/ar). Historisk bokning, beläggningsobservation och simulerat schema ska inte förväxlas.

Målbilden är en framtida export som universitetets bokningssystem kan importera. Systemanpassad export ligger **utanför PoC** tills ett importkontrakt finns; en enkel maskinläsbar resultatfil kan prövas utan att påstå kompatibilitet med bokningssystemet. Se [kravspecifikationen](docs/KONCEPTUELL_KRAVSPECIFIKATION.md) och [kravstatusen](docs/KRAV_OCH_STATUS.md).

## Källfiler

Originalfilerna ligger i `C:\lokalt\tentalokaler\underlag` och ska hanteras skrivskyddat. Filnamn och ark finns i `config/source_files.toml`. Excellfiler och normaliserade datadumpar ska inte läggas i Git.

## Körning

Installera paketet i redigerbart läge så att körningar och tester använder `src` (inte en gammal kopia i `site-packages`): `.\.venv\Scripts\python.exe -m pip install -e .`. Därefter, med den lokala virtuella miljön:

```powershell
.\.venv\Scripts\python.exe -m tentaoptimering.cli prepare
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`prepare` återskapar normaliserade underlag och rapporter, inklusive den aktivitetsspecifika `demand_scope.csv`; dess konfiguration (efterfrågemått och explorativa PoC-antaganden om lokalbestånd) finns i `config/data_preparation.toml`. `status` och `resources` läser senast genererade beredskapsstatus och resurser, `joint-parameters` listar den gemensamma parameterkatalogen. CLI:t skriver JSON som standard.

Den gemensamma CP-SAT-kärnan kan köras reproducerbart på ett namngivet verkligt delurval. Den optimerar kalenderpass, faktiska salar och regelberäknad bemanningskostnad i samma modell:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
.\.venv\Scripts\python.exe -m tentaoptimering.cli optimize-joint --config config\scenarios\joint_real_subset.toml
```

Körningen sparar versionsmärkt modellindata, resultat, manifest och rapport under `runs/` (som inte versionshanteras) och kör eftervalideringen direkt efter lösningen. Se [gemensam optimeringsdesign](docs/GEMENSAM_OPTIMERINGSDESIGN.md), [optimeringsstrategi](docs/OPTIMERINGSSTRATEGI.md) och [kravstatus](docs/KRAV_OCH_STATUS.md) för gällande kontrakt, mätningar och begränsningar.

Den fristående eftervalideringen läser en sparad körnings egna modellindata och placeringsresultat och kan köras utan att optimeringen körs igen. Den redovisar regelvis `pass`, `fail`, `not_evaluated` eller `not_applicable` och skiljer teknisk placeringsfullständighet från verksamhetsmässig verifiering; avsaknad av data eller modellstöd blir aldrig ett godkänt krav. Se [oberoende eftervalidering](docs/OBEROENDE_EFTERVALIDERING.md).

```powershell
.\.venv\Scripts\python.exe -m tentaoptimering.cli validate-joint-run --run-id <körnings-id>
```

Standardstrategin är `solver.strategy = "decomposed"`. En aggregerad relaxation väljer datum, lokalportfölj och bemanningspool och ger en bevisad undre kostnadsgräns. Därefter kontrolleras varje dag exakt med samma hårda villkor. Den monolitiska modellen kan väljas med `"monolithic"`. Se [optimeringsstrategin](docs/OPTIMERINGSSTRATEGI.md) för analys och mätningar.

### Varmstart och parallella dagkontroller

När parametrar ändras startar `optimize-joint` som standard från den senaste användbara körningen av samma problem (`--warm-start auto`). Körningen väljs bland sparade körningsmappar under `runs/` och pekas ut med sitt körnings-id:

```powershell
.\.venv\Scripts\python.exe -m tentaoptimering.cli optimize-joint --config config\scenarios\joint_real_subset.toml --warm-start auto
.\.venv\Scripts\python.exe -m tentaoptimering.cli optimize-joint --config <scenario> --warm-start 20261012T101500Z-joint_real_subset
.\.venv\Scripts\python.exe -m tentaoptimering.cli optimize-joint --config <scenario> --warm-start none
```

Den tidigare körningen måste ha oförändrade filer enligt sitt manifest och godkännas av den oberoende eftervalideringen vid själva körningen; ett sparat godkännande räknas aldrig. Lösaren kontrollerar därefter placeringen dag för dag mot den nya instansens regler. Den blir en första övre gräns bara om varje dag klarar kontrollen. I annat fall används de tidigare passen som ledtråd och vanlig optimering körs. Beslutet och skälen sparas i `joint_warm_start.json` i den nya körningen och redovisas i rapporten.

`--threads`, `--memory-mb` och `--sequential-day-checks` styr den gemensamma trådbudgeten och minnesgränsen för de parallella dagkontrollerna. Ctrl+C stoppar lösaren och sparar den bästa verifierade lösningen hittills. Se [optimeringsstrategin](docs/OPTIMERINGSSTRATEGI.md), avsnitt 9.

## Förklarad besparing mellan valfria alternativ

Kostnader, avtal och externhyror ligger i ett **resurspaket** (`config/resource_data/`, schema `resource-data-v1`) där varje uppgift märks som observerad, modellberäknad, simulerad eller antagen. Den medföljande filen är **simulerad** och ersätts av verkliga uppgifter med en ny fil, utan kodändring. Personalkostnaden är **betald personaltid** (förberedelse, tentamen, avslut, kortaste betalda pass och restid) och fasta bokningar utanför de valda tentorna spärrar salar. Under **Jämför** väljer du själv två alternativ (A, B eller en sparad C-körning) och ser totalskillnaden uppdelad i hyrda lokaler, externa bokningar och personal, ner till namngivna lokaler, ändrade bokningar och betalda timmar. Skillnaden är modellberäknad; verifierad realiserbar besparing kräver observerade avtalsuppgifter. Se [kostnadsmodellen](docs/KOSTNADSMODELL.md) och [A, B och C](docs/ABC_SCENARIOMODELL.md).

## Lokalt gränssnitt

PoC:n har ett lokalt React- och FastAPI-gränssnitt för gemensamma körningar: scenarier, parametrar, körning, jämförelse och eftervalidering. Se [lokalt gränssnitt](docs/LOKALT_GRANSSNITT.md) för utveckling, Windows-paketering och offlineverifiering.

## Aktuell implementation

Projektet innehåller ett reproducerbart inläsnings- och analyslager, ett kanoniskt scope-/efterfrågelager och en första gemensam CP-SAT-kärna med full efterfrågetäckning, faktiska salar och bemanningsrelaterad kostnad. Den avgränsade verkliga körningen är ett modellbevis och inte ett operativt schema eller en beräkning av realiserbar besparing. Den äldre kapacitets- och termmotorn är borttagen (finns i Git-historiken före den här grenen); den gemensamma motorn är den enda optimeringsvägen.

Population och täckning ska alltid läsas ur det frusna underlaget för den
aktuella körningen. Resultat för en beräkningsbar delpopulation får inte
beskrivas som täckning av hela verksamheten innan samtliga aktiviteter fått ett
verksamhetsbeslut.

## Datakvalitet

Bokningsrader, unika tentamensbehov och Ladokaktiviteter representerar olika informationsnivåer. `ANTAL_TOT` är inte verifierad faktisk närvaro och internhyra är inte automatiskt en realiserbar besparing. Saknade uppgifter hanteras som kvalificerade, dokumenterade och ersättbara antaganden.

Se [filöversikten](docs/FILOVERSIKT.md) för ansvar per versionshanterad fil och filstorlekspolicyn.
