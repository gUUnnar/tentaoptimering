# Krav och aktuell status

**Status:** enda aktuella kravuppfyllnadsmatrisen.
**Avstämd:** 2026-10-14 mot `main` efter PR #21.
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

De viktigaste hindren är fasta bokningar utanför optimeringspopulationen,
program-/studentkrockar, verifierad digital- och lokaltillgänglighet,
individuella arbets- och avtalsregler, full population samt avvecklingsbara
kostnadsobjekt.

## A. Omfattning, period och fullständig täckning

| Krav | Status | Nuvarande omfattning och begränsning | Bevis |
|---|---|---|---|
| Varje inkluderat tentamensbehov placeras exakt en gång | **Implementerat** | Gäller modellerbara behov i den valda körningens omfattning. En lösning med oplacerad obligatorisk efterfrågan underkänns. | `tests/test_joint_optimizer.py`, `tests/test_joint_validation.py` |
| Alla dimensionerande tentander placeras utan dubbelräkning | **Implementerat** | Deltagare ägs av delgrupper och summeras till behov. Samtentors disjunkthet är fortfarande ett antagande. | `tests/test_joint_optimizer.py`, `tests/test_joint_validation.py` |
| Täckning av hela källpopulationen | **Datablockerat** | Omkring 266 av 1 525 Ladokaktiviteter är oavgjorda; exakta aktuella tal ska tas från körningens underlag och inte hårdkodas i resultattext. | `joint_input.json`, [datagap](BLOCKERANDE_DATAGAP.md) |
| Valfri sammanhängande planeringsperiod | **Implementerat** | Datumvalet skär både urval och kandidatkalender till vald period. Helt eller delvis otäckt period avvisas eller kräver uttryckligt godkännande. | `tests/test_joint_period.py`, `tests/test_joint_period_run.py` |
| Dag-, vecko- och andra kortperiodskörningar utan manuell TOML | **Implementerat** | Samma API, artefakter och eftervalidering används som för större körningar. | `tests/test_joint_period.py`, frontendens periodtester |
| Redan lagda bokningar blockerar resurser vid korttidsplanering | **Saknas** | Motorn läser ännu inte reservationer för bokningar utanför den valda optimeringspopulationen. Korta körningar är därför explorativa. | [period- och reservationsdesign](PERIODVAL_OCH_SNABBA_KORNINGAR.md) |
| Ursprungligt schema bevaras när en ändring saknar tillräcklig nytta | **Delvis** | Ursprungstillfället används som preferens efter kostnaden. Ingen kronviktad avvägning mellan verksamhetens önskemål och kostnad finns. | `joint_preference.py`, `tests/test_joint_optimizer.py` |

## B. Gemensam optimering och ekonomi

| Krav | Status | Nuvarande omfattning och begränsning | Bevis |
|---|---|---|---|
| Datum, starttid, salar och bemanningspool optimeras gemensamt | **Implementerat** | Gäller den gemensamma modellens salstillfällen och aggregerade samtidiga vaktpool. | `joint_optimizer.py`, `joint_strategy/`, handräknade tester |
| Hela vald period löses med en gemensam portfölj och pool | **Implementerat** | Den dekomponerade strategin delar exakta dagkontroller men bevarar gemensam portfölj, pool, undre gräns och full eftervalidering. Resultat kan ha optimalitetsgap. | [optimeringsstrategin](OPTIMERINGSSTRATEGI.md) |
| Bemanningsstyrkans storlek är kostnadsvariabel | **Implementerat** | En anonym samtidig pool kostnadssätts. Individernas anställningsformer och verkliga kostnader ingår inte. | `joint_optimizer.py`, validerarens bemannings- och kostnadsregler |
| Externhyra och korttidsdebitering | **Delvis** | Motorn och eftervalideraren kostnadssätter externa salstillfällen, men nuvarande dataadapter skapar inga sådana kostnadsatta alternativ och katalogparametern saknar motorstöd. | `tests/test_joint_strategy.py`, [kostnadsmodellen](KOSTNADSMODELL.md) |
| Bomtid, transport och betald tid i målfunktionen | **Saknas** | Redovisas inte som fullständiga gemensamma kostnadsvariabler i nuvarande motor. | [kollektivavtalsanalysen](ANALYS_KOLLEKTIVAVTAL.md) |
| Modellkostnad skiljs från faktisk kostnad och besparing | **Implementerat** | A saknar fördelad faktisk kostnad; körningar redovisar proxybaserad modellkostnad; potential jämför två modellkörningar. | [A/B/C](ABC_SCENARIOMODELL.md), [kostnadsmodellen](KOSTNADSMODELL.md) |
| Verifierad realiserbar besparing | **Datablockerat** | Kräver avtalsobjekt, undvikbarhet, uppsägningstid, engångskostnader och verifierade personal-/externkostnader. | [kostnadsmodellen](KOSTNADSMODELL.md) |

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
| A–B, A–C, B–C och C–C kan jämföras säkert | **Delvis** | Jämförelser spärras vid olika underlag/tentamängd och kostnadsskillnad spärras vid ändrade antaganden. A saknar faktisk kostnad och vissa saljämförelser är inte möjliga. | `profile_compare.py`, `tests/test_abc_runs.py` |
| Lokalens bokningar kan inspekteras utan optimering | **Delvis** | Bokningar och bokad tid visas. Verklig beläggning och verifierad tillgänglig tid saknas. | `booking_views.py`, `booking_overview.py` och tester |
| En bokad tentamen kan sökas och jämföras med simulering | **Delvis** | Flera salar och osäkra kopplingar redovisas. Observerat utfall och vissa saljämförelser saknas. | `booking_compare.py` och tester |
| Vanlig Windowsdator utan Python/Node/Docker | **Inte verifierat** | Paketeringsflöde finns, men föreskrivet offlineprov på ren Windowsprofil efter ombyggnaden är inte dokumenterat genomfört. | [lokalt gränssnitt](LOKALT_GRANSSNITT.md) |

## F. Eftervalidering och beslutbarhet

| Krav | Status | Nuvarande omfattning och begränsning | Bevis |
|---|---|---|---|
| Fristående teknisk eftervalidering | **Implementerat** | Läser sparad indata, resultat och manifest utan att importera optimerarens regel- eller kostnadskod. | [eftervalideringen](OBEROENDE_EFTERVALIDERING.md), AST-test |
| Regelvis `pass`, `fail`, `not_evaluated`, `not_applicable` | **Implementerat** | Saknad data eller motorstöd blir aldrig `pass`. | `tests/test_joint_validation.py` |
| Teknisk placering skiljs från verksamhetsgenomförbarhet | **Implementerat** | Axlarna rapporteras separat. | valideringskontrakt och rapporttester |
| Verksamhetsmässigt godkänd körning | **Saknas** | Grundreglerna är fortfarande `not_evaluated` eftersom oberoende verksamhetsunderlag och fullständigt motorstöd saknas. | `business_verification` i sparade valideringsresultat |

## Prioriterad återstående ordning

1. Inför ett reservationslager för fasta bokningar och koppla det till motorn och
   eftervalideringen.
2. Fastställ verifierat, tidsversionerat lokalregister inklusive digital
   kompatibilitet och tillgänglighet.
3. Lös program-/studentkrockar och verifiera definitionen av samtentor.
4. Modellera tillämpliga individuella arbetstids- och avtalsregler.
5. Importera full efterfrågeperiod och verklig beläggning med säkra nycklar.
6. Koppla lokaler och personal till undvikbara kostnadsobjekt innan realiserbar
   besparing beräknas.
7. Genomför och dokumentera offlineprov av Windowsdistributionen.

Matrisen uppdateras i samma ändring som ett krav får ny status. En status får
inte höjas till `Implementerat` utan namngivet test eller reproducerbar körning,
och aldrig till verksamhetsmässigt godkänd enbart på grund av teknisk
eftervalidering.
