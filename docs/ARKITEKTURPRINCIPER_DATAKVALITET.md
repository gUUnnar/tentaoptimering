# Arkitekturprinciper: verksamhetsmodell och datakvalitet hålls isär

Status: principiella fynd och förslag. **Ingen kod är ändrad av detta dokument.** Det är skrivet före större ändringar och granskar PR #13 (periodval), #14 (lokalvy) och #15 (översikt och jämförelse) mot principerna nedan. Beslut om vilka förslag som genomförs ligger hos beställaren.

Syftet med PoC:n är att undersöka den potentiellt optimala tentamensverksamheten under justerbara verksamhetskrav. Det är inte att återskapa begränsningarna i dagens administrativa rutiner eller datauttag.

## 1. Principer

1. **Verksamhetsmodell och datakvalitet separeras.** Modellen ska fungera med fullständiga, korrekta och detaljerade data, även när dagens underlag är bristfälligt. Databrister hör hemma i datainläsning och undantagshantering, inte i modellens grundantaganden.
2. **Saknade uppgifter hanteras explicit.** Okänd sal, ännu inte tilldelad sal, bokning som avsiktligt avser en hel adress, lokal som inte är en fysisk sal och faktiskt felaktig eller ofullständig data är olika fall och får inte ges samma tolkning.
3. **Bättre data förbättrar precisionen utan ombyggnad.** Ett bokningsuttag där varje bokning har korrekt sal ska utnyttjas automatiskt.
4. **Inga tysta antaganden.** Okänd sal är varken ledig eller (automatiskt) alla salar på adressen upptagna.
5. **Tydlig undantagspolicy.** Explorativa körningar får acceptera osäkra data med tydlig redovisning. Verksamhetsmässigt tillförlitlig planering kräver att vissa databrister först åtgärdats.
6. **Testa med olika dataförutsättningar.** Fullständigt salsatta bokningar, bokningar på adressnivå och blandade eller bristfälliga underlag ska alla fungera i grundmodellen.

## 2. Vad "saknad sal" faktiskt är i dagens uttag

Mätt på `data/processed/bookings.csv` (8 466 rader, varav 364 avbokade; 8 102 aktiva). De 41 procent som nämnts är 3 461 rader utan salnamn **inklusive** avbokade; bland aktiva rader är det 3 097 (38,2 procent).

| Adress | Aktiva rader | Utan salnamn | Andel |
|---|---|---|---|
| Bergsbrunnagatan 15 | 2 532 | 5 | 0,2 % |
| Klostergatan 3 | 2 267 | 2 267 | 100 % |
| Råbyvägen 95 | 1 610 | 0 | 0 % |
| Fyrislundsgatan 80 | 1 141 | 566 | 49,6 % |
| Danmarksgatan 30 | 237 | 237 | 100 % |
| Fyrishov | 178 | 0 | 0 % |
| Hemma | 124 | 9 | 7,3 % |
| "Ordinarie sal utan anpassningar" | 13 | 13 | 100 % |

Det är fyra olika mönster, inte ett:

- **Systematiskt per adress (Klostergatan 3, Danmarksgatan 30).** Salnamn anges aldrig. På Klostergatan 3 är medianen två bokade platser och 95 procent av de tentamina som har rader där har även en namngiven sal någon annanstans. Det *kan* vara en bokningskonvention för anpassade eller små platser, men uppgiften finns inte i underlaget. Det är en hypotes som verksamhetsägaren behöver bekräfta, inte något som modellen ska anta.
- **Blandat inom en adress (Fyrislundsgatan 80, hälften).** Här finns både namngivna salar och rader utan sal. Det talar för att saknaden delvis är en registreringslucka, eller att två olika fall blandas.
- **Sällsynt avvikelse (Bergsbrunnagatan 15, fem rader).** Troligen en vanlig registreringslucka, alltså felaktig eller ofullständig data.
- **Värden som inte är det de ser ut att vara.** "Hemma" är en adress men inte en fysisk lokal, och "Hemtenta" står som sal. "Ordinarie sal utan anpassningar" står i adressfältet men är en beskrivning, inte en adress.

Dessutom två andra datatillstånd som lätt blandas ihop med bristande bokningsdata:

- **Täckning, inte kvalitet.** Ladok-underlaget börjar 12 januari 2026 och slutar 31 mars 2026. Av bokningar utanför det fönstret saknar 5 596 av 5 659 kandidatkoppling. Det beror på att Ladok inte täcker perioden, inte på att kopplingen misslyckats. Inom fönstret saknar 496 rader kandidat och 123 är tvetydiga.
- **Datat har redan två nivåer.** I salsregistret finns `eligible_for_exploratory_capacity_poc` och `eligible_for_operational_scheduling`. Alla åtta salar i optimeringsunderlaget är utforskande och ingen är operativt godkänd. Det är principen om explorativ respektive tillförlitlig planering i redan existerande data, och den innebär att tillförlitlig planering i dag inte är möjlig för någon sal.

## 3. Granskning av PR #13–15

### Vad som håller

- Motorn och dess indata (`joint_inputs`, `joint_optimizer`) innehåller **ingen** anpassning till bokningsluckor: bokningar används inte alls i optimeringen. PR #13 ändrar inte det.
- Periodens täckning i `joint_period.py` läses ur efterfrågedatat (första och sista datum, klara och ej klara tentor), inte från fasta datum. Nytt underlag med annan period fungerar utan kodändring.
- Delvis täckta perioder kräver ett uttryckligt godkännande. Det är undantagspolicy, inte en dataanpassning.
- Parametern `digital.partial_support_policy` är ett bra mönster: en uttrycklig, versionsspårad policy för osäkra data i stället för ett inbyggt antagande.
- Verklig närvaro visas som okänd, aldrig som noll, och kapacitet används bara för namngiven sal. Det är i linje med princip 4.

### Fynd: för hårt anpassat till dagens dataluckor

| # | Var | Fynd | Princip |
|---|---|---|---|
| F1 | PR #14/#15: `booking_views.load_bookings`, `booking_overview.place_label`, gränssnittets "sal ej angiven" | **Alla** rader utan salnamn får samma tolkning och samma etikett, oavsett om det är en adresskonvention, en registreringslucka, en icke-fysisk lokal eller ett felaktigt fält. Räkningar och summor är riktiga, men begreppet "sal ej angiven" döljer de fyra mönstren i avsnitt 2. | 2 |
| F2 | PR #14/#15: `ladok_link`, `LINK_TEXT`, `linkIsUnclear` | `no_candidate` blandar "utanför Ladok-täckningen" (5 596 rader) med "ingen koppling trots täckning" (496). Täckningsfönstret härleds inte ur data utan syns bara indirekt. | 2, 3 |
| F3 | PR #14/#15: `booking_views`, kapacitet | "Namngiven sal" är reglerna för när kapacitet gäller. Matchning mot registret saknar eget tillstånd: en sal som är namngiven men saknar kapacitet i registret (t.ex. Fyrishov D–F) får bara `capacity = null`; att den inte kunnat matchas och att kapaciteten saknas är samma tillstånd. Högsta samtidiga bokning över kapacitet (t.ex. 105 %) visas utan att markeras som misstänkt data. | 2 |
| F4 | PR #15: `booking_compare._room_names`, jämförelse | Jämförelsen jämför salar bara om *alla* bokade lokaler har namn. Det är rätt, men skälet ("saknar salnamn") är ett enda skäl för olika orsaker. | 2 |
| F5 | PR #14: `load_bookings` | Länkstatus per bokningsrad tas från första raden i `candidate_linkage` när flera finns. Det är i dag samma status på alla rader, men regeln är implicit. | 4 |
| F6 | PR #13: `PLANNING_BASIS` | `mode = "exploratory"` och `fixed_bookings_considered = false` är konstanter. Det är sant i dag, men "explorativ" är en egenskap hos körningen som borde **härledas** av datatillstånd och vald policy, så att tillförlitlig planering kan uppstå utan kodändring. | 3, 5 |
| F7 | PR #13: `docs/PERIODVAL_OCH_SNABBA_KORNINGAR.md` avsnitt 3 | **Det allvarligaste fyndet.** Designen för att beakta redan lagda bokningar föreslår "kapacitetsreduktion per adress och pass" som den modell som gäller när sal saknas. Det gör en datalucka till ett modellantagande. Den designen bör ersättas av avsnitt 4 nedan. | 1, 2, 4 |
| F8 | Motorn (befintlig, inte PR #13–15) | `rooms` väljs med `eligible_for_exploratory_capacity_poc`. Valet är hårdkodat. Nivån bör vara en uttrycklig policy (`explorativ` eller `operativ`) så att tillförlitlig planering blir möjlig när data godkänner salar operativt. | 5 |

## 4. Föreslagen arkitektur

Tre lager med tydliga gränser.

### 4.1 Datakvalitetslager (inläsning)

**Uppdaterad efter genomförande (se avsnitt 9).** Den första skissen i det här avsnittet förde samman allt i ett uteslutande resurstillstånd. Det är ersatt av **fyra oberoende dimensioner**: en bokningsrad har ett värde på var och en, och dimensionerna blandas inte.

| Dimension | Frågan | Värden |
|---|---|---|
| **Resursidentifiering** | Vad identifierar datat? (Inte varför något saknas.) | `room_matched`, `room_named_not_in_register`, `address_only`, `no_address`, `declared_non_physical` |
| **Datakvalitet** | Vilka fynd finns på raden? (Flera kan gälla samtidigt.) | Lista av flaggor: `room_missing`, `room_not_in_register`, `capacity_missing_in_register`, `places_exceed_capacity`, `places_missing_or_zero`, `date_missing`, `time_unparseable`, `status_unclassified`, `address_field_not_an_address` |
| **Källtäckning** | Ligger bokningen inom den period en annan källa täcker? | `ladok_coverage`: `within`, `outside`, `unknown`. Fönstret härleds ur källans datum (eller sätts uttryckligen i konfigurationen). |
| **Kopplingssäkerhet** | Hur säker är kopplingen bokning till Ladok-aktivitet? | `unique`, `ambiguous`, `none_within_coverage`, `none_outside_coverage`, `none_coverage_unknown`, `not_assessed` |

Därtill bokningsstatus som klass (`cancelled`, `active`, `unclassified`) enligt konfigurationen.

Några konsekvenser:

- "Sal saknas" är ett **fynd** (`room_missing`) på en rad som identifieras till en adress (`address_only`). Det säger inte *varför* sal saknas. Fyra möjliga orsaker (adresskonvention, ännu ej tilldelad, icke-fysisk lokal, felaktig data) skiljs inte åt i datat och får inte skiljas åt av lagret. De kan bara skiljas åt av en uppgift från dataägaren, som läggs in som en **verifierad regel**.
- En deklaration att en adress avser adressnivå (`address_level_rule`) ändrar inte vad datat identifierar. Den sätter en separat egenskap (`declared_address_level`) som senare steg får läsa.
- En bokning kan vara `address_only`, `outside` Ladok-täckning, ha `ambiguous` koppling och oklassad status samtidigt. Det är oberoende fakta.
- "Under behandling" och "Andring begard" har ingen regel och är `unclassified`. De antas inte betyda att sal tilldelas senare.

Reglerna ligger i `config/booking_data_quality.toml`. **Varje regel har `verified` och `source`; en overifierad regel klassificerar ingenting** och ger bara en kandidatnotering. Ett nytt uttag med korrekta salar får `room_matched` utan kodändring, och nya verifierade uppgifter eller andra kolumnnamn läggs till i konfigurationen.

### 4.2 Domänmodell (oberoende av datakvalitet)

En bokning är en **reservation** av en resurs i en tidsrymd:

`Reservation { resurs: {typ: rum | adress | ingen, id}, tid, platser, tillstånd, källa }`.

Modellen och dess regler talar om reservationer och resurstyper, inte om "bokningsrader utan sal". En fullständig uppsättning blir reservationer av typ `rum`. En adressreservation är en riktig modelleringsmöjlighet (hela adressen eller en pool av platser) som aktiveras av `address_level_declared`, inte av att data saknas.

### 4.3 Policylager (undantagshantering)

> Utkast för ett senare steg. Tabellen använder resurstillstånd som förkortning för kombinationer av de fyra dimensionerna ovan. Inget i den är genomfört, och klassificeringen styr ingenting förrän policyn är beslutad.

För varje tillstånd anges hur det behandlas, **per planeringsläge**. Policyn är en parameter i katalogen (`bookings.state_policy.*`) som övriga parametrar, med grund och spårbarhet.

| Tillstånd | Explorativt läge | Tillförlitligt läge |
|---|---|---|
| `room_known` | Spärrar salen | Spärrar salen |
| `address_level_declared` | Reducerar adressens platser enligt deklarationen | Samma |
| `room_pending` | Behandlas som efterfrågan att placera, inte som spärr | Samma |
| `not_physical` | Ingen spärr | Ingen spärr |
| `room_unknown` | Ingen spärr. Redovisas: antal, platser och tid. **Ger två gränser** (optimistisk: ingen spärr, försiktig: alla salar på adressen upptagna under tiden) i stället för ett antagande | Nekas över en konfigurerad tröskel, annars som explorativt men märkt |
| `room_named_unregistered` | Spärrar, kapacitet okänd, redovisas | Nekas tills salen finns i registret |
| `invalid` | Utesluts och räknas | Nekas över tröskel |

Resultatet bär sitt läge och sina skäl: `planning_basis` blir **härlett** (läge, antal rader per tillstånd, tillämpad policy, tillförlitlighetsgrund) i stället för en konstant. Ett resultat får bara kallas tillförlitligt när alla villkor för det läget är uppfyllda.

**Känslighetsintervall i stället för antagande:** när okänd sal finns beräknas resultatet mot båda gränserna och skillnaden redovisas. Det uppfyller princip 4 (varken ledig eller alla upptagna) utan att välja.

## 5. Föreslagna begränsade korrigeringar

Allt nedan ligger i datainläsning, undantagshantering och redovisning. **Ingenting ändrar optimeringsmotorns grundantaganden.**

| Åtgärd | PR | Omfattning |
|---|---|---|
| A1 Ny modul för klassificering av bokningsrader till resurstillstånd, regler i konfiguration, förinställning försiktig | #14 (grund), används av #15 | Medel; ersätter F1, F3, F4 |
| A2 Etiketter och räkningar i vyerna per tillstånd i stället för "sal ej angiven"; tillstånd visas med förklaring | #14/#15 | Liten efter A1 |
| A3 Täckningsfönstret för Ladok härleds ur data; länkstatus får `outside_source_coverage` | #14/#15 | Liten |
| A4 Registermatchning som eget tillstånd; kapacitetsmisstanke (`peak > kapacitet`) markeras som datatillstånd | #14/#15 | Liten |
| A5 Länkstatus per rad: uttrycklig regel i stället för första raden | #14 | Mycket liten |
| A6 `planning_basis` härleds (läge, skäl, tillstånd) | #13 | Liten; i dag blir resultatet fortfarande explorativt |
| A7 **Ersätt avsnitt 3 i `PERIODVAL_OCH_SNABBA_KORNINGAR.md`** med designen i avsnitt 4 här | #13 | Dokumentation |
| A8 Parametern `rooms.eligibility_basis` (explorativ eller operativ) i stället för hårdkodat val | motorn | Liten, men en ändring i motorns indata; bör beslutas separat |

Inget av detta kräver ombyggnad för att utnyttja bättre data: A1–A3 gör att ett nytt uttag med korrekt sal automatiskt ger `room_known`.

## 6. Testmatris (princip 6)

Syntetiska bokningsuppsättningar som genom samma kod ska ge rätt tillstånd, räkningar och beteende:

| Uppsättning | Innehåll | Förväntat |
|---|---|---|
| S-A Fullständig | Alla rader har sal som finns i registret | Allt `room_known`; ingen osäkerhet; läget kan bli tillförlitligt |
| S-B Adressnivå deklarerad | Adress deklarerad som adressnivå; rader utan sal | `address_level_declared`; ingen osäkerhetsredovisning; adressreduktion enligt deklarationen |
| S-C Blandad | Namngivna salar, saknade salar utan förklaring, hemtenta, pseudo-lokal i adressfält, sal som saknas i registret | Varje rad i rätt tillstånd; räkningarna går ihop; explorativt läge märkt, tillförlitligt läge nekas över tröskeln |
| S-D Tilldelas senare | Rader med status "Under behandling" och utan sal | `room_pending`; behandlas som efterfrågan |
| S-E Täckning | Bokningar utanför Ladok-fönstret och inom det | `outside_source_coverage` skiljs från `link_none_within_coverage` |
| S-F Kapacitetsmotsägelse | Bokade platser över salens kapacitet | Tillstånd markerat, inte dolt |

Tester i PR #14/#15 täcker i dag S-A och en blandad uppsättning av enklare slag; matrisen ovan är det som saknas.

## 7. Beslut och bekräftelser som behövs från verksamhetsägaren

1. Betyder frånvaro av salnamn på Klostergatan 3 och Danmarksgatan 30 en avsiktlig adressnivåbokning eller en lucka? Vad är bokningarna med medianen två platser?
2. Vad betyder frånvaro av sal på Fyrislundsgatan 80 (hälften av raderna)?
3. Är "Hemma/Hemtenta" och "Ordinarie sal utan anpassningar" bokningstyper som aldrig ska spärra en fysisk sal?
4. Vilka statusar är bokningar som ännu inte fått sal (`Under behandling`, `Andring begard`)?
5. Vilka tröskelvärden gäller för tillförlitlig planering (andel `room_unknown`, `invalid`)?
6. Vilka salar får bli operativt godkända och på vilket underlag (jfr `eligible_for_operational_scheduling`)?

## 8. Rekommenderad ordning

1. Beslut om vilka av A1–A8 som ska genomföras (särskilt A7 och A1).
2. A7 först, eftersom den felaktiga designen står i PR #13.
3. A1–A5 på PR #14/#15, med testmatrisen i avsnitt 6.
4. A6 och A8 separat, eftersom de rör körningens redovisning och motorns indata.
5. Steg 3 (hänsyn till redan lagda bokningar i optimeringen) påbörjas först när resurstillstånden finns och policyn är beslutad.

## 9. Status efter genomförande

| Åtgärd | Status |
|---|---|
| A7 Ny design för steg 3 | **Genomförd** i PR #13: avsaknad av salnamn leder aldrig automatiskt till spärrning eller adressbaserad kapacitetsreduktion. |
| A6 Härledd `planning_basis` | **Genomförd** i PR #13: läget härleds ur motorns förmåga och datat (operativt godkända salar, provisorisk efterfrågan) och skälen visas. |
| A1 Datakvalitets- och klassificeringslager | **Genomfört som fristående lager** (`src/tentaoptimering/booking_quality/`, PR #14). Påverkar inte optimeringsmotorn och styr ingen spärrning, kapacitetsreduktion eller godkännande. |
| A2–A5 Vyerna följer lagret | **Genomförda** i PR #15: "sal ej angiven" ersatt av resursidentifiering, Ladok-täckning skild från kopplingskvalitet, uttrycklig länkregel, kapacitetsmotsägelser flaggade. |
| A8 `rooms.eligibility_basis` | Ej genomförd (rör motorns indata; kräver beslut). |
| Steg 3 i motorn | Ej påbörjad. Väntar på bättre bokningsuttag, svar på `docs/FRAGOR_TILL_DATAAGARE.md` och beslutad policy. |

Dimensionernas oberoende och konfigurationsstyrningen prövas av `tests/test_booking_quality.py` (S-A–S-F på syntetiska uttag).
