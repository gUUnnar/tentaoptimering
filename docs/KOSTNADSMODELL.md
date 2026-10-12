# Struktur för kostnadsmodellen

Kostnadsmodellen ska hålla isär tre resultat:

1. minskat resursbehov, exempelvis färre samtidiga salar eller färre externa bokningar
2. ändrad intern kostnadsfördelning
3. potentiellt realiserbar besparing för universitetet

En kostnadskomponent behöver minst stabilt sal-ID, avtalsobjekt, kostnadstyp, belopp, om kostnaden är undvikbar, uppsägningstid, tidigaste realiseringsdatum och eventuella engångskostnader.

Preliminär internhyra summeras endast som källprofil och behandlas inte som besparing. Källans internhyra och modellens scenariokostnad är två helt åtskilda profiler: ingen differens mellan dem beräknas eller publiceras. Teoretisk årlig potential och verifierad realiserbar besparing är `null` tills sal–avtal, undvikbarhet, uppsägningstid och engångskostnad kan beläggas.

Den äldre kapacitets- och termmotorn, med modulerna `cost_model.py` (blockerat sparresultat) och `cost_comparison.py` (separata kostnadsprofiler), är borttagen (finns i Git-historiken före den här grenen). Den gemensamma motorn redovisar kostnad som modellkostnad med scenariots proxypriser och ger aldrig en verifierad besparing; principen ovan gäller fortsatt för nästa kostnadsmodell.

## Verksamhetskalkyler som ännu inte är besparingsberäkningar

[Presentation 2026-10-02](VERKSAMHETSUNDERLAG_2026-10-02.md) använder ”pengar i sjön” för kostnaden av skillnaden mellan **beställda platser** och **anmälda i Ladok** under januari–juni 2026. Två tabeller på samma bild ger **1 687 819,38 kr** respektive **1 779 583 kr**; slutbilden avrundar till **ca 1,8 mnkr/16 %**. Beräkningsskillnaden och beloppens komponenter måste verifieras. Ingen av siffrorna är ett belägg för hur mycket hyreskostnad universitetet kan säga upp.

Bemanningsbilden redovisar **1 228,5 timmar bomtid** och **191,5 timmar ”Övt”** under 2025, samt ungefär **250 000 + 44 000 = 294 000 kr** i bomtids-/mer- eller övertidskostnad. Definitionen av den senare posten är oklar i källan. Detta är historiska observations-/kalkylvärden och får inte utan motfaktiskt nuläge, tillämpade personalavtal och faktisk undvikbarhet bli en sparpost.

Modellen behöver därför särredovisa **överbeställning/utnyttjande**, **optimerat resursbehov**, **modellkostnad med oförändrad prisprofil** samt **faktiskt avvecklingsbar årskostnad**. Om två körningar använder olika kostnadsantaganden ska skillnaden inte rubriceras som effektivisering.
