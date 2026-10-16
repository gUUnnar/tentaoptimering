# Struktur för kostnadsmodellen

**Dokumenttyp:** styrande kostnadssemantik.
**Status:** gällande; verifierad realiserbar besparing är ännu datablockerad.

Kostnadsmodellen ska hålla isär tre resultat:

1. minskat resursbehov, exempelvis färre samtidiga salar eller färre externa bokningar
2. ändrad intern kostnadsfördelning
3. potentiellt realiserbar besparing för universitetet

En kostnadskomponent behöver minst stabilt sal-ID, avtalsobjekt, kostnadstyp, belopp, om kostnaden är undvikbar, uppsägningstid, tidigaste realiseringsdatum och eventuella engångskostnader.

Preliminär internhyra summeras endast som källprofil och behandlas inte som besparing. Källans internhyra och modellens scenariokostnad är två helt åtskilda profiler: ingen differens mellan dem beräknas eller publiceras. Teoretisk årlig potential och verifierad realiserbar besparing är `null` tills sal–avtal, undvikbarhet, uppsägningstid och engångskostnad kan beläggas.

Den äldre kapacitets- och termmotorn, med modulerna `cost_model.py` (blockerat sparresultat) och `cost_comparison.py` (separata kostnadsprofiler), är borttagen (finns i Git-historiken före den här grenen). Den gemensamma motorn redovisar kostnad som modellkostnad med scenariots proxypriser och ger aldrig en verifierad besparing; principen ovan gäller fortsatt för nästa kostnadsmodell.

## Besparingspotential mot en referensoptimering med låsta datum

Resultatvyn redovisar en **teoretisk årlig besparingspotential**: modellkostnaden för en **referensoptimering med låsta datum** (tidigare kallad Nuläge) minus modellkostnaden för körningen. Referensen är en modellkörning, inte den faktiska bokningen (A), som aldrig optimeras och inte har någon kostnad per tentamen i underlaget. Tre sorters kostnad hålls isär: *historisk* (A: saknas), *modellberäknad* (körningar) och *teoretisk besparingspotential* (skillnaden mellan två modellkostnader). Referensen är samma scenario, data, lokalbestånd, bemanningsregler och kostnadsantaganden, men ingen tentamen får flyttas från sitt ursprungstillfälle (`flex.movable_types = []`); salar och bemanning optimeras fortfarande. Skillnaden är därför effekten av planeringsflexibiliteten. Den gäller de valda tentorna och scenariots proxypriser. Verifierad realiserbar besparing förblir `null` tills sal–avtal, undvikbarhet, uppsägningstid och engångskostnad kan beläggas, och källans internhyra jämförs aldrig mot modellkostnaden.

## Verksamhetskalkyler som ännu inte är besparingsberäkningar

[Presentation 2026-10-02](VERKSAMHETSUNDERLAG_2026-10-02.md) använder ”pengar i sjön” för kostnaden av skillnaden mellan **beställda platser** och **anmälda i Ladok** under januari–juni 2026. Två tabeller på samma bild ger **1 687 819,38 kr** respektive **1 779 583 kr**; slutbilden avrundar till **ca 1,8 mnkr/16 %**. Beräkningsskillnaden och beloppens komponenter måste verifieras. Ingen av siffrorna är ett belägg för hur mycket hyreskostnad universitetet kan säga upp.

Bemanningsbilden redovisar **1 228,5 timmar bomtid** och **191,5 timmar ”Övt”** under 2025, samt ungefär **250 000 + 44 000 = 294 000 kr** i bomtids-/mer- eller övertidskostnad. Definitionen av den senare posten är oklar i källan. Detta är historiska observations-/kalkylvärden och får inte utan en jämförbar motfaktisk referens, tillämpade personalavtal och faktisk undvikbarhet bli en sparpost.

Modellen behöver därför särredovisa **överbeställning/utnyttjande**, **optimerat resursbehov**, **modellkostnad med oförändrad prisprofil** samt **faktiskt avvecklingsbar årskostnad**. Om två körningar använder olika kostnadsantaganden ska skillnaden inte rubriceras som effektivisering.

## Betald personaltid, externhyra och avtalsobjekt (gemensam kostnad)

Modellkostnaden för en körning har fem komponenter som redovisas var för sig och summerar exakt till totalen: långsiktiga salar (en gång per använd sal, även en sal som bara används genom en fast bokning), externa salstillfällen (per tillfälle), **betald personaltid**, vaktpool (årskostnad per samtidig resurs, noll när paketet inte anger någon) och rörlig kostnad per vakt och salstillfälle.

**Betald personaltid** härleds ur placeringen, inte ur en schablon. Varje vaktposition i ett salstillfälle är ett betalt pass från `start − förberedelse` till `slut + avslut`; betald tid är det längre av arbetad tid och kortaste betalda pass (2 timmar enligt lokalt kollektivavtal §2.2), plus salens betalda restid. Kostnaden är betalda minuter gånger kostnaden per betald minut. Därför kan motorn välja en lösning med fler betalda personaltimmar när lokalbesparingen är större, och en lösning med färre timmar när personalen är dyrare. Gränser: luckor mellan en persons pass betalas inte (varje pass är eget), och dygnsvila, högsta arbetstid per dygn, rast och veckonorm ingår inte (`staffing.max_daily_minutes` m.fl. är `contract_only`). Det som inte modelleras redovisas som `not_evaluated`, aldrig som uppfyllt.

**Avtalsobjekt och realiserbarhet.** Motorn prissätter varje sal med sin tilldelade årskostnad; att en sal slutar användas minskar därför modellkostnaden. Om hyran kan avvecklas avgör `cost_realization.py` mot avtalsobjektet: `verified` kräver observerade avtalsuppgifter, att avtalet kan avvecklas och att inga andra rum i avtalet används; `possible_unverified` när villkoren är simulerade, antagna eller beräknade; `blocked_shared` när avtalet delas med en sal som används; `blocked_contract` när avtalet inte kan sägas upp; `conditional` när avtalsobjekt eller villkor saknas. En extern bokning som undviks är en undviken debitering, men verifierad bara med observerade villkor. Med simulerade uppgifter är den verifierade besparingen alltid noll.

**Fyra slags kostnad blandas aldrig** (visas så i jämförelsen): historisk kostnad (saknas för A), modellberäknad kostnad, teoretisk årlig potential (beräknas inte: årsomräkning och efterfrågeprofil för den ej simulerade tiden saknas) och verifierad realiserbar besparing.

**A prissätts med körningens regler.** A (faktisk bokning) ändras aldrig. För att få en jämförbar siffra prissätts de historiska bokningarna av samma regler och priser som den körning de jämförs med (`joint_pricing.py`), märkt *modellberäknad kostnad för de historiska bokningarna*; bemanningen räknas ur bokade platser per sal. Kan en bokning inte prissättas (sal utanför körningens lokalbestånd, ingen bokning) redovisas den och ingen totalskillnad visas. En bokning med bara adress godtas under en temporär regel: adressen antas ha en sal med fler platser än antalet anmälda, hyran är okänd och räknas som noll, så A:s modellkostnad är då en underkant och märks så.

**Utnyttjande skiljs från priser.** Mellan två körningar delas skillnaden i *ändrat resursutnyttjande* (den högra planen prissatt med den vänstra körningens priser, minus den vänstras kostnad) och *ändrade priser, regler eller antaganden* (resten). Kan den högra planen inte prissättas med de vänstra priserna (en sal saknar pris där) anges varför uppdelningen saknas.
