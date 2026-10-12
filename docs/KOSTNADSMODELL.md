# Struktur för kostnadsmodellen

Kostnadsmodellen ska hålla isär tre resultat:

1. minskat resursbehov, exempelvis färre samtidiga salar eller färre externa bokningar
2. ändrad intern kostnadsfördelning
3. potentiellt realiserbar besparing för universitetet

En kostnadskomponent behöver minst stabilt sal-ID, avtalsobjekt, kostnadstyp, belopp, om kostnaden är undvikbar, uppsägningstid, tidigaste realiseringsdatum och eventuella engångskostnader.

Preliminär internhyra summeras endast som källprofil och behandlas inte som besparing. Källans internhyra och modellens scenariokostnad är två helt åtskilda profiler: ingen differens mellan dem beräknas eller publiceras. Teoretisk årlig potential och verifierad realiserbar besparing är `null` tills sal–avtal, undvikbarhet, uppsägningstid och engångskostnad kan beläggas.

Den äldre kapacitets- och termmotorn, med modulerna `cost_model.py` (blockerat sparresultat) och `cost_comparison.py` (separata kostnadsprofiler), är borttagen (finns i Git-historiken före den här grenen). Den gemensamma motorn redovisar kostnad som modellkostnad med scenariots proxypriser och ger aldrig en verifierad besparing; principen ovan gäller fortsatt för nästa kostnadsmodell.
