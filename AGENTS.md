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

## Verifiering

Använd Python 3.11 eller senare och kör före leverans:

```powershell
python -m tentaoptimering.cli
python -m unittest discover -s tests -v
```

Kontrollera att källdata förblir oförändrade och att genererade radantal stämmer mot baslinjen.
