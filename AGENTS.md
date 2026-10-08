# Arbetsinstruktioner för Codex

## Omfattning

Detta repo är en PoC för analys och senare optimering av tentamenslokaler.

## Källdata

- Originaldata finns i `C:\lokalt\tentalokaler\underlag` och är alltid read-only.
- Lägg aldrig Excel-, CSV- eller databasexporter från källmappen i Git.
- Normaliserade tabeller under `data/processed` är reproducerbara och ska inte versionshanteras.

## Modellregler

- Skilj beställning/tentamenstillfälle, fysisk salplacering och särskilt stöd.
- Anta inte att Ladoks `ANTAL_TOT` är faktisk närvaro utan verifierad definition.
- Anta inte att preliminär internhyra är en realiserbar besparing.
- Hårdkoda inte verksamhetsparametrar eller scenariointervall. Värden ska komma från det maskinläsbara parameterregistret eller en uttrycklig beställning.
- Bygg ingen solver förrän datamodell, parameterregister och kostnadskoppling har godkänts eller användaren uttryckligen beställer nästa steg.

## Kodfilers storlek och filöversikt

- Håll Python-kodfiler omkring 500 rader eller kortare. Dela efter ansvar, inte bara efter antal rader.
- Vid 800 rader är det en stark varning: planera uppdelning innan filen växer vidare.
- Vid 1 000 rader är filen för stor och måste delas upp innan leverans. `tools/check_code_file_lengths.py` kontrollerar detta och stoppar med felkod.
- Håll `docs/FILOVERSIKT.md` uppdaterad när en versionshanterad fil läggs till, tas bort eller får ett väsentligt ändrat ansvar.

## Verifiering

Använd Python 3.11 eller senare och kör före leverans:

```powershell
python -m tentaoptimering.cli
python tools/check_code_file_lengths.py
python -m unittest discover -s tests -v
```

Kontrollera att källdata förblir oförändrade och att genererade radantal stämmer mot baslinjen.
