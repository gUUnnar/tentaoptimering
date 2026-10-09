# Tentaoptimering – proof of concept

## Syfte

PoC:n ska uppskatta den långsiktiga **årliga besparingspotentialen** i Uppsala universitets tentamensverksamhet genom samordnad planering av **tentamenstillfällen, lokaler och tentamensvakter**.

Målet är den lägsta **totala årskostnaden** för en fullt genomförbar verksamhet. Samtliga tentamina och tentander inom den uttryckligen valda omfattningen ska få plats. Planeringsenheten är minst en termin; datum, tentamensperioder och pass är justerbara verksamhetsparametrar.

## Dokumentation

- [Kravspecifikation](docs/KONCEPTUELL_KRAVSPECIFIKATION.md) – verksamhetskrav, kostnadsmodell, scenarioparametrar och förväntade resultat.
- [AGENTS.md](AGENTS.md) – arbetsinstruktioner för Codex och aktuellt utvecklingssteg.
- [Kodgranskning och arbetsuppdrag](docs/KODGRANSKNING_OCH_CODEX_UPPDRAG_2026-10-08.md) – ursprunglig kodinventering och nästa leverans.
- [Gemensam optimeringsdesign](docs/GEMENSAM_OPTIMERINGSDESIGN.md) – kanoniskt tentamensbehov, salstillfällen, bemanning och årskostnad.
- [Datamodell](docs/DATAMODELL.md), [kostnadsmodell](docs/KOSTNADSMODELL.md) och [datagap](docs/BLOCKERANDE_DATAGAP.md) – tekniska underlag som stäms av mot kravspecifikationen.

## Källfiler

Originalfilerna ligger i `C:\lokalt\tentalokaler\underlag` och ska hanteras skrivskyddat. Filnamn och ark finns i `config/source_files.toml`. Excellfiler och normaliserade datadumpar ska inte läggas i Git.

## Körning

Med den lokala virtuella miljön:

```powershell
.\.venv\Scripts\python.exe -m tentaoptimering.cli prepare
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`prepare` återskapar normaliserade underlag och rapporter, inklusive den aktivitetsspecifika `demand_scope.csv`. `status` läser senast genererade beredskapsstatus. CLI:t skriver JSON som standard.

Den första integrerade terminskörningen använder en separat, versionshanterad scenariofil. Den placerar enbart de preliminärt inkluderade behoven och redovisar därför både täckning av modellens behov och täckning av hela källpopulationen:

```powershell
.\.venv\Scripts\python.exe -m tentaoptimering.cli optimize-term --config config\scenarios\integrated_term_exploratory.toml
```

Körningen sparar spårbarhets- och resultatfiler under `runs/`, som inte versionshanteras. Den är explorativ: rumstillgänglighet, digital kompatibilitet, kostnader och bemanningsregler är uttryckliga, ersättbara scenarioantaganden. Den skapar anonymiserade vaktuppgifter och kontrollerar arbetspass, raster, vila och byggnadsbyten. Resultatet är inte ett operativt schema och den konstruktiva heltermsmetoden redovisar inget optimalitetsgap.

Eftervalideringen läser en sparad körnings egna modellindata, scenario och placeringsrader, och kan köras utan att placeringsmetoden körs igen:

```powershell
.\.venv\Scripts\python.exe -m tentaoptimering.cli validate-term-run --run-id <körnings-id>
```

Den skriver `validation.json` och `validation.md` i körningsmappen. Full teknisk placering innebär inte verksamhetsmässig genomförbarhet: regler som bara täcks av antaganden eller saknar data/modellstöd redovisas separat och ger status `not_verified`. Resultatets kostnadsjämförelse visar endast separata, ej jämförbara kostnadsprofiler och redovisar aldrig en differens eller verifierad besparing utan avtalskopplingar.

Den nya gemensamma CP-SAT-kärnan kan köras reproducerbart på ett namngivet verkligt delurval. Den optimerar kalenderpass, faktiska salar och regelberäknad bemanningskostnad i samma modell:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
.\.venv\Scripts\python.exe -m tentaoptimering.cli optimize-joint --config config\scenarios\joint_real_subset.toml
```

Körningen sparar versionsmärkt modellindata, resultat, manifest och rapport under `runs/`. Se [första gemensamma CP-SAT-leveransen](docs/GEMENSAM_CP_SAT_FORSTA_LEVERANS.md) för statussemantik, handräknade facit, uppmätt verklig körning och kända begränsningar.

## Lokalt gränssnitt

PoC:n har ett lokalt React- och FastAPI-gränssnitt för scenarier, parametrar, terminskörningar och eftervalidering. Se [lokalt gränssnitt](docs/LOKALT_GRANSSNITT.md) för utveckling, Windows-paketering och offlineverifiering.

## Aktuell implementation

Projektet innehåller ett reproducerbart inläsnings- och analyslager, ett kanoniskt scope-/efterfrågelager och en första gemensam CP-SAT-kärna med full efterfrågetäckning, faktiska salar och bemanningsrelaterad kostnad. Den avgränsade verkliga körningen är ett modellbevis och inte ett operativt schema eller en beräkning av realiserbar besparing. Den äldre kapacitetsoptimeraren finns tillfälligt kvar för den befintliga applikationsvägen tills dess funktioner har ersatts.

Den aktuella scope-rapporten redovisar 1 259 tekniskt inkluderade aktiviteter och 266 oavgjorda. Resultat för den omfattningen får inte beskrivas som täckning av hela verksamheten förrän samtliga aktiviteter fått ett verksamhetsbeslut.

## Datakvalitet

Bokningsrader, unika tentamensbehov och Ladokaktiviteter representerar olika informationsnivåer. `ANTAL_TOT` är inte verifierad faktisk närvaro och internhyra är inte automatiskt en realiserbar besparing. Saknade uppgifter hanteras som kvalificerade, dokumenterade och ersättbara antaganden.

Se [filöversikten](docs/FILOVERSIKT.md) för ansvar per versionshanterad fil och filstorlekspolicyn.
