# Tentaoptimering – PoC

> **Aktuellt uppdrag (2026-10-08):** Detta README dokumenterar den första databaslinjen, inte hela PoC:ns aktuella målbild. Läs **[AGENTS.md](AGENTS.md)** först och därefter **[konceptuell kravspecifikation](docs/KONCEPTUELL_KRAVSPECIFIKATION.md)**, **[gap-analys](docs/GAP_ANALYS_MOT_KRAVSPECIFIKATION.md)** och **[aktuellt Codex-uppdrag](docs/KODGRANSKNING_OCH_CODEX_UPPDRAG_2026-10-08.md)**. Äldre begränsningar i denna fil avser första checkpointen och ersätter inte de aktuella kraven. Codex ska i detta steg endast granska den lokala implementationen, inte skriva ny kod. **Noll oplacerade tentander och terminsövergripande gemensam kostnadsoptimering** är grundläggande krav.


Detta repo innehåller den första, avgränsade leveransen för en PoC om tentamenslokaler. Målet är att skapa en verifierbar databaslinje inför senare optimering. Ingen solver och inga förutbestämda scenariointervall ingår ännu.

## Första leveransen

- projektstruktur och reproducerbar körning
- läsning av de tre källfilerna utan att ändra dem
- datavalidering med konkreta kvalitetsfynd
- normaliserade CSV-tabeller för placeringar, Ladok-aktiviteter och lokal-/kostnadsrader
- maskinläsbart parameterregister utan låsta värden
- genererad baslinjerapport
- struktur för kostnadsmodellen
- lista över blockerande datagap

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

Körningen skapar:

```text
data/processed/bookings.csv
data/processed/ladok_activities.csv
data/processed/lease_rows.csv
reports/baseline.md
reports/data_quality.json
```

De normaliserade tabellerna ignoreras av Git eftersom de kan återskapas från originaldata. Rapporterna versionshanteras som en granskningsbar baslinje.

## Avgränsning

Baslinjen beskriver källdata och risker. Den antar inte att en bokningsrad är en unik tentamen, att `ANTAL_TOT` är faktisk närvaro eller att preliminär internhyra är en realiserbar besparing. Dessa frågor måste lösas innan en optimerare får tolka resultaten i kronor.
