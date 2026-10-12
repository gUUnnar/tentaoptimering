# Verksamhetsunderlag: Utvecklingsarbete 2-10-26

**Källa:** `Utvecklingsarbete 2-10-26.pptx`, överlämnad inom projektet Tentalokaler. Materialet sammanfattar lokalbokning/utnyttjande under **VT 2026** och bemanning under **2025**. Siffrorna nedan är *återgivna uppgifter i presentationen*, inte verifierade källdatamått eller beslutade verksamhetsregler. Presentationsfilen och dess inbäddade kalkylbilder läggs inte i Git.

**Datum för genomgång:** 2026-10-12. **Status:** kompletterande verksamhetsuppgift – kräver avstämning med data-/verksamhetsägare innan den används som hård regel eller som underlag för sparpåstående.

## 1. Lokaler och pass (bilden ”Lokalresurser”)

| Mått enligt presentationen | Värde |
| --- | ---: |
| Ordinarie tentamenssalar | 7 |
| Platser i ordinarie salar | 1 109 |
| RPS-lokal | 1 lokal, 41 platser |
| Vanligt antal pass | 2 per sal och dag (förmiddag/eftermiddag) |
| Skrivplatstillfällen vid två pass, ordinarie salar | 2 218 per dag |
| Skrivplatstillfällen vid två pass, RPS | 82 per dag |

Presentationens **förslag att undersöka**, inte ett beslutat villkor: **tre separata skrivtider per sal och dag** beroende på tentamenslängd, tentamenstyp och studentantal. Skilj salarnas fysiska kapacitet (platser) från *platstillfällen* (platser multiplicerat med antal genomförbara pass). Fler pass kan kräva ändrad bemanning och måste prövas mot tentamenslängd, för- och efterarbete, raster och lokaltillgänglighet.

**Avstämning:** presentationens 1 109 ordinarie platser är inte samma tal som tidigare summeringar ur universitetets publicerade salregister; salarnas identiteter, giltighetstid och eventuell avgränsning behöver stämmas av. RPS-totalen 41 platser säger inget om kapaciteten hos enskilda rum.

## 2. Belastning och efterfrågan (bilden ”Närvaro – anmälda – totala skrivplatser VT-26”)

Presentationens månadsvis angivna *planerade platser* januari–juni 2026:

| Månad | Planerade platser |
| --- | ---: |
| Januari | 21 641 |
| Februari | 15 449 |
| Mars | 28 182 |
| April | 12 611 |
| Maj | 14 322 |
| Juni | 22 411 |
| **Summa** | **114 616** |

Kurvorna jämför **närvaro**, **anmälda i Ladok** och **justerat totalt antal skrivplatser** dag för dag. De är olika mått och får inte blandas i efterfrågevariabeln. Kurvorna visar tydliga toppar i **januari, mars och början av juni**. Bilden anger ungefär **35 % papperstentor** och **65 % e-tentor**, utan tillräckligt definierad beräkningsmetod för att använda talen som verifierad digitalandel i modellen.

**Konsekvens för nuvarande testfall:** `config/scenarios/joint_full_term.toml` i PR #11 avser endast **2026-01-12–2026-03-31**, trots etiketten ”Hela terminen VT 2026”. Det täcker inte topparna i april–juni, särskilt inte juni. Ändra inte tidsgränserna tyst: välj antingen en rättvisande etikett för kvartalsurvalet eller definiera och prestandatesta ett verkligt helterminsurval. Redovisa även exkluderad/oklar efterfrågan.

## 3. Lokalrelaterade ekonomiska uppgifter (bilden ”Pengar i sjön” för VT-26)

Presentationen definierar ”pengar i sjön” som **kostnad för gapet mellan beställda platser och anmälda studenter i Ladok**; det är en verksamhetsmässig kalkyl över överbeställning, **inte en realiserbar hyresbesparing**.

Bilden innehåller två parallella kalkylsammanställningar som **inte överensstämmer**:

| Redovisning i samma bild | Summerad kostnad | ”Pengar i sjön” |
| --- | ---: | ---: |
| Vänster pivottabell | 11 386 097,13 kr | 1 687 819,38 kr |
| Höger tabell, fördelad per vetenskapsområde | 11 595 654 kr | 1 779 583 kr (ca 15 %) |

Högertabellens ”pengar i sjön” per vetenskapsområde: **HumSam 895 062 kr (20 %)**, **MedFarm 269 024 kr (13 %)**, **TekNat 615 497 kr (12 %)**. Presentationens slutbild avrundar bedömningen till **ca 1,8 mnkr och 16 %**. Orsaken till skillnaden mellan pivottabellerna framgår inte.

**Tolkning:** kostnaden kan vara relevant som mått på beställningsprecision/intern kostnadsfördelning, men kan inte dras av från universitetets totalkostnad utan identifierade undvikbara kostnader, avtalsobjekt och uppsägningstid. Den ska inte användas som målfunktionens facit eller som en prognos för faktisk besparing.

## 4. Bemanning (bilderna ”Personal – tentavakter och behov” m.fl.)

Presentationen uppger **86 aktiva tentavakter**, varav **20 anställda**. Detta är en ögonblicksuppgift utan specificerad referensdag; det är inte verifierad schematillgänglighet för varje datum.

Presentationen visar följande **verksamhetstrappa för antal vakter per arbetspass**:

| Antal tentander | Vakter/pass |
| --- | ---: |
| 1–65 | 2 |
| 66–135 | 3 |
| 136–220 | 4 |
| 221–250 | 5 |
| 250–300 | 6 |

Texten anger dessutom **alltid minst två vakter per arbetspass**. Observera överlappningen vid **250 tentander** mellan de två sista intervallen. Regler för mer än 300 tentander, stora salar, samtidiga tentor och undantag framgår inte. Det är **verksamhetsuppgift att verifiera**, inte en regel ur det lokala kollektivavtalet.

Vid fullt utnyttjande av samtliga salar förmiddag och eftermiddag anges **64 arbetspass** som ett maxat bemanningsbehov en enskild dag och **32 arbetspass** vid ”minsta möjliga aktivitet”. Det framgår inte tillräckligt väl om ordet arbetspass avser bemannade vaktpass, vaktpersoner eller någon annan enhet. Använd inte 32/64 som hård kapacitetsgräns utan definition.

**Januari–februari 2025 enligt Retendo:** januari **755 pass**, varav **242 anställda och 513 timanställda**; februari **467 pass**, varav **156 anställda och 311 timanställda**. Motsvarande manuella räkningar anges som **740** respektive **433** pass, alltså olösta skillnader mot Retendo. Totalt för de två månaderna: **1 222 pass**, **398 anställda** och **824 timanställda**. Perioden bör inte förväxlas med ett helt år.

**Bemanningsrelaterad tid/kostnad för hela 2025:** **1 228,5 timmar ”Bom”**, **191,5 timmar ”Övt”** samt **17 124 timmar totalt**; presentationen anger cirka **7 % bomtid**. De redovisade ungefärliga kostnaderna är **250 000 kr för bomtid** och **44 000 kr för ”mertid”** (samtidigt som kolumnrubriken säger ”Övt”), sammanlagt **294 000 kr**, avrundat till ”nästan 300 000 kr”. Mertid/övertid bör definieras och stämmas av före kostnadsmodellering.

**Skillnad mot befintligt exempel:** `joint_full_term.toml` använder trappan **1/2/3 vakter upp till 50/150/300**, vilket inte motsvarar verksamhetsuppgiften ovan. Ändra inte en giltig PoC-testkonfiguration till påstått verifierad verklighet utan beslut; gör avvikelsen tydlig, pröva gärna en separat sensitivitet med den nya trappan och säkerställ testad täckning även över 300.

## 5. Frågor till verksamhets- och dataägare

1. Vilka **sju salar** och vilken **RPS-lokal** omfattar 1 109 + 41 platser; vad är historisk och aktuell kapacitet och vilka enheter kan faktiskt avvecklas?
2. Är **bemanningstrappan**, två-vaktsminimum och tredelade skrivpass beslutade? Hur definieras vakter per *sal*, *tenta* respektive *pass*; hur hanteras 250 och fler än 300 tentander?
3. Vilka data visar **verklig närvaro**, och hur har antalet beställda, anmälda och faktiskt närvarande platser beräknats för VT26?
4. Varför skiljer **1 687 819 kr** från **1 779 583 kr**, och vilka kostnadsposter ingår i respektive belopp?
5. Hur ska *bomtid*, *mertid*, *övertid*, vaktpool och kostnader avgränsas; kan Retendo-export (utan personuppgifter) komplettera testunderlaget?
6. Ska en helterminssimulering omfatta även **april–juni**, och finns data så att alla relevant tentor och lokaler ingår?

## 6. Användning i PoC

- Bevara presentationens siffror som **redovisade källuppgifter** med datum och känd osäkerhet.
- Låt **verifierade kollektiva avtal** fortsätta styra rättsliga hårda villkor; verksamhetstrappan blir verifierad först efter sakgranskning/beslut.
- Håll isär **beställningsprecision**, **ändrat resursbehov**, **modellkostnad** och **realiserbar besparing**.
- Simulera tre pass per dag som en **valbar parameter/förutsättning**, inte som fördefinierat scenario eller som fast policy.
- Dokumentera exakt planeringsperiod, ort, beräkningsbar population, exkluderade aktiviteter och alla kostnadsantaganden vid jämförelser.

Se även [Analys av kollektivavtalet](ANALYS_KOLLEKTIVAVTAL.md), [Kostnadsmodell](KOSTNADSMODELL.md) och [Blockerande datagap](BLOCKERANDE_DATAGAP.md).
