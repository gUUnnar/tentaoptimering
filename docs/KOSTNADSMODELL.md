# Struktur för kostnadsmodellen

Kostnadsmodellen ska hålla isär tre resultat:

1. minskat resursbehov, exempelvis färre samtidiga salar eller färre externa bokningar
2. ändrad intern kostnadsfördelning
3. potentiellt realiserbar besparing för universitetet

En kostnadskomponent behöver minst stabilt sal-ID, avtalsobjekt, kostnadstyp, belopp, om kostnaden är undvikbar, uppsägningstid, tidigaste realiseringsdatum och eventuella engångskostnader.

`src/tentaoptimering/cost_model.py` innehåller dataklasserna för detta. Funktionen `uncalculated_savings()` returnerar uttryckligen ett blockerat resultat tills de verifierade kopplingarna finns. Preliminär internhyra summeras endast som källprofil och behandlas inte som besparing.

Terminskörningen redovisar därför med `cost_comparison.py` två helt åtskilda kostnadsprofiler: källans preliminära internhyra och scenariots antagandekostnad. Ingen differens beräknas eller publiceras. Teoretisk årlig potential och verifierad realiserbar besparing är `null` tills sal–avtal, undvikbarhet, uppsägningstid och engångskostnad kan beläggas.
