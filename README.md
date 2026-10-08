# Tentaoptimering – proof of concept

## Syfte
PoC:n ska uppskatta den långsiktiga **årliga besparingspotentialen** i Uppsala universitets tentamensverksamhet genom samordnad planering av **tentamenstillfällen, lokaler och tentamensvakter**.

Målet är den lägsta **totala årskostnaden** för en fullt genomförbar verksamhet. Samtliga tentamina och tentander inom den angivna omfattningen ska få plats. Planeringsenheten är minst en termin. Tillåtna datum, tentamensperioder och pass är justerbara verksamhetsparametrar.

## Dokumentation
- [Kravspecifikation](docs/KONCEPTUELL_KRAVSPECIFIKATION.md) – verksamhetskrav, kostnadsmodell, scenarioparametrar och förväntade resultat.
- [AGENTS.md](AGENTS.md) – arbetsinstruktioner för Codex och aktuellt utvecklingssteg.
- [Kodgranskning och arbetsuppdrag](docs/KODGRANSKNING_OCH_CODEX_UPPDRAG_2026-10-08.md) – kodinventering och leverans för nästa steg.
- [Datamodell](docs/DATAMODELL.md), [kostnadsmodell](docs/KOSTNADSMODELL.md) och [datagap](docs/BLOCKERANDE_DATAGAP.md) – tekniska underlag som ska stämmas av mot kravspecifikationen.

## Källfiler
Originalfilerna ligger i `C:\lokalt\tentalokaler\underlag` och ska hanteras skrivskyddat. Filnamn och ark finns i `config/source_files.toml`. Excellfiler och normaliserade datadumpar ska inte läggas i Git.

## Körning av datainläsning på GitHub-main
```powershell
python -m pip install -e .
python -m tentaoptimering.cli
python -m unittest discover -s tests -v
```

Kommandona i GitHub-main avser datainläsning, normalisering och kvalitetsrapporter. För den lokala arbetskatalogen `C:\lokalt\tentalokaler\PoC` ska faktisk kodversion, kommandon och eventuella lokala ändringar inventeras innan ytterligare utveckling.

## Datakvalitet
Bokningsrader, unika tentamensbehov och Ladokaktiviteter representerar olika informationsnivåer. Ladokfältet `ANTAL_TOT` är inte verifierad faktisk närvaro. Internhyra ger inte automatiskt en realiserbar besparing. Saknade uppgifter hanteras med kvalificerade, dokumenterade och utbytbara antaganden så att PoC:n är körbar innan kompletterande material levereras.
