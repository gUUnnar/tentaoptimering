# Kravmatris (S0-utkast)

> Den äldre kapacitets- och termmotorn är borttagen (finns i Git-historiken före den här grenen). Hänvisningar nedan till dess moduler, scenarier, kommandon och rutter beskriver därför det tidigare läget.

Varje krav i `KONCEPTUELL_KRAVSPECIFIKATION.md` och i acceptanskriterierna (`AGENTS.md`) redovisas med dagens status, status efter första leveransen och det som bevisar den. Statusord: **Uppfyllt**, **Delvis**, **Saknas**, **Kan inte verifieras** (data saknas). Matrisen uppdateras vid varje steg; ett krav får inte markeras *Uppfyllt* utan ett test eller en kontroll.

Underlag klassas **A** (finns i tillgängliga data), **B** (kräver antagande), **C** (kräver nya verksamhetsuppgifter).

## 1. Planeringskrav

| Krav | Idag | Efter första leveransen | Bevis | Underlag |
|---|---|---|---|---|
| Fullständig efterfrågetäckning inom vald omfattning (AC1) | Delvis: täckning rapporteras mot 1 258 inkluderade; kapacitet i kända lokaler är ej prövad mot historiken | **Uppfyllt för beräkningsbar population**; brist i lokaler redovisas som datagap | Täckningsregel i valideraren; golden master 1 258 | A |
| Täckning av hela verksamheten | Saknas (267 oavgjorda) | **Saknas** (redovisas separat som kvarstående) | Befolkningspanelen | C |
| Terminsövergripande planering över kalenderperioder (AC2) | Delvis: fast pass 08-18, ingen koppling till historiskt datum | **Uppfyllt för datum, veckodagar, spärrade perioder, starttider, tentamenstyp** | Effektfall per parameter; golden master | A/B |
| Ursprungligt schema bevaras när förändring saknar nytta (AC2) | Saknas | **Uppfyllt** (andra målnivå: minimera antal flyttar; tolerans) | Test: tolerans > 0 ger ≤ flyttar | A |
| Gemensam totalkostnad: datum, salar, bemanning optimeras tillsammans (AC3) | Delvis: kostnadsproxyer, giriga steg | **Delvis**: datum optimeras mot platstopp; salar och bemanning räknas efteråt. Ingen gemensam kostnadsoptimering | Resultatmodellens nivåindelning | C |
| Personalstyrkans storlek som kostnadsvariabel (AC3) | Delvis (poolstorlek) | **Delvis**: vaktbehov redovisas; kostnadsstruktur saknas | Steg C | C |
| Bomtid, restid och betald tid som kostnad | Delvis: redovisas, prissätts inte | **Delvis**: redovisas separat utan dubbelräkning; betalt pass ≥ 2 h modelleras | Test för betald tid | C |
| Hårda villkor: fysisk kapacitet | Delvis | **Uppfyllt mot publicerad kapacitet** (preliminärt tak) | `room_capacity` | A/B |
| Hårda villkor: digital kompatibilitet | Saknas | **Saknas** | - | C |
| Hårda villkor: Uppsala och Visby skilda | Uppfyllt (ort), Visby saknar efterfrågan | **Uppfyllt**; Visby utan data | `plan_area` | A |
| Hårda villkor: kurs- och programkrockar | Delvis: kurs, ej program | **Delvis**: kurs (överlapp och ordning). Studentkrockar: fotnot | Kursregel, ordning | C |
| Lagar, avtal, arbetstid | Delvis: antagna värden | **Delvis**: rast vid pass > 5 h och kortaste betalda pass 2 h är Verifierade; övrigt Antagande | `ANALYS_KOLLEKTIVAVTAL.md` | B/C |
| Spårbara data och antaganden; ersättbara (AC5) | Delvis: fyra parallella register | **Uppfyllt**: en katalog, grund per värde, frusen specifikation | Katalogtest | A |
| Skilj faktisk kostnad, teoretisk potential, verifierad besparing (AC5) | Delvis | **Uppfyllt**: tre nivåer; två senare "kan inte beräknas" | Kostnadsspärr-test | C |

## 2. Efterfrågan, lokaler, personal

| Krav | Idag | Efter första leveransen | Bevis | Underlag |
|---|---|---|---|---|
| Efterfrågemått dokumenterat; registrerade, bokade, närvarande skilda | Delvis | **Uppfyllt**: registrerade; bokade som kontext | Definition i Dataunderlaget | A |
| `demand_variation_pct` med explicit avrundning | Saknas | **Uppfyllt** | Effektfall | A/B |
| `digital_exam_share_pct` | Saknas | **Saknas** | - | C |
| `max_exam_duration_hours` | Saknas | **Saknas** | - | C |
| Lokaldata: stabilt id, ort, kapacitet, teknik, kostnad | Delvis | **Delvis**: id, ort, kapacitet; teknik och avtal saknas; lokaler utan kapacitet som datagap | Dataunderlagets kvalitetsvy | C |
| Långtids- och korttidsdisponerade lokaler, ersättningslokaler, externhyra | Saknas | **Saknas** | - | C |
| Anonymiserade vakter med arbetstid, kompetens, tillgänglighet | Delvis (anonym pool) | **Delvis**: anonym plan med raster, vila, restid; ingen kompetens eller tillgänglighet | `staffing_validation` | B/C |
| Bemanning efter antal samtidigt skrivande per sal | Delvis: trappa efter deltagare | **Delvis**: trappa efter deltagare (Antagande) | `test_staffing` | C |
| Vakter över flera salar och byggnader samma dag | Uppfyllt (modellerat) | **Uppfyllt** | `test_staffing` | B |

## 3. Resultat och kvalitet

| Krav | Idag | Efter första leveransen | Bevis |
|---|---|---|---|
| Körningen dokumenterar konfiguration, dataversion, antaganden, omfattning, solverstatus, tid, gap | Delvis (gap saknas) | **Uppfyllt** | Frusen specifikation, gap från CP-SAT |
| Efterfrågetäckning och bevisad täckning | Delvis | **Uppfyllt** | Valideringsregel |
| Schema och ändringar mot ursprungligt datum, pass, lokal | Saknas | **Uppfyllt för datum och starttid; lokal: realisering mot portfölj** | Flyttlista |
| Belastning, lokalportfölj, korttidsinhyrning, digitala platser | Delvis | **Delvis**: belastning, portfölj; inhyrning och digitala platser saknas | Resultatmodell |
| Personalvolym, arbetstid, bomtid, förflyttningar | Delvis | **Uppfyllt** (redovisas) | Resultatmodell |
| Kostnad per kategori, total årskostnad, potential mot baslinje | Saknas | **Delvis**: modellkostnad enligt antaganden; potential och besparing "kan inte beräknas" | Kostnadsnivåtest |
| Reproducerbarhet | Delvis | **Uppfyllt**: frusen specifikation + frö | Test: identiskt resultat |
| Oberoende eftervalidering | Delvis (fritextkrock) | **Uppfyllt**: härledd status, ingen fritext | Regressionstest G4 |

## 4. Användargränssnitt och experiment (kravspecifikationen §11)

| Krav | Idag | Efter första leveransen | Bevis |
|---|---|---|---|
| UX-1 Start lokalt på Windows utan Python/Node/Docker/databasserver | Delvis (paketering finns) | **Uppfyllt** | Ren-installationstest (R11) |
| UX-2 Skapa simulering med standardvärden | Saknas | **Uppfyllt** | Playwright steg 1 |
| UX-3 Ändra förutsättningar, se grund | Saknas | **Uppfyllt** | Playwright steg 2-3 |
| UX-4 Köra, följa status, avbryta | Delvis (ingen avbrytning) | **Uppfyllt** | Playwright steg 4 |
| UX-5 Resultat, antaganden, begränsningar, jämfört mot Nuläge | Saknas | **Uppfyllt** | Playwright steg 5 |
| UX-6 Ändra och köra igen utan att äldre körningar ändras | Delvis | **Uppfyllt** | Test: frusen specifikation |
| UX-7 Jämföra körningar, bara jämförbara | Delvis | **Uppfyllt** | Jämbarhetsnyckel-test |
| UX-8 Namnge, organisera, kopiera, radera | Saknas | **Uppfyllt** | Playwright steg 8 |
| P-1 Aktiv betyder verksam | Saknas | **Uppfyllt** | Katalogtest |
| P-3 Härledd verifiering | Saknas | **Uppfyllt** | Regressionstest |
| N-1 till N-10 (Nuläge, population, lokaler, fotnot, påverkansmått) | Saknas | **Uppfyllt** (N-7: brist som datagap) | Se plan |

### Aktuell status efter PR #11 (gemensam motor och nytt gränssnitt)

Tabellen ovan är S0-planen. Efter att den äldre motorn togs bort gäller detta för den gemensamma motorn och det nya gränssnittet. Det som inte är uppfyllt står som sådant.

| Krav | Status | Kommentar |
|---|---|---|
| N-1 Nuläge med samma kod och data | **Ej uppfyllt** | Det finns ingen definierad nulägesberäkning. Gränssnittet jämför mot föregående körning av samma scenario, vilket är användbart för experiment men inte samma sak. |
| N-3 Efterfrågeeffekt skild från planeringseffekt | **Ej uppfyllt** | När efterfrågan ändras redovisas ingen kostnadsskillnad alls, eftersom den inte går att tillskriva schemaläggningen. En uppdelning saknas. |
| N-5 Kostnadsbelopp bara mellan körningar med samma antaganden | **Uppfyllt för jämförelsen** | Vid ändrade kostnads- eller efterfrågeparametrar visas ingen kostnadsskillnad, och texten säger att det beror på antagandena (`tests/test_joint_review_fixes.py`). |
| UX-1 Start lokalt på Windows utan Python/Node | **Ej verifierat** | Paketeringen är inte provad efter ombyggnaden, och mappväljaren för källdatakatalog (PR #5) ingår inte. |
| UX-5 Resultat med antaganden och jämförelse mot Nuläge | **Delvis** | Resultat, domar, ändrade parametrar och begränsningar visas. Jämförelse mot Nuläge saknas (se N-1). |
| UX-7 Jämföra bara jämförbara körningar | **Delvis** | Körningar jämförs bara vid samma underlag, samma tentor, verifierad lösning, och kostnad bara vid samma antaganden. En fullständig jämbarhetsnyckel finns inte. |
| UX-8 Namnge, organisera, kopiera, radera | **Delvis** | Egna scenarier kan sparas. Radering och organisering saknas. |

## 5. Datagap som begränsar bedömningen (nya uppgifter, klass C)

| Uppgift | Påverkar |
|---|---|
| Kapacitet och tillgänglighet för Danmarksgatan 30 och Fyrishov hall D-F; verifierade salskapaciteter | Realisering av Nuläge och simuleringar |
| Student- eller programöverlapp | Trovärdighet för datumflyttar |
| Beslut om delade tillfällen (summa eller största aktivitet) | 82 tillfällen, 3 583-5 203 platser |
| Bemanningsregler per sal och deltagarantal; centralt Villkorsavtal-T 4 kap. 5 §; avtal om obekväm arbetstid; anställningsform per vakt; lönenivåer | Personalbehov och kostnad |
| Kod-till-namn för institutioner | Granskning per institution med namn |
| Tentamensperioder och omtentaintervall | Realistiska standardfönster |
| Digital kompatibilitet per sal | Digital andel |
| Underlag för fler terminer och Visby | Årsvärden; ortsbedömning |

## Komplettering: verksamhetspresentation 2026-10-02 (ej kravuppfyllelse)

Det har tillkommit en [sammanställning av redovisade verksamhetsuppgifter](VERKSAMHETSUNDERLAG_2026-10-02.md): 1 109 ordinarie salplatser + 41 RPS, bemanningstrappa med minst två vakter/pass, förslag att pröva tre skrivpass per sal och dag, toppar till juni samt preliminära överbeställnings- och personalkostnader. **Uppgifterna är inte verifierade verksamhetsbeslut** och ändrar därför inte status *Uppfyllt* i matrisen.

Inför leverans ska minst följande bedömas med explicita verifieringsprov: (a) valbar planeringsperiod (nuvarande `joint_underlay_period` är korrekt avgränsad till 12 januari–31 mars men perioden ska bli användarstyrd inom dataunderlaget), (b) verifierad kapacitet och sal-ID, (c) bemanningstrappa med entydiga intervall, (d) tidspass och längder vid försök med tre pass/dag, (e) jämförbara kostnadsantaganden och faktisk undvikbarhet (kraven N-1/N-5). Markera respektive krav som delvis eller saknas tills bevis finns.


## Nya uttryckliga krav 2026-10-12: periodval, läsvyer och export

Den tidigare formuleringen att **minsta planeringsperiod är en termin** har ersatts av **valfri vald period inom tillgängligt dataunderlag**. Detta är ett bindande ändrat krav, inte en tolkning av presentationen. Förväntad dataleverans: 1 januari–30 september inklusive verklig beläggning. Det faktiska året och måttens definition fastställs vid import.

| Krav | Status inför implementation | Kontroll innan uppfyllt |
| --- | --- | --- |
| UX-9 Val av planeringsperiod inom dokumenterad datatäckning | **Genomförd i PR #13 (ej mergad)**: datumval och genvägar i gränssnittet, täckning per källa, kontroll mot underlaget, godkännande av delvis täckt period, mätning dag/vecka/månad. Saknas på den här grenen. | Kvarstår: verifiera efter merge, och data 1 januari–30 september när den levererats. |
| UX-10 Lokalens nyttjande per vald tidsperiod | **Delvis**: sidan Lokaler har vyn En lokal och vyn Dag eller period per adress. Där väljs dag eller period (och adress) och bokningar visas per adress och sal med tentamina (en gång vardera), bokade platser och bokad tid med definition. Bokningar som bara anger adress (41 % av raderna) ligger kvar under sin adress som "sal ej angiven" och hänförs inte till någon sal. **Verklig beläggning saknas i underlaget och visas som okänd, aldrig som noll.** Ingen optimering krävs. | Kvarstår: verklig beläggning när data finns, dokumenterad tillgänglig tid som nämnare, kapacitet per adress. |
| UX-11 Historiskt schema för en viss bokad tentamen | **Delvis**: sök på id, kurskod eller kursnamn, eller öppna en tentamen ur tidslinjen, tabellen eller periodöversikten och se alla salar, tider och bokade platser. **Jämförelse mot vald körning finns**: ursprunglig och simulerad tid samt adress och sal, via den provisoriska Ladok-kopplingen (tvetydig eller saknad koppling redovisas, inget gissas). | Kvarstår: observerat utfall, sökning på datum i tentamenssökningen, jämförelse på salnivå när bokningen saknar salnamn. |
| Data: verklig beläggning med egen proveniens och tidsstämpel | **Inväntar ny data** | Säker uppslagsnyckel, definition per mått, täckning, test att frånvaro av data inte blir noll. |
| Framtida systemkompatibel export | **Utanför PoC** | Dokumentera importformat för senare leverans; eventuell enkel fil inom PoC ska beskrivas som preliminär, inte direkt importerbar. |

Skilj ett datumval för att **studera historiska bokningar** från en **planeringskörning**; de ska kunna använda samma tidsfilter utan krav på att användaren först optimerar. Nuläge och simulering måste dela planeringsperiod, data och antaganden för att kunna jämföras.


### Snabb iteration med små perioder (ej verifierad, 2026-10-12)

**Status: saknas i UX, delvis stöd i motorn.** Backendens `joint_selection.select_ready_demands` kan välja korta intervall med `date_from`/`date_to`, men de är ännu bundna till scenariofilen: ingen enkel datumväljare finns i körgränssnittet. Ett litet reproducerbart testfall går att köra i dag via befintligt namngivet delurval eller manuellt skapad scenariofil; det uppfyller inte kravet att kunna snabbt växla period från UX.

Acceptanskriterier: dags- och veckourval direkt i UX utan TOML, redovisat antal tentor/oklarheter, verifierad fullständig placering, sparad specifikation och mätning av både tid till första verifierade lösning och total tid. Testa att redan lagda salbokningar utanför den valda optimeringspopulationen inte felaktigt betraktas som ledig resurs. Den korta perioden ska vara ett verkligt användningsfall för **kortvarselplanering** och för **snabba funktions-/regressionstester**.
