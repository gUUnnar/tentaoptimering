# Krav och aktuell status

**Status:** enda aktuella kravuppfyllnadsmatrisen.
**Avstämd:** 2026-10-15 mot grenen `feature/forklarad-totalbesparing` (efter PR #21).
**Tolkning:** statusen bygger på versionshanterad implementation, dokumenterade
tester och sparade körningar. Den är inte ett verksamhetsgodkännande.

## Statusord

| Status | Betydelse |
|---|---|
| **Implementerat** | Funktion och bevisande test eller körning finns för den angivna omfattningen. |
| **Delvis** | En användbar del finns, men hela kravet är inte uppfyllt. |
| **Saknas** | Nödvändigt modell- eller produktstöd saknas. |
| **Datablockerat** | Arkitekturen kan hantera uppgiften, men verifierbar indata eller verksamhetsbeslut saknas. |
| **Inte verifierat** | Funktionen kan finnas men föreskriven verifiering är inte genomförd. |

`Implementerat` betyder aldrig automatiskt att en regel är
verksamhetsverifierad. En körning får kallas tekniskt godkänd endast när den
oberoende eftervalideringen passerar. Den får kallas verksamhetsmässigt
genomförbar endast när alla tillämpliga hårda verksamhetsregler har kunnat
utvärderas och passerat.

## Sammanfattande dom

PoC:n är ett fungerande **explorativt optimerings- och analysverktyg**. Den kan
producera fullständiga, tekniskt eftervaliderade placeringar för en uttryckligen
vald och modellerbar omfattning. Den är inte ännu ett operativt
schemaläggningssystem och kan inte beräkna verifierad realiserbar besparing.

Två alternativ (A, B eller sparade C-körningar) kan jämföras i kronor och i konkreta
förändringar av namngivna lokaler, externa bokningar, bokningar och betalda
personaltimmar. Alla kostnads- och avtalsuppgifter som används är ännu
**simulerade**, så en förklarad skillnad är en modellberäkning och aldrig en
verifierad besparing.

De viktigaste hindren är verkliga kostnads-, avtals- och bemanningsuppgifter,
bokningar som saknar identifierad sal, program-/studentkrockar, verifierad
digital- och lokaltillgänglighet, individuella arbets- och avtalsregler samt full
population.

## A. Omfattning, period och fullständig täckning

| Krav | Status | Nuvarande omfattning och begränsning | Bevis |
|---|---|---|---|
| Varje inkluderat tentamensbehov placeras exakt en gång | **Implementerat** | Gäller modellerbara behov i den valda körningens omfattning. En lösning med oplacerad obligatorisk efterfrågan underkänns. | `tests/test_joint_optimizer.py`, `tests/test_joint_validation.py` |
| Alla dimensionerande tentander placeras utan dubbelräkning | **Implementerat** | Deltagare ägs av delgrupper och summeras till behov. Samtentors disjunkthet är fortfarande ett antagande. | `tests/test_joint_optimizer.py`, `tests/test_joint_validation.py` |
| Täckning av hela källpopulationen | **Datablockerat** | Omkring 266 av 1 525 Ladokaktiviteter är oavgjorda; exakta aktuella tal ska tas från körningens underlag och inte hårdkodas i resultattext. | `joint_input.json`, [datagap](BLOCKERANDE_DATAGAP.md) |
| Valfri sammanhängande planeringsperiod | **Implementerat** | Datumvalet skär både urval och kandidatkalender till vald period. Helt eller delvis otäckt period avvisas eller kräver uttryckligt godkännande. | `tests/test_joint_period.py`, `tests/test_joint_period_run.py` |
| Dag-, vecko- och andra kortperiodskörningar utan manuell TOML | **Implementerat** | Samma API, artefakter och eftervalidering används som för större körningar. | `tests/test_joint_period.py`, frontendens periodtester |
| Redan lagda bokningar blockerar resurser vid korttidsplanering | **Delvis** | Bokningar utanför de valda tentorna som identifierar en sal i modellen spärrar salen under sin tid plus ställtid och gör att salen räknas som använd (`reservations.policy`, standard spärra). Bokningar som bara anger adress eller en sal som modellen saknar kan inte spärra något; de räknas och redovisas som oidentifierade. Salen spärras hel (registret har ingen finare enhet) och personalen för de fasta bokningarna ingår inte. | `tests/test_joint_paid_time.py`, `tests/test_resource_data.py`, `tests/test_explained_saving_chain.py`, [period- och reservationsdesign](PERIODVAL_OCH_SNABBA_KORNINGAR.md) |
| Ursprungligt schema bevaras när en ändring saknar tillräcklig nytta | **Delvis** | Ursprungstillfället används som preferens efter kostnaden. Ingen kronviktad avvägning mellan verksamhetens önskemål och kostnad finns. | `joint_preference.py`, `tests/test_joint_optimizer.py` |

## B. Gemensam optimering och ekonomi

| Krav | Status | Nuvarande omfattning och begränsning | Bevis |
|---|---|---|---|
| Datum, starttid, salar och bemanningspool optimeras gemensamt | **Implementerat** | Gäller den gemensamma modellens salstillfällen och aggregerade samtidiga vaktpool. | `joint_optimizer.py`, `joint_strategy/`, handräknade tester |
| Hela vald period löses med en gemensam portfölj och pool | **Implementerat** | Den dekomponerade strategin delar exakta dagkontroller men bevarar gemensam portfölj, pool, undre gräns och full eftervalidering. Resultat kan ha optimalitetsgap. | [optimeringsstrategin](OPTIMERINGSSTRATEGI.md) |
| Bemanningsstyrkans storlek är kostnadsvariabel | **Implementerat** | En anonym samtidig pool kostnadssätts. Individernas anställningsformer och verkliga kostnader ingår inte. | `joint_optimizer.py`, validerarens bemannings- och kostnadsregler |
| Externhyra och korttidsdebitering | **Implementerat** | Externa salar i resursdatan debiteras per salstillfälle (fast pris eller timpris med minsta debiterade tid) och konkurrerar med fasta lokaler i alla lösningsvägar och i eftervalideringen. Debiteringsvillkoren i resursdatan är ännu simulerade. | `tests/test_resource_data.py`, `tests/test_explained_saving_chain.py`, [kostnadsmodellen](KOSTNADSMODELL.md) |
| Bomtid, transport och betald tid i målfunktionen | **Delvis** | Varje vaktposition i ett salstillfälle är ett betalt pass (förberedelse, tentamen, avslut, lägst kortaste betalda pass, plus salens betalda restid) och kostar en kostnad per betald minut; kostnaden härleds ur betald tid, inte ur en schablon. Luckor mellan en persons pass är obetalda (varje pass är eget), och individuella arbetstids-, rast- och vilouppgifter ingår inte. Modellen kan välja fler betalda timmar när lokalbesparingen är större. | `tests/test_joint_paid_time.py`, `tests/test_joint_paid_time_differential.py`, [kollektivavtalsanalysen](ANALYS_KOLLEKTIVAVTAL.md) |
| Modellkostnad skiljs från faktisk kostnad och besparing | **Implementerat** | A saknar fördelad faktisk kostnad; körningar redovisar proxybaserad modellkostnad; potential jämför två modellkörningar. | [A/B/C](ABC_SCENARIOMODELL.md), [kostnadsmodellen](KOSTNADSMODELL.md) |
| Namngivna lokaler kopplade till hyres- eller avtalsobjekt och kostnadsregler med ursprung | **Implementerat** | Resursdata (`config/resource_data/`) bär namngivna salar, avtalsobjekt (undvikbarhet, uppsägningstid, tidigaste frigörande, engångskostnad), externhyror och personalregler, var och en märkt `observed`, `model_calculated`, `simulated` eller `assumption` med giltighetsperiod. Samma kontrakt bär verkliga och simulerade uppgifter; körningen fryser den använda resursdatan. Den medföljande filen är simulerad. | `tests/test_resource_data.py`, [datamodellen](DATAMODELL.md) |
| Verifierad realiserbar besparing | **Datablockerat** | Besparingen från en sal som slutar användas klassas mot avtalsobjektet (`verified`, villkorad, delat avtal, ej uppsägningsbart) men kan bara bli verifierad av observerade avtalsuppgifter. Alla nuvarande uppgifter är simulerade, så verifierad besparing är alltid noll. | `tests/test_abc_explain.py`, [kostnadsmodellen](KOSTNADSMODELL.md) |

## C. Hårda regler

| Krav | Status | Nuvarande omfattning och begränsning | Bevis |
|---|---|---|---|
| Fysisk salskapacitet och tidsöverlapp | **Implementerat** | Kontrolleras mot kapaciteten och tillgängligheten i modellens indata. Källvärdenas verksamhetsgiltighet är inte därmed verifierad. | `tests/test_joint_optimizer.py`, validerarens salsregler |
| Digital kompatibilitet | **Delvis** | Teknisk kompatibilitet prövas mot indata och policy. Faktisk kompatibilitet per sal, plats och period är inte verifierad. | `tests/test_joint_review_fixes.py`, `business_verification = not_evaluated` |
| Uppsala och Visby är separata planeringsområden | **Implementerat** | Ort är ett hårt modellvillkor. Verksamhetsbedömning av Visby blockeras av otillräcklig efterfrågan och lokaldata. | validerarens `room_planning_area`-regel |
| Samma kurs kolliderar inte | **Implementerat** | Kurskod och uttryckliga konfliktgrupper kontrolleras. | optimerar- och valideringstester |
| Program- och studentkrockar | **Datablockerat** | Student-/programrelationer saknas och fullständigt motorstöd kan därför inte verifieras. Regeln är `not_evaluated`, aldrig `pass`. | validerarens `student_overlap`-regel |
| Ställtid och salens återanvändning | **Implementerat** | Salstillfällets senaste sluttid plus ställtid styr nästa möjliga start. | handräknade gränsfall i `tests/test_joint_optimizer.py` och `tests/test_joint_validation.py` |
| Individuella arbets-, rast-, vilo- och avtalsregler | **Saknas** | Nuvarande pool är aggregerad. Kortaste betalda pass, begränsningsperiod, arbetsdagar, helgnorm, individuell vila, kompetens och tillgänglighet är inte fullständigt modellerade. | [kollektivavtalsanalysen](ANALYS_KOLLEKTIVAVTAL.md) |

Explorativa körningar får genomföras när en verksamhetsregel är
`not_evaluated`, men resultatet får då inte kallas verksamhetsmässigt
genomförbart. Detta är föreningen mellan kravet på hårda regler och möjligheten
att utforska effekter trots ofullständiga data.

## D. Data, spårbarhet och datakvalitet

| Krav | Status | Nuvarande omfattning och begränsning | Bevis |
|---|---|---|---|
| Beställning, bokningsplacering och Ladokaktivitet hålls isär | **Implementerat** | Olika korn och provisoriska relationer bevaras. | [datamodellen](DATAMODELL.md) |
| Antaganden är deklarerade och utbytbara | **Implementerat** | Parameterkatalog, grund, scenario och frusen körningsindata sparas. | [parameterkatalogen](PARAMETERKATALOG.md), `joint_run.json` |
| Underlag, modellversion och artefakter är spårbara | **Implementerat** | Körningsmanifest och hashar eftervalideras. | proveniensregler i [eftervalideringen](OBEROENDE_EFTERVALIDERING.md) |
| Verifierat tidsversionerat salregister | **Datablockerat** | Kapacitet och tillgänglighet saknas eller är preliminär för flera historiskt använda lokaler. | [datagap](BLOCKERANDE_DATAGAP.md) |
| Verklig beläggning/närvaro | **Datablockerat** | Den annonserade leveransen är ännu inte en verifierad importerad källa. Saknad observation behandlas som okänd, aldrig noll. | [datamodellen](DATAMODELL.md) |
| Samtentors deltagargrupper är verifierat disjunkta | **Datablockerat** | Nuvarande summering redovisas som antagande. | validerarens `group_disjointness` |

## E. A, B, C och användargränssnitt

| Krav | Status | Nuvarande omfattning och begränsning | Bevis |
|---|---|---|---|
| A återger faktisk bokning och optimeras aldrig | **Implementerat** | Historiska brister bevaras och A har ingen påhittad kostnad. | `profile_actual.py`, `tests/test_abc_actual.py` |
| B och C använder samma motor | **Implementerat** | Skillnaden är frusna parametervärden och körningstyp, inte algoritm. | [A/B/C](ABC_SCENARIOMODELL.md), `run_meta.py` |
| Körningar skrivs aldrig över och kan återanvändas | **Implementerat** | Namn, typ, parametrar, underlag och modellversion sparas per körning. | `joint_run.json`, körnings- och API-tester |
| A–B, A–C, B–C och C–C kan jämföras säkert | **Implementerat** | Jämförelser spärras vid olika underlag, tentamängd, efterfrågan och när A inte kan prissättas fullständigt. A prissätts med körningens regler (modellberäknad kostnad för de historiska bokningarna, märkt som sådan; bokningar med bara adress godtas under en temporär regel med noll hyra, så A:s kostnad är en underkant) och dess bemanning märks som beräknad ur bokade platser, aldrig som observerad. | `abc_explain.py`, `tests/test_abc_explain.py`, `tests/test_explained_saving_chain.py` |
| Totalskillnaden förklarad i kostnadsposter, lokaler, bokningar och personaltimmar | **Implementerat** | Posterna hyrda lokaler, externa bokningar och personal summerar exakt till totalskillnaden; skillnaden delas i ändrat resursutnyttjande och ändrade priser/antaganden; namngivna lokaler som behålls, tillkommer eller kan avvaras, tentor med före-/efteruppgifter och personalpass visas, och gränssnittet leder från total till post till lokal, tentamen och pass. Förklaringen är modellberäknad; historisk kostnad, teoretisk årlig potential (kräver årsomräkning som saknas) och verifierad besparing redovisas separat. | `tests/test_abc_explain.py`, `tests/test_explained_saving_chain.py`, `frontend/src/lib/abcExplainView.test.ts` |
| Lokalens bokningar kan inspekteras utan optimering | **Delvis** | Bokningar och bokad tid visas. Verklig beläggning och verifierad tillgänglig tid saknas. | `booking_views.py`, `booking_overview.py` och tester |
| En bokad tentamen kan sökas och jämföras med simulering | **Delvis** | Flera salar och osäkra kopplingar redovisas. Observerat utfall och vissa saljämförelser saknas. | `booking_compare.py` och tester |
| Vanlig Windowsdator utan Python/Node/Docker | **Inte verifierat** | Paketeringsflöde finns, men föreskrivet offlineprov på ren Windowsprofil efter ombyggnaden är inte dokumenterat genomfört. | [lokalt gränssnitt](LOKALT_GRANSSNITT.md) |

## F. Eftervalidering och beslutbarhet

| Krav | Status | Nuvarande omfattning och begränsning | Bevis |
|---|---|---|---|
| Fristående teknisk eftervalidering | **Implementerat** | Läser sparad indata, resultat och manifest utan att importera optimerarens regel- eller kostnadskod. | [eftervalideringen](OBEROENDE_EFTERVALIDERING.md), AST-test |
| Regelvis `pass`, `fail`, `not_evaluated`, `not_applicable` | **Implementerat** | Saknad data eller motorstöd blir aldrig `pass`. | `tests/test_joint_validation.py` |
| Teknisk placering skiljs från verksamhetsgenomförbarhet | **Implementerat** | Axlarna rapporteras separat. | valideringskontrakt och rapporttester |
| Fasta bokningar, betald personaltid och resursdatans ursprung eftervalideras | **Implementerat** | Valideraren kontrollerar att inget salstillfälle överlappar en fast bokning, räknar om betalda pass och minuter och kostnaden ur placeringen, och att den frusna resursdatan är den som manifestet anger. Resursdata och fasta bokningars fullständighet är alltid `not_evaluated` på verksamhetsaxeln; simulerade uppgifter blir aldrig verifierade. | `tests/test_joint_paid_time.py`, `tests/test_joint_paid_time_differential.py`, `tests/test_explained_saving_chain.py` |
| Verksamhetsmässigt godkänd körning | **Saknas** | Grundreglerna är fortfarande `not_evaluated` eftersom oberoende verksamhetsunderlag och fullständigt motorstöd saknas. | `business_verification` i sparade valideringsresultat |

## Prioriterad återstående ordning

1. Ersätt de simulerade resursuppgifterna med verkliga hyresavtal, externhyror
   och personalkostnader (Retendo/lön) i en ny fil i `config/resource_data/`, och
   identifiera de bokningar som saknar sal så att de kan spärra.
2. Fastställ verifierat, tidsversionerat lokalregister inklusive digital
   kompatibilitet och tillgänglighet.
3. Lös program-/studentkrockar och verifiera definitionen av samtentor.
4. Modellera tillämpliga individuella arbetstids- och avtalsregler.
5. Importera full efterfrågeperiod och verklig beläggning med säkra nycklar.
6. Verifiera avtalsobjektens undvikbarhet, uppsägningstid och engångskostnad mot
   verkliga avtal så att en förklarad lokalbesparing kan bli verifierad.
7. Genomför och dokumentera offlineprov av Windowsdistributionen.

Matrisen uppdateras i samma ändring som ett krav får ny status. En status får
inte höjas till `Implementerat` utan namngivet test eller reproducerbar körning,
och aldrig till verksamhetsmässigt godkänd enbart på grund av teknisk
eftervalidering.
