# Dataanalys inför S0

**Underlag:** `data/processed/` (härlett ur originalfilerna i `C:\lokalt\tentalokaler\underlag`, som är oförändrade). Bokningar 2025-09-01 till 2026-08-29 (8 466 rader, 5 506 bokningsordrar), Ladok 1 525 aktiviteter (terminen 12 januari-31 mars 2026), 1 283 behovsposter. Analyserna är engångsberäkningar; de skapar inga produktionsmoduler. Siffrorna blir golden-master-värden i S1 (`requires_local_data`).

## 1. Population (B7/F4)

| Nivå | Aktiviteter | Registrerade | Andel | Not |
|---|---:|---:|---:|---|
| Inläst population (Ladok) | 1 525 | 53 076 | 100 % | |
| **Beräkningsbar, direkt** | 1 258 | 46 698 | 88,0 % | Ingår i huvudberäkningen |
| Delade tillfällen (flera aktiviteter per bokat tentamenstillfälle) | 170 | 5 038 | 9,5 % | 82 tillfällen. **Ingår inte i huvudberäkningen** (F4b). Redovisas separat |
| Ingen bokning hittad | 71 | 1 339 | 2,5 % | Datum och starttid finns i Ladok; längd och sal saknas |
| Saknat deltagarantal | 25 | - | - | Delmängd av de oavgjorda; ingen dubbelräkning |
| Ingen kandidatrelation | 1 | 1 | <0,1 % | |

Kontrollsummor: 1 258 + 170 + 71 + 25 + 1 = 1 525. 46 698 + 5 038 + 1 339 + 1 = 53 076. De 25 med saknat värde ingår i de 267 oavgjorda (267 = 170 + 71 + 25 + 1).

Av de 267 oavgjorda är 175 digitala tentamina i LIS (4 581 av 6 378 oavgjorda registrerade). Huvudpopulationen underrepresenterar därför digitala tentor.

**Resultatvyn** visar alltid raden: *Inläst 1 525 · Beräkningsbar 1 258 (88 % av registrerade) · Kvarstående 267*. Nuläget och optimerade körningar bygger på samma beräkningsbara population och samma efterfrågedefinition. En separat rad anger vad som saknas för hela verksamheten.

## 2. Delade tillfällen: summa eller största aktivitet (F4b)

82 bokade tillfällen har oavgjorda Ladokaktiviteter: 66 med två aktiviteter, 10 med tre till sex och 6 där bara en av tillfällets aktiviteter är oavgjord. Frågan är om deltagarna är samma personer (då gäller största aktiviteten) eller olika (då gäller summan). Jämfört med bokade platser per tillfälle:

| Grupp | Tillfällen | Summa av aktiviteterna | Största aktiviteten | Summa / bokat | Största / bokat |
|---|---:|---:|---:|---:|---:|
| Aktiviteter med **samma** kurskod | 71 | 4 588 | 3 347 | 1,05 | 0,77 |
| Aktiviteter med **olika** kurskoder | 7 | 551 | 185 | 1,01 | 0,34 |
| Referens: entydiga tentor (huvudpopulationen) | 1 258 | - | - | registrerade/bokat 0,73 (median 0,80) | - |

(Fyra tillfällen saknar uppgift om bokade platser och ingår inte i kvoterna.)

**Tolkning.** För olika kurskoder (samtenta för flera kurser) passar *summan* (annars blir bokade platser för få). För samma kurskod ligger *största aktiviteten* närmast referenskvoten (0,77 mot 0,73) och summan över den (1,05), men skillnaden är inte avgörande: fördelningen är bred (för entydiga tentor ligger kvoten mellan 0,57 och 0,91 för mittersta hälften). Det som kan skilja fallen åt är hur "ordinarie tentamen" och "digital tentamen (LIS)" i samma kurs registreras: som alternativa, överlappande anmälningar eller som skilda studentgrupper. Det kan bara verksamheten bekräfta.

**Beslut:** ingen av metoderna är säker. De delade tillfällena ingår inte i huvudberäkningen. De redovisas som separat omfattning med intervall: **3 583 platser (största aktivitet) till 5 203 (summa)**, motsvarande +7,7 % respektive +11,1 % av huvudpopulationens 46 698. Den uppdelning efter kurskod som visas ovan är bevarad som underlag för beslutet.

**Åtgärd i S1:** bokningsfälten `co_exam` och `co_exam_identical` kan bli en del av beslutsunderlaget. I de 82 tillfällena är samtenta=Ja för 35 av 148 bokningsrader; det är ingen entydig indikator.

## 3. Återanvändning av `canonical_demand` (F8)

Modulen är **ingen metod** för att avgöra deltagarantal; den är en **strukturvalidator**. `build_canonical_exam_demands` kräver att varje inkluderad aktivitet kopplas exakt en gång till en delgrupp, att en delgrupp äger ett deltagarantal med en angiven räknegrund (`count_basis`) och att ett tentamensbehov får sitt antal som summan av sina delgrupper. Därmed är dubbelräkning strukturellt omöjlig när relationerna är rätt uttryckta.

| Aspekt | Bedömning |
|---|---|
| Fungerar för delade tillfällen? | Ja, som struktur: tillfället blir ett `exam_demand`; aktiviteter som antas vara samma grupp pekar på *en* delgrupp (antal = största aktivitet, `count_basis = assumed_same_group_max`); aktiviteter som antas vara skilda grupper får en delgrupp vardera (`count_basis = distinct_group_sum`) |
| Används i produkten idag? | Nej. Bara scope-delen (`provisional_scope_decisions`, `build_scope_report`) körs via pipeline. Builder-funktionen används bara av tester |
| Rekommendation | **Återanvänd som enda väg för att bilda tentamensbehov**, alltså även för huvudpopulationen (där varje tillfälle har en aktivitet och en delgrupp). `count_basis` blir en synlig egenskap i Dataunderlaget. Det ger en gemensam, testad struktur för både huvud- och delad omfattning, och det är först då koden inte bara finns kvar av historiska skäl. Radera annars `build_canonical_exam_demands` och dess test |
| Ändringar i modulen | Indata byggs ur `activity_booking_candidates` och `exam_events`; `demand_definitions` fylls med ort, längd och lokalkrav ur bokningarna. Funktionen ska inte själv välja `count_basis`; regeln för det ligger i Dataunderlagets bygge och är ett beslut |

## 4. Hemtentor och duggor (F6)

| Examinationsform | Behov i huvudpopulationen | Platser | Lokal används? |
|---|---:|---:|---|
| Ordinarie tenta | 721 | - | Ja, utom 1 tillfälle som bara har hemma-placering |
| Omtenta | 497 | - | Ja |
| Hybridtenta | 16 | - | Ja (alla 23 bokningsrader har lokal) |
| **Dugga** | 22 | 1 432 | **Ja**: alla 39 bokningsrader har lokal (bland annat Bergsbrunnagatan, Fyrislundsgatan, Klostergatan) |
| **Hemtenta** | 2 | - | **Nej**: 26 av 27 bokningsrader är "hemma" |

Tre behov (94 platser, 0,2 %) har bara hemma-placeringar: två hemtentor och en ordinarie tenta. Examinationsformen är därför inte en tillförlitlig regel; **regeln blir: ett behov belastar lokaler bara om minst en av dess placeringar har en identifierad lokal eller adress** (härlett ur bokningen, inte ur typfältet). De tre hemma-behoven tas ur lokalbehovet och redovisas som "ingen lokal används". Duggor ingår, eftersom de har lokalbokningar.

## 5. Institution som granskningsdimension (F12)

Fältet `org_code` finns på alla 5 506 bokningsordrar och ingen order har fler än en kod. I huvudpopulationen finns 48 koder; endast 4 av 902 kurskoder har tentor under mer än en kod.

| Villkor | Resultat |
|---|---|
| Koppling tillförlitlig? | **Ja på ordernivå**: varje tentamenstillfälle har exakt en kod. Kopplingen Ladokaktivitet → tillfälle är entydig för huvudpopulationen |
| Institutionsnamn | **Saknas** i underlaget (bara numeriska koder, till exempel 106, 104, 113, 261) |
| Konsekvens | Granskning per institution kan göras med koden som etikett. Visning med namn kräver en kod-till-namn-tabell från verksamheten (ny uppgift) |

## 6. Avvikelser mellan publicerad kapacitet och historiska bokningar (F2b)

Publicerad kapacitet används som preliminärt tak. Bokningarna under terminsfönstret (12 januari-31 mars 2026, ej avbokade) jämförs enskilt med det taket:

| Sal | Publicerad | Bokningar | Över taket | Andel | Största bokning | Andel av platserna som ligger över taket |
|---|---:|---:|---:|---:|---:|---:|
| Bergsbrunnagatan 15 sal 1 | 206 | 310 | 3 | 1,0 % | 254 | 5,7 % |
| Bergsbrunnagatan 15 sal 2 | 229 | 356 | 11 | 3,1 % | 274 | 16,1 % |
| Fyrislundsgatan 80 sal 1 | 200 | 209 | 0 | 0 % | 200 | 0 % |
| Råbyvägen 95 sal 1 | 96 | 98 | 4 | 4,1 % | 106 | 14,2 % |
| Råbyvägen 95 sal 2 | 128 | 99 | 2 | 2,0 % | 130 | 5,7 % |
| Råbyvägen 95 sal 3 | 180 | 187 | 3 | 1,6 % | 210 | 6,4 % |
| **Summa** | | **1 259** | **23** | **1,8 %** | | |

Avvikelsen är liten under terminen (23 av 1 259 bokningar) men finns och är systematisk i vissa salar. Hela året är avvikelserna större (till exempel 280 mot 229). Historiskt bokat antal behandlas inte som verifierad fysisk kapacitet. Avvikelserna redovisas i Dataunderlagets kvalitetsvy ("Bokningar över publicerad kapacitet: 23 av 1 259") och kan inte användas för att höja taket utan beslut.

**Nuläge, efterfrågan och lokalrealisering.** Nuläget skiljer tre saker:
- *Historisk efterfrågan* (modellerad, registrerade tentander): 1 604 samtidiga platser som mest.
- *Känd lokalportfölj* (preliminärt tak, publicerad kapacitet): 1 179 platser i åtta salar. Fyra dagar har efterfrågan över detta.
- *Faktisk lokalrealisering* (vad som bokades): 68,3 % av bokade platser i de åtta salarna; resten i Danmarksgatan 30, Fyrishov hall D/E/F, Klostergatan 3 (specialtentamenscentret), hemma och ofullständiga adresser. De lokaler som saknar kapacitet i registret är identifierade av bokningarna men har ingen kapacitetsuppgift.

**Lokaler som saknas i registret enligt bokningarna** (terminsfönstret): Danmarksgatan 30 (7,3 % av bokade platser; största bokning 344), Fyrishov hall D, E, F (2,9 %, 2,7 %, 2,8 %; största bokning 300, 330, 260; största samtidiga bokning på en hall 330), Fyrislundsgatan 80 utan rumsangivelse (0,8 %). Dessa utgör ett synligt datagap: kapacitet och tillgänglighet behöver fastställas av verksamheten. Observerad största bokning anges som **kontext** per lokal ("observerad bokning"), inte som kapacitet.

## 7. Konsekvenser för planen

| Fynd | Förändring i planen |
|---|---|
| Delade tillfällen osäkra | Utanför huvudberäkningen; redovisas som intervall; `canonical_demand` används som strukturen när beslut finns |
| Hemtentor | Regeln "belastar lokal" ur bokningen; 3 behov (94 platser) tas ur lokalbehov |
| Duggor | Ingår; ingen särskild hantering |
| Institution | Etikett = kod; visa namn när tabell finns |
| Kapacitet | Publicerad som tak; avvikelser redovisade; observerad kapacitet **inte** ett lokalalternativ som standard |
| Lokaler utan kapacitet | Datagap; ingen portfölj "P2" med observerad minimikapacitet i första leveransen. Användaren kan lägga till en lokal med egen kapacitet (grund Antagande) |
