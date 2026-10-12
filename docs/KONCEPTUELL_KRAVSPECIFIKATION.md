# Kravspecifikation – optimering av tentamensverksamhet

**Projekt:** Tentaoptimering, Uppsala universitet  
**Version:** 2026-10-08  
**Status:** Konceptuell verksamhetskravspecifikation för PoC

## 1. Syfte och förväntat resultat

PoC:n ska beräkna hur tentamensverksamhetens långsiktiga **årliga totalkostnad** kan minskas genom att tentamenstillfällen, tentamenslokaler och tentamensvakter planeras gemensamt. Den ska ge ett beräknat ekonomiskt optimum eller den bästa hittade genomförbara lösningen inom tillgänglig beräkningstid, redovisa osäkerhet och jämföra med en tydligt beskriven nulägeskostnad.

Minsta planeringsperiod är **en termin**. Flera terminer kan kombineras. Ekonomiska resultat redovisas i **kronor per år**. PoC:n avser i första hand långsiktig strukturell potential: faktisk genomförbarhet enligt hyresavtal, uppsägningstider och omställningskostnader kan utredas separat.

## 2. Modellens beslut och gemensam målfunktion

Optimeraren beslutar inom valda verksamhetsregler:
- vilka tillåtna datum och skrivpass som används för respektive tentamen,
- hur varje tentamens deltagare fördelas mellan kompatibla salar och vilka salar som nyttjas,
- vilka långsiktiga lokalalternativ och kortvariga externa hyrperioder som behövs,
- hur många anonymiserade tentamensvakter som behövs, hur arbetsdagar läggs upp och hur vakterna fördelas mellan salar och byggnader.

**Målfunktion:** minimera jämförbar långsiktig årskostnad för långsiktiga lokaler, korttids-/externhyror, personal, betalda förflyttningar och andra relevanta kostnader. Undvik dubbelräkning av betald arbetstid, bomtid och resor. Personalvolym, arbetstimmar och bomtid är kostnadsvariabler; ingen förutbestämd personalstyrka är ett kapacitetstak.

En förändring av historiskt datum, startpass eller lokal ska göras när nyttan motiverar den. Använd verklig administrationskostnad när den kan beläggas och annars en separat justerbar preferens som kan avgöra mellan ekonomiskt likvärdiga lösningar.

## 3. Genomförbarhet och hårda begränsningar

En godkänd lösning ska uppfylla **hela den obligatoriska efterfrågan** inom vald PoC-omfattning. Alla ingående tentamina och dimensionerande tentander ska kunna skriva. Modellen får inte minska kostnaderna genom att lämna tentamina eller personer oplacerade. Om fullständig placering inte kan visas redovisas statusen tydligt; ett partiellt schema kan användas enbart för separat kapacitetsdiagnostik.

- Varje sals fysiska skrivplatsantal är ett **absolut tak**.
- Digitala tentamina placeras endast i lokaler med nödvändig digital teknik.
- Uppsala och Visby är **separata planeringsområden**; tentander och personal flyttas inte mellan orterna.
- Tentamina för samma kurs eller utbildningsprogram får inte kollidera. Om koppling till program saknas måste begränsad kontrolltäckning redovisas.
- Tillämpliga lagar, avtal, arbetstidsregler, raster, vila, bemanning och kompetenskrav gäller alla personalresurser.
- **Särskilt pedagogiskt stöd och särskild stöd-sal** ingår inte i den inledande optimeringsomfattningen. Deras efterfrågan och kapacitet hålls konsekvent utanför och redovisas separat.

## 4. Kalender och tentamenstillfällen

Modellen omfattar minst en hel termin, med parameterstyrda tillåtna kalenderdatum, skrivperioder, dagar (inklusive möjliga helger), provpass och startfönster. Ursprungligt datum, starttid och lokal kan vara bindande, önskat med prioritet eller flexibelt inom scenarioinställningarna.

Varje tentamen har normalt en given skrivtid. En möjlig parameter `max_exam_duration_hours` representerar ett **explicit verksamhetsexperiment** med ändrade examinationsvillkor och måste redovisas som sådant.

Olika tentamina får samlokaliseras och kan ha olika sluttider under ett gemensamt salstillfälle. Deltagarna börjar vid samma starttid för salen. Ny grupp får börja först sedan samtliga i föregående tillfälle avslutat och den justerbara ställtiden passerat. En tentamen får delas över flera salar vid samma tillfälle utan dubbelräkning av deltagare. Utgångsantagande är ett gemensamt starttillfälle per tentamen.

Ställtid anges med en konfigurerbar tidsparameter, t.ex. `turnaround_minutes`.

## 5. Lokaler

Lokaldata ska beskriva stabilt sal-ID, ort, byggnad, position, fysisk kapacitet, digital kompatibilitet, tillgänglighet och kostnads- eller avtalsvillkor.

**Långsiktigt disponerade lokaler** modelleras som en strukturell årskostnad. PoC:n ska kunna undersöka ett mindre eller annorlunda lokalbestånd, även genom ett hypotetiskt ersättningsalternativ med färre salar och angiven uppskattad hyra. Sådana ersättningshyror markeras som antaganden tills en verklig lokal och ett avtal är kända.

**Tillfälligt hyrda lokaler** modelleras med faktiska eller uppskattade debiteringsperioder, exempelvis dag eller sammanhängande hyrperiod. Digital kompatibilitet gäller även för dem. Teknikinvesteringar är endast ett möjligt framtida analysalternativ för långsiktigt disponerade lokaler och ingår inte i inledande kalkyl.

## 6. Tentamensvakter

Vakter representeras av **anonymiserade personalresurser**, med arbetstid, kostnad, anställnings-/avtalskategori, kompetens och tillgänglighet. Antalet resurser kan varieras och bestämmas utifrån totalt ekonomi- och bemanningsbehov.

Bemanningskrav anges som verifierbara eller preliminära regler kopplade till **antal samtidigt skrivande tentander per sal och tidsintervall**. Möjligheten att minska bemanningen när deltagare avslutar är en scenarioinställning som endast aktiveras när regelverket medger det.

En vakt kan arbeta vid flera tentamenstillfällen och i olika byggnader under samma dag inom samma ort. Modellen ska respektera restider, förberedelse, avslut, rast, vila, tillämpliga avtal, arbetspass och eventuell betald bomtid. Förflyttning och förberedelse får inte överlappa andra tilldelade arbetsuppgifter.

Dagens uppgifter om cirka 86 aktiva vakter, varav cirka 20 anställda, är **indata för nulägesbeskrivningen**, inte en begränsning av framtida bemanningsvolym. Bemanningsintervall som anges i verksamhetens presentationer behöver valideras och hanteras som lätt utbytbara regeldata.

## 7. Efterfrågan och framtidsscenarier

Historiska bokningar kombineras med Ladokuppgifter för att dimensionera antalet tentander. Separera önskade platser, anmälda tentander och verifierad faktisk närvaro. För varje körning dokumenteras vilket efterfrågemått som används.

- `demand_variation_pct`: gemensam procentuell förändring av **antal tentander per tentamen**. Antalet tillfällen ändras inte; avrundning anges explicit.
- `digital_exam_share_pct`: hypotetisk andel digitala tentamina vid en framtida tidpunkt; vilka prov som klassificeras om och hur det sker måste vara reproducerbart.
- Tillåtna datum, helger, skrivpass, ställtider, tidspreferenser och verksamhetsregler ska kunna väljas i scenariokonfigurationen utan godtyckligt snäva hårdkodade intervall.

## 8. Datakällor och antaganden

Befintliga datakällor i `C:\lokalt\tentalokaler\underlag`:
- `Tentaplaceringar_Export_2025-09-01-2026-08-31.xlsx` – historiska boknings-/placeringsposter.
- `Utsökning Ladok tentander från tidigare termin.xlsx` – Ladokbaserade deltagaruppgifter, inte automatiskt verifierad närvaro.
- `2026 Tentamenslokaler.xlsx` – lokal-/kostnadsrader som behöver kopplas till verkliga salar.
- Verksamhetsdokument, beslut, tillämpningsregler, avtal och utvecklingspresentationer.

PoC:n ska vara **körbar med tillgängligt material**. Saknade uppgifter får ersättas med kvalificerade, uttryckligen märkta antaganden. Varje antagande ska ange namn, värde, enhet, motivering, källa, giltighet och status. Antaganden ska kunna ersättas med inkommande data utan ombyggnad av solverlogiken.

Källdatamodellen ska hålla isär **tentamensbehov/beställning, historisk salplacering, Ladokaktivitet, faktisk sal och avtals-/kostnadsobjekt**. Kopplingsosäkerhet och exkluderade poster redovisas.

## 9. Resultat och kvalitetskrav

Varje körning ska dokumentera konfiguration, dataversion, antaganden, modellerad omfattning, solverstatus, beräkningstid och eventuell optimalitetslucka. Rapporten ska visa:
- total efterfrågan och bevisad fullständig täckning, eller uttryckligt uteblivet genomförbarhetsresultat,
- schema och ändringar från ursprungligt datum, pass och lokal,
- belastning, lokalportfölj, korttidsinhyrningar och tillgång till digitala platser,
- personalvolym, arbetstid, bomtid och förflyttningar,
- kostnad per kategori, total långsiktig årskostnad och teoretisk årlig besparingspotential jämfört med definierad baslinje,
- osäkerheter och skillnad mellan hypotetisk respektive avtalsmässigt genomförbar besparing.

Resultaten ska vara tillgängliga både i det lokala användargränssnittet (avsnitt 11) och som maskinläsbara filer. Utvärdera modellen först med små syntetiska fall med kända svar och därefter med en hel termins historiska data.

## 10. Öppna databehov

För att minska osäkerheten behöver projektet verifierade uppgifter om faktisk närvaro, kurs–programkopplingar, salarnas teknik och kapacitet, externa hyrperioder och priser, alternativa lokalers hyresnivåer, personal- och transportkostnader samt detaljerade bemannings-/arbetstidsregler. Lösningen ska kunna omvärderas utan programombyggnad när dessa uppgifter blir tillgängliga.

Följande uppgifter avgör särskilt hur långt resultaten kan tolkas: kurs-/programöverlapp eller studentöverlapp (utan dem är varje flytt av ordinarie tentor en övre gräns för potential), regler för omtentamen och fastställda tentamensperioder, kapacitet och kalender för alla använda lokaler utanför de publicerade salarna, samt avskrift och verifiering av det lokala kollektivavtalet för tentamensvakter.

## 11. Användargränssnitt och experimentellt arbetsflöde

Syftet med PoC:n är att kunna **undersöka hur ändrade planeringsförutsättningar påverkar behovet av lokaler och vakter**. Det kräver ett användargränssnitt som utgår från användarens arbete och inte från programmets interna struktur.

### 11.1 Begrepp

| Begrepp | Betydelse |
|---|---|
| **Dataunderlag** | Oföränderlig ögonblicksbild av inlästa källdata, med källfilernas hashar, kvalitet och omfattningsbeslut |
| **Simulering** | Ett namngivet arbetsobjekt: dataunderlag, omfattning och förutsättningsvärden |
| **Förutsättning** | Ett justerbart värde i en simulering, definierat av parameterkatalogen |
| **Körning** | Genomförd beräkning av en simulering med frusen specifikation |
| **Resultat** | Täckning, resursbehov, validering, begränsningar och kostnadsprofil för en körning |
| **Nuläge** | Referenskörning med samma omfattning, data och beräkningsförutsättningar men utan planeringsflexibilitet |

Termen *scenario* används inte som produktbegrepp.

### 11.2 Krav på arbetsflödet (UX)

Användaren ska utan kunskap om konfigurationsfiler, JSON, modellversioner, filsökvägar eller Python kunna:

- **UX-1** starta programmet lokalt på Windows utan separat installation av Python, Node.js, Docker eller databasserver;
- **UX-2** skapa en simulering med begripliga standardvärden;
- **UX-3** ändra verksamhetsförutsättningar, och se vilka värden som är verifierade, hämtade ur data, antaganden eller experiment;
- **UX-4** köra beräkningen, följa status och avbryta;
- **UX-5** undersöka resultat, antaganden och begränsningar, med resursbehov alltid jämfört mot Nuläge;
- **UX-6** ändra förutsättningar och köra igen utan att tidigare körningar förändras;
- **UX-7** jämföra körningar, där bara jämförbara körningar får jämföras och skillnaden i förutsättningar redovisas;
- **UX-8** namnge, organisera, kopiera och radera simuleringar; radering visar vad som tas bort.

### 11.3 Krav på parametrar och verifiering

- **P-1 Aktiv betyder verksam.** En parameter som visas som justerbar ska faktiskt påverka beräkningen eller en uttryckligen beskriven beräkning. Funktioner utan modellstöd visas inte som reglage.
- **P-2 En parameterkatalog.** Definitioner (enhet, gränser, hjälptext, standardvärde, grund) finns på ett ställe. Värden hör till simuleringen.
- **P-3 Härledd verifiering.** Verifieringsstatus för en regel härleds av dokumenterat underlag och oberoende kontroll av resultatet. Ingen användare kan göra en regel verifierad genom att ange värde eller etikett. Saknad data eller modellstöd är aldrig godkänt.
- **P-4 Grund.** Varje värde är *Verifierad*, *Hämtat ur data*, *Antagande* (med motivering) eller *Experiment*.
- **P-5 Reproducerbarhet.** En körning fryser alla förutsättningsvärden, katalogversion, dataunderlagets hash och motorversion.

### 11.4 Krav på Nuläge och jämförelse

- **N-1** Nuläge beräknas med samma kod, data, omfattning, efterfrågemått, lokalbestånd, bemanningsregler och kostnadsantaganden som simuleringen. Endast uttryckligt definierade flexibilitetsparametrar och efterfrågevariation får skilja.
- **N-2** Faktisk historik (till exempel bokade platser och lokaler utanför beståndet) redovisas som kontext, inte som baslinje.
- **N-3** Vid efterfrågevariation särskiljs efterfrågeeffekt från planeringseffekt.
- **N-4** Datumflyttar simuleras fritt inom användarens parametrar; avsaknad av studentöverlappsdata begränsar inte optimeringen. Resultatvyn har en diskret fotnot: "Simuleringen tar inte hänsyn till individuella studenters eventuella tentamenskrockar." Antaganden och begränsningar visas tydligt men får inte dominera analysen; verktyget undersöker möjligheter och godkänner inget färdigt schema.
- **N-6** Platsnivåer från optimeringen redovisas som optimistiska undre gränser under angivna restriktioner. Lokalrealisering mot känd lokalportfölj och bemanning redovisas som separata nivåer och förväxlas inte med platsmåttet.
- **N-7** Inga lokaler uppfinns. Historiskt samtidigt platsbehov skiljs från den kända lokalportföljen; saknad kapacitet är ett synligt datagap.
- **N-8** Grundmått för efterfrågan är registrerade tentander. Registrerade, bokade och närvarande platser blandas aldrig utan tydlig definition.
- **N-9** Populationen redovisas som inläst, beräkningsbar och kvarstående datagap. Oavgjorda aktiviteter exkluderas inte automatiskt ur potentialbedömningen.
- **N-11** Resultatsidan har högst en fotnotsrad, en hopfälld panel för förutsättningar och begränsningar samt en omfattningsrad med neutrala siffror. Upprepade varningstexter och bannrar används inte; måttens namn bär sin definition.
- **N-10** Resultatet redovisar påverkansmått (antal och andel flyttade tentor, flyttavstånd, flyttar till helg eller ändrad starttid, fördelning per institution och kurs) så att priset för flexibiliteten är synligt.
- **N-5** Kostnadsbelopp jämförs endast mellan körningar med samma kostnadsantaganden. Skillnad mot internhyra visas aldrig som besparing.

### 11.5 Avgränsning av första användbara leverans

Första leveransen ska möjliggöra experiment med: datum- och veckodagsflexibilitet inklusive flexibilitet per tentamenstyp, starttidsflexibilitet, efterfrågevariation och jämförelse av resursbehov (platser, lokaler, vaktbehov, tidsmått) mot Nuläge. Digital andel, externhyra, ersättningslokaler, maximal skrivtid och avancerad kostnadsoptimering ingår i målbilden men tillkommer först när motor och data stöder dem. Varje krav i denna specifikation redovisas i `docs/KRAVUPPFYLLNAD.md` som uppfyllt, delvis uppfyllt eller saknas, med bevisande test.

### 11.6 Krav på kodbasen

Kodbasen ska innehålla en domänmodell, en parameterkatalog, en körnings- och valideringskedja, ett API och ett användargränssnitt. Ersatt eller historisk implementation, parallella scenariomodeller och kompatibilitetslager ska inte finnas kvar. Testkod som behövs för att verifiera resultat får finnas som tester.
