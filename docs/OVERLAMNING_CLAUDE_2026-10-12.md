# Överlämning till Claude – verksamhetsuppgifter 2026-10-02 (2026-10-12)

**Repo:** `gUUnnar/tentaoptimering`; **utgångspunkt:** PR #11 (`feature/ux-gemensam-korning`).  
**Primär källa:** den externa filen `Utvecklingsarbete 2-10-26.pptx` i projektunderlaget.  
**Kanonisk sammanställning i Git:** [`docs/VERKSAMHETSUNDERLAG_2026-10-02.md`](VERKSAMHETSUNDERLAG_2026-10-02.md).

## Uppdrag och avgränsning

Integrera de nya verksamhetsuppgifterna i arbetet med PoC:n **utan att göra presentationens preliminära värden till verifierade regler**. Syftet med PoC:n är fortfarande att undersöka hur lokaler och tentavakter kan optimeras samt hur stor den *realiserbara årliga* besparingspotentialen är. Användaren ska kunna justera verksamhetsparametrar löpande och ska **inte behöva välja bland på förhand låsta scenarier**.

Detta dokument är en prioriterad uppdragsöverlämning. Det inför **nya krav på valbar planeringsperiod och datagranskning i UX**, men ändrar inte motor, standardparametrar eller existerande scenariers dateringar i denna dokumentations-PR.

## Prioriterat att utreda och genomföra

1. **Bemanningstrappa:** presentationen anger min 2 vakter/pass, 2/3/4/5/6 vakter för 1–65/66–135/136–220/221–250/250–300 tentander. `config/scenarios/joint_underlay_period.toml` har 1/2/3 vid 50/150/300. Dokumentera skillnaden och föreslå hur alternativ bemanningstrappa ska kunna testas som parameter utan att den nya källan påstås vara avtalsregel. Klargör gränsen 250 och >300 innan en ny norm införs. Säkerställ bemanningskostnad, placering och eftervalidering har samma trappa.
2. **Perioden:** i senare PR #11-commits har det felaktigt namngivna helterminsscenariot redan blivit `joint_underlay_period.toml` för **12 januari–31 mars**. Behåll den rättelsen. **Det nya kravet är viktigare:** ersätt framtida beroende av ett fast scenariodatum med valbart start- och slutdatum inom dataunderlagets dokumenterade täckning; när januari–september-data har levererats ska de stödas efter import och verifiering. Redovisa alltid exkluderad/oklar efterfrågan.
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


## Kompletterat uppdrag 2026-10-12: valbar period och inspektion av data i UX

**Ändrat krav från beställaren:** en hel termin är **inte längre minsta tillåtna planeringsperiod**. Användaren väljer start- och slutdatum för en valfri sammanhängande period inom den tidsmässiga täckningen i dataunderlaget (t.ex. veckor, månader, termin, flera terminer). Den gamla formuleringen om en hel termin i tidigare krav/arbetsuppdrag är ersatt; se `docs/KONCEPTUELL_KRAVSPECIFIKATION.md` UX-9–11 och §11.8.

**Ny dataleverans:** beställaren kommer att tillhandahålla uppgifter **1 januari–30 september inklusive verklig beläggning**. Årtal, kolumner, relationer och definitioner måste verifieras vid import; behandla inte detta som en redan levererad källa. Bygg ut importen så att tillgänglig period och luckor per datatyp kan redovisas utan antaganden om fast terminslängd. Försök att planera utanför täckningen ska ge begripligt besked. Saknad beläggning = okänd, inte noll.

**Obligatoriskt läsflöde i UX, separat från optimering:**

1. Välj en **sal** och tidsperiod; visa vilka bokade tentamina och pass som nyttjar lokalen och, när observerad beläggning finns, hur stor del av tillgänglig tid/platser som faktiskt nyttjas (tydlig måttdefinition, nämnare och källa). Filtrera på dag/vecka/månad/valfritt datumintervall.
2. Sök en **viss bokad tentamen** (ID, kurs, datum). Visa historiskt datum, start/slut, samtliga salar och bokade platser samt tillhörande observerad beläggning där koppling och data räcker. Visa vid vald körning ett tydligt avskilt **simulerat schema** och förändringar mot bokningen. Provisoriska eller tvetydiga länkar mellan bokning och Ladok måste synas.
3. Inspektion ska fungera direkt efter dataimport **utan krav på simulering**, även om delar av populationen inte är optimeringsbara.

**Implementationsprinciper:** den valda tidsperioden måste ingå i körningens frusna specifikation och jämförbarhetsnyckel; filtrering ska göras på korrekta dataobjekt (bokning, tentamenshändelse, salplacering), utan dubbelräkning. Bestäm och testa vad som händer med tentor vars flyttfönster passerar vald periodgräns. Om årsbelopp härleds från en kortare period, redovisa antagandet och kalla inte skalningen verklig sparpotential.

**Framtida export:** målbilden är att en planeringsfil ska kunna **importeras i universitetets lokalbokningssystem**, men systemanpassad export/import är **utanför PoC** såvida det visar sig vara enkelt med ett faktiskt känt importkontrakt. En enkel maskinläsbar CSV/JSON kan vara frivillig utdata, men får inte kallas importerbar utan verifierad format-/ID-mappning. Ingen direkt integration eller produktionseffekt.

**Föreslagna acceptanstester:** valfritt datumintervall som skiljer sig från nuvarande fasta testintervall; period utanför täckning; salvisning med flera bokningar och uppmätt/okänd beläggning; tentamensuppslag som omfattar flera salar och oklar Ladokkoppling; historiskt vs simulerat schema; jämförelse som kräver identiska datumintervall. Uppdatera testerna efter nya dataleveransen.

**Prioritet:** (1) definiera datatäckning/periodval och validera befintlig motor, (2) läs-UX för sal och bokad tentamen, (3) importera verklig beläggning när källschemat finns, (4) export efter PoC. Samordna med Claudes pågående PR #11 och återanvänd befintlig kod; ändra inte `main` och merga inte utan användarens godkännande.


## Förtydligande 2026-10-12: snabb iteration är ett eget krav

Korta planeringsperioder behövs av **två oberoende skäl**:

1. **Verksamhet:** en betydande del av tentamensbokningarna görs med kort framförhållning. Enstaka dagar och veckor behöver kunna omplaneras på kort tid utan att andra redan lagda bokningar försvinner från salarnas tillgänglighetsbild.
2. **Utveckling/test:** andra funktioner (parameterredigering, körningsprogress, lokal-/tentamensvisning, jämförelse och senare filutdata) ska kunna funktionstestas genom **mycket snabba och reproducerbara körningar** av korta perioder eller små urval, med samma ordinarie API, validering och resultathantering.

Viktigt: det gamla kravet *minst en hel termin* var **inte genomförbart mot befintlig Ladokfil**, som slutar 31 mars. Det är inte terminslängden som är målet; användaren ska fritt välja planeringshorisont **inom för respektive funktion verifierad datatäckning**. För närvarande kan bokningar studeras fram till augusti medan efterfrågeunderlaget för optimering bara sträcker sig 12 januari–31 mars. Nytt underlag 1 januari–30 september inklusive verklig beläggning tillkommer senare.

**Prioritera korta testfall som förstaklassflöde.** Genomför minst ett dagsurval, ett veckourval och ett större urval; mät tid till första fullständigt verifierade lösning och total tid på definierad dator. UI ska kunna välja period och starta körningen **utan manuell TOML-hantering**. En snabb körning ska inte tappa kvalitetskontrollerna, och befintliga fasta bokningar utanför valt optimeringsurval som påverkar salarnas ledighet måste beaktas eller synligt deklareras som en begränsning. Kontrollera jämförbarhetsnyckeln så att olika perioder inte behandlas som identiska.

Se kravspecifikationen §11.9 och UX-9–11.
