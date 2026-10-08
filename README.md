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

## Aktuell implementation

Projektet innehåller ett reproducerbart inläsnings- och analyslager, ett kanoniskt scope-/efterfrågelager och ett syntetiskt integrerat CP-SAT-bevisfall. Den äldre kapacitetsoptimeraren är explorativ och är inte ett kalenderverifierat schema eller en beräkning av realiserbar besparing.

Den aktuella scope-rapporten redovisar 1 258 tekniskt inkluderade aktiviteter och 267 oavgjorda. Resultat för den omfattningen får inte beskrivas som täckning av hela verksamheten förrän samtliga aktiviteter fått ett verksamhetsbeslut.

## Datakvalitet

Bokningsrader, unika tentamensbehov och Ladokaktiviteter representerar olika informationsnivåer. `ANTAL_TOT` är inte verifierad faktisk närvaro och internhyra är inte automatiskt en realiserbar besparing. Saknade uppgifter hanteras som kvalificerade, dokumenterade och ersättbara antaganden.

Se [filöversikten](docs/FILOVERSIKT.md) för ansvar per versionshanterad fil och filstorlekspolicyn.
