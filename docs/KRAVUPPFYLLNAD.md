# Kravmatris (S0-utkast)

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
