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

CLI och maskinläsbara resultat är tillräckliga för PoC:n. Utvärdera modellen först med små syntetiska fall med kända svar och därefter med en hel termins historiska data.

## 10. Öppna databehov

För att minska osäkerheten behöver projektet verifierade uppgifter om faktisk närvaro, kurs–programkopplingar, salarnas teknik och kapacitet, externa hyrperioder och priser, alternativa lokalers hyresnivåer, personal- och transportkostnader samt detaljerade bemannings-/arbetstidsregler. Lösningen ska kunna omvärderas utan programombyggnad när dessa uppgifter blir tillgängliga.
