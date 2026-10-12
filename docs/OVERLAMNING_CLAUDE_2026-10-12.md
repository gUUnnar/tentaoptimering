# Överlämning till Claude – verksamhetsuppgifter 2026-10-02 (2026-10-12)

**Repo:** `gUUnnar/tentaoptimering`; **utgångspunkt:** PR #11 (`feature/ux-gemensam-korning`).  
**Primär källa:** den externa filen `Utvecklingsarbete 2-10-26.pptx` i projektunderlaget.  
**Kanonisk sammanställning i Git:** [`docs/VERKSAMHETSUNDERLAG_2026-10-02.md`](VERKSAMHETSUNDERLAG_2026-10-02.md).

## Uppdrag och avgränsning

Integrera de nya verksamhetsuppgifterna i arbetet med PoC:n **utan att göra presentationens preliminära värden till verifierade regler**. Syftet med PoC:n är fortfarande att undersöka hur lokaler och tentavakter kan optimeras samt hur stor den *realiserbara årliga* besparingspotentialen är. Användaren ska kunna justera verksamhetsparametrar löpande och ska **inte behöva välja bland på förhand låsta scenarier**.

Detta dokument är en prioriterad uppdragsöverlämning och registrerar i nuläget **inga ändringar av motor, parametrarnas standardvärden eller beräkningsperiod**.

## Prioriterat att utreda och genomföra

1. **Bemanningstrappa:** presentationen anger min 2 vakter/pass, 2/3/4/5/6 vakter för 1–65/66–135/136–220/221–250/250–300 tentander. `config/scenarios/joint_full_term.toml` har 1/2/3 vid 50/150/300. Dokumentera skillnaden och föreslå hur alternativ bemanningstrappa ska kunna testas som parameter utan att den nya källan påstås vara avtalsregel. Klargör gränsen 250 och >300 innan en ny norm införs. Säkerställ bemanningskostnad, placering och eftervalidering har samma trappa.
2. **Perioden:** scenariot ”Hela terminen VT 2026” slutar 31 mars; verksamhetens diagram avser januari–juni med betydande toppar i juni. Välj rättvisande benämning eller full terminsomfattning **efter kontroll av tillgängliga data och prestanda**. Kom ihåg exkluderad/oklar efterfrågan.
3. **Pass per sal och dag:** lägg till eller verifiera att `calendar.start_times`, tentamenslängd, för-/efterarbete och salens tillgänglighet tillåter **experiment med upp till tre faktiskt genomförbara pass/dag**. Inte tre pass som default eller fast scenario; detta är ett *prövningsalternativ*. Saknad längddata ska inte döljas.
4. **Beståndet:** presentationen redovisar 7 salar, 1 109 platser + 41 RPS; nuvarande register anger andra summor och har tids-/kapacitetsluckor. Mappa salnamn, platsdefinition, RPS och giltighetstid; hitta inte på saknade rum eller kapaciteter.
5. **Kostnad och besparingar:** verksamhetens ”pengar i sjön” ligger 1 687 819 respektive 1 779 583 kr i **olika tabeller på samma bild**; slutbilden anger ca 1,8 mnkr. Detta avser gap mellan beställda och anmälda platser, inte undvikbar hyra. Även 294 000 kr i personalrelaterade bom-/mer-/övertidskostnader är historisk observation, inte garanterad reducerbar kostnad. Kräver avtalsobjekt, bemanningsdata, uppsägningstid och referensberäkning före sparpåstående.
6. **Nuläge och jämförelser:** Nuläge ska beräknas med **samma data, period, kostnadsantaganden och personalregler** som simuleringen, utom explicit ändrade flexibilitetsparametrar/efterfrågevariation. Ingen resultattext får kalla en skillnad beroende på *ändrat pris* för optimeringsbesparing. Knyt arbetet till `docs/KONCEPTUELL_KRAVSPECIFIKATION.md` §11.4 (N-1, N-3, N-5, N-9).
7. **Windowsdistribution:** bibehåll kravet att användaren installerar/startar på vanlig Windows-dator utan Python, Node, Docker eller separat DB; allt lokalt. Verifiera detta efter PR #11 på ren offline-Windowsmiljö.

## Teknisk kontroll vid fortsatt arbete på PR #11

Vid tidigare granskning av commit `36053dd` noterades bl.a. felobjekt i Reacts felhantering, motsägelsefull `finished`-händelse vid fel i slutlagring, skillnad mellan backendens *antal* och frontendens *lista* av avvikande parametrar, samt en kostnadsjämförelse som kan tolka prisändringar som förbättring. **Kontrollera om dessa redan rättats i nyare PR-commits; återinför inte gamla fel och duplicera inte kodändringar i onödan.** Se befintliga inline-kommentarer i PR #11.

Kontrollera bland annat:
- teknisk lösningsstatus vs eftervalidering, även vid avbruten/korrupt körning;
- att kostnadsjämförelse inte blandar olika kostnadsantaganden;
- att parameterändringar sparas och visas med samma kontrakt;
- att helterminsresultat redovisar täckning, saknade grupper, parametrar och solver-gap;
- att påverkansmått och möjlig ekonomisk potential förblir skilda.

## Beslut att inhämta

Be verksamhetsägaren verifiera 1 109 + 41 platser, bemanningstrappan och intervallgränserna, definitionen av ”pass”, förekomsten av tre starttider, Retendo kontra manuella arbetspass, skillnaden mellan två kostnadsberäkningar samt vad som räknas som faktisk närvaro. Fram till dess: **modellera öppet och känslighetspröva, inte fastslå**.

Ändra inte huvudscenariots förutsättningar, dold affärslogik eller lagstadgade krav på basis av denna överlämning utan explicit beslut. `main` ska inte ändras utan separat granskning/godkännande enligt `AGENTS.md`.
