# Uppdrag till Codex – teknisk inventering och arkitekturförslag
**Datum:** 2026-10-08  
**Omfattning:** Kodgranskning och förslag. Ingen implementation i detta steg.

## Uppdragets syfte
Undersök hur den lokala kodbasen kan användas för en PoC som optimerar **tentamensdatum/pass, lokaler och personal i en gemensam långsiktig årskostnadsmodell**. Den ska planera minst en termin och uppfylla all obligatorisk efterfrågan inom vald omfattning. Styrande verksamhetskrav finns i [kravspecifikationen](KONCEPTUELL_KRAVSPECIFIKATION.md).

## Arbetsplats och säker hantering
- Lokal arbetskatalog: `C:\lokalt\tentalokaler\PoC`.
- Rådata: `C:\lokalt\tentalokaler\underlag` (skrivskyddade).
- Börja med att kontrollera aktuell branch, remote, `git status`, opushade commits, ocommittade och ignorerade filer, installerade paket, aktuell CLI, rapporter och testsvit.
- Bevara alla lokala ändringar. Inga kod-, data- eller Git-muteringar i detta uppdrag. Gör ingen reset, pull, checkout, merge eller rebase.

## Krav som granskningen ska mäta mot
1. **Alla obligatoriska tentamina och tentander placeras.** Solverstatus och genomförbarhet måste spegla täckning; om fullständig lösning inte går att hitta ska programmet redovisa detta och ge diagnostik.
2. **Kalenderbaserad planering över minst en termin.** Datum, tentamensperioder, extra dagar, helger och provpass ska kunna vara tillåtna eller otillåtna enligt justerbara regler. Ursprungsschema får vara fast, önskemål eller flexibelt.
3. **Integrerad ekonomi.** Lokalportfölj, externa hyrperioder och anonymiserade vakters arbetsdagar, förflyttning och bomtid ska ingå i samma årskostnad. Bemanningsstorlek är en ekonomisk variabel.
4. **Verksamhetsvillkor.** Absoluta kapacitetsgränser, digital kompatibilitet, Uppsala/Visby, kurs-/programkrockar, samtidig start vid samlokalisering, olika tillåtna sluttider, ingen löpande nyinsläppning, ställtid och arbetstidsregler.
5. **Scenarier och kompletterande data.** Procentuell deltagarvariation, framtida digital andel, transparenta antaganden och stabilt gränssnitt för att senare ersätta uppskattningar med faktiska data.

## Inventera särskilt
- Representationen av en unik tenta och deltagarantal, relationer mellan bokningar/Ladok/salplaceringar och risker för dubbelräkning.
- Solverns beslutsvariabler, hårda villkor, eventuella mjuka villkor, status och optimeringsmål.
- Kalender- och tidsrepresentation, salernas beläggning, ställtid och digitalt format.
- Personalkostnader, bemanningsregler, restider, raster, arbetsdagar och långsiktig personalvolym.
- Hyreskostnader för fasta och externa lokaler; beräkningsmetod för långsiktig årskostnad och besparingspotential.
- Antaganderegister, parametergränssnitt, rapportering, tester och möjlig beräkningskomplexitet på en hel termin.

GitHub-`main` har vid en tidigare fjärrinventering visat datainläsning, normalisering, validering och kostnadsstrukturer. Den lokala kodbasen kan innehålla ytterligare solvermoduler. Fastställ vad som faktiskt finns i arbetskatalogen innan designförslag lämnas.

## Leverans
Lämna **ett kort tekniskt granskningsunderlag** med:
1. Lokal revisionsstatus och verifierade moduler.
2. Kravuppfyllnad per del: uppfyllt, delvis uppfyllt, saknas eller kan ännu inte verifieras.
3. En minimal sammanhängande målarkitektur som separerar källdata, antaganden, scenariokonfiguration, gemensam solver och resultat.
4. Prioriterade kodåtgärder, vad som kan behållas och uppskattade tekniska risker.
5. Testförslag med kända förväntade resultat: full efterfrågetäckning, oförenliga toppar, kapacitetstak, kurskrock, digitalt format, blandade sluttider, ställtid, vakters arbetstid/förflyttning samt avvägningen mellan lokaler och personalkostnader.
6. En plan för att kunna göra en första terminskörning med tydliga antaganden och senare ersätta dessa med verifierade uppgifter.

**Arbetet avslutas med förslag för användarens godkännande, innan implementation inleds.**
