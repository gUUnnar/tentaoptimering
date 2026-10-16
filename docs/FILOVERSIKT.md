# Filöversikt

Detta är innehållsförteckningen för de versionshanterade filer som utgör PoC:n. Den beskriver ansvar, inte rad-för-rad-innehåll. Uppdatera översikten tillsammans med varje väsentlig filförändring.

## Rotnivå

| Fil | Ansvar |
|---|---|
| `.gitattributes` | Git-attribut för textfiler. |
| `.gitignore` | Utesluter källexporter, reproducerbar data, byggresultat och lokal miljö från Git. |
| `AGENTS.md` | Arbetsregler för agenten, inklusive modellavgränsning, verifiering och filstorlekspolicy. |
| `README.md` | Projektets syfte, körinstruktioner, leverabler och avgränsning. |
| `pyproject.toml` | Python-paketets metadata, beroenden, kommandoradspunkt och verktygskonfiguration. |
| `frontend/` | Separat byggbar React-, TypeScript-, Vite- och Tailwind-klient för det lokala gränssnittet. |
| `packaging/build_windows.ps1` | Bygger frontend och paketerar lokal Windowsdistribution med PyInstaller. |
| `packaging/desktop_entry.py` | Paketvänlig Pythonstartpunkt för den lokala Windowsapplikationen. |

## Konfiguration

| Fil | Ansvar |
|---|---|
| `config/data_preparation.toml` | Konfiguration för dataförberedelsen (`prepare`): efterfrågemått och de explicita PoC-antagandena om lokalbestånd. Ersätter det borttagna `config/parameters.toml`. |
| `config/joint_parameter_catalog.toml` | Gemensam v2-katalog (version 2.5.0, 63 parametrar) för GUI, lagring, validering och ny motor, inklusive explicit motorstöd per parameter och tillåtna val (`choices`) för valparametrar, bland annat vald resursdata, kostnad per betald minut, fasta bokningar och bortvalda salar. |
| `config/resource_data/simulated_dev_2026.toml` | SIMULERAT resurspaket (schema `resource-data-v1`): namngivna salar, avtalsobjekt med undvikbarhet och uppsägningsvillkor, externhyra (Fyrishovs hallar), betald personalkostnad och en exempelrad faktisk bemanning, allt märkt `simulated`. Ersätts av verkliga uppgifter genom en ny fil i samma mapp och en ny rad i valen för `resources.pack`. |
| `config/room_register.toml` | Versionsmärkt officiellt rumsreferenslager med publicerade kapaciteter, källadress och tidsmässig osäkerhet. |
| `config/booking_data_quality.toml` | Regler och kolumnnamn för datakvalitetslagret med `verified`, `source` per regel. Nya verifierade uppgifter eller andra kolumnnamn i ett nytt uttag läggs till här utan kodändring. Inga adress- eller salmönster är verifierade. |
| `config/source_files.toml` | Namn, blad och rubrikrad för de tre lästa källexporterna. |
| `config/scenarios/joint_real_subset.toml` | Reproducerbart avgränsat verkligt datafall för den nya gemensamma CP-SAT-kärnan (med `reservations.policy = none` så att regressionssiffran är oförändrad). Markerat `hidden = true`: ett test- och utvecklingsscenario som inte erbjuds som utgångspunkt i gränssnittet. |
| `config/scenarios/joint_base.toml` | B – Grundoptimering och förval: alla klara tentor i Uppsala i hela underlaget, katalogens standardvärden utom fem motiverade antaganden (bara verksamhetens önskemål som datum, önskemålsprioritet bland lika billiga lösningar, observerade salar utan registerkapacitet, ett explorativt pris per plats för salar som resursdatan inte prissätter och de simulerade resursuppgifterna). Utgångspunkt för egna körningar (C). Testat i `tests/test_joint_reference.py`. |
| `config/scenarios/joint_underlay_period.toml` | Befintligt avgränsat scenariourval i Uppsala (`joint_underlay_period_2026`), 12 januari–31 mars 2026: regel `selection = "all_ready"` med datumintervall, 1 172 tentor. Ingen generell minsta terminslängd; framtida användarstyrt periodval är krav. Markerat `hidden = true`: ett test- och utvecklingsscenario som inte erbjuds som utgångspunkt i gränssnittet. |

## Dokumentation

| Fil | Ansvar |
|---|---|
| `docs/README.md` | Kanonisk dokumentationsingång med läsordning och gräns mellan styrande dokument, tekniska referenser, verksamhetsunderlag och historik. |
| `docs/ABC_SCENARIOMODELL.md` | Den gällande begreppsmodellen: A (faktisk bokning, aldrig optimerad), B (grundoptimering utifrån verksamhetens önskemål) och C (egna körningar): vad som sparas, hur körningar jämförs, hur önskemål, kostnad och lokalutnyttjande vägs, datakvalitet och kvarstående begränsningar. |
| `docs/KONCEPTUELL_KRAVSPECIFIKATION.md` | Bindande verksamhetskrav, målbild och acceptanstester. |
| `docs/KRAV_OCH_STATUS.md` | Enda aktuella kravuppfyllnadsmatrisen: en status, begränsning och bevis per krav. |
| `docs/BLOCKERANDE_DATAGAP.md` | Datagap som måste lösas före tillförlitlig optimering eller kronberäkning. |
| `docs/VERKSAMHETSUNDERLAG_2026-10-02.md` | Källtrogen genomgång av verksamhetspresentationens kapacitet, planerade platser, bemanningsregler och historiska kalkyler, inklusive oklarheter och verifieringsbehov. |
| `docs/DATAMODELL.md` | Korn, nycklar och gränser mellan beställning, placering, Ladokaktivitet och lokalrad; tidsmässig datatäckning och åtskild verklig beläggning. |
| `docs/FILOVERSIKT.md` | Denna innehållsförteckning och filernas ansvar. |
| `docs/GEMENSAM_OPTIMERINGSDESIGN.md` | Teknisk specifikation för kanoniskt tentamensbehov, salstillfällen, integrerad bemanning och konsekvent årskostnad. |
| `docs/OBEROENDE_EFTERVALIDERING.md` | Valideringens design, regelkatalog, verkliga statusar för 12-tentakörningen, kvarstående datagap och hur den körs. |
| `docs/OPTIMERINGSSTRATEGI.md` | Analys av den monolitiska modellens beräkningskostnad, den rekommenderade strategin (aggregerad relaxation och daglig kontroll), mätningar på frysta verkliga instanser och kvarstående risker. |
| `docs/PERIODVAL_OCH_SNABBA_KORNINGAR.md` | Valbar planeringsperiod i gränssnittet och dess regler, mätning av snabba körningar och teknisk design (ej implementerad) för hänsyn till redan lagda bokningar vid korttidsplanering. |
| `docs/ARKITEKTURPRINCIPER_DATAKVALITET.md` | Principer för att hålla verksamhetsmodell och datakvalitet isär: vad saknad sal är i dagens uttag (mätt), granskning av PR #13–15 mot principerna, föreslagen arkitektur med resurstillstånd och policy per planeringsläge, begränsade korrigeringar, testmatris och frågor till verksamhetsägaren. |
| `docs/FRAGOR_TILL_DATAAGARE.md` | Frågor till dataägaren om bokningsuttaget (sal, status, icke-fysiska lokaler, salsregister, Ladok-täckning) och om tentavakter, med siffror ur datakvalitetsrapporten och hur svaren läggs in som verifierade regler. |
| `docs/KOSTNADSMODELL.md` | Avgränsning mellan resursbehov, intern kostnadsfördelning och realiserbar besparing. |
| `docs/PARAMETERKATALOG.md` | Utkast till den enda parameterkatalogen (endast parametrar som motorn läser) med grund och effektfall. |
| `docs/ANALYS_KOLLEKTIVAVTAL.md` | Analys av lokalt kollektivavtal för tentamenspersonal och vad som kan bli verifierat. |
| `docs/LOKALT_GRANSSNITT.md` | Arkitektur, API-kontrakt, källkodsutveckling och offlineverifiering av Windowsdistributionen. |
| `docs/historik/README.md` | Register över bevarade historiska rapporter; slår fast att de inte är aktuella krav- eller statuskällor. |
| `docs/historik/GEMENSAM_CP_SAT_FORSTA_LEVERANS.md` | Historisk ögonblicksbild av den första gemensamma CP-SAT-kärnan. |
| `docs/historik/VERKSAMHETSPAVERKAN_2026-10-12.md` | Historisk analys av verksamhetspresentationens påverkan den 12 oktober 2026. |
| `docs/historik/DATAANALYS_S0.md` | Historisk S0-dataanalys. |
| `docs/historik/granskning/*.md` | Sammanhållen revisionsrapport och delrapporter från den 9 oktober 2026. |

## Python-paket: `src/tentaoptimering`

| Fil | Ansvar |
|---|---|
| `__init__.py` | Paketidentifiering och kort paketbeskrivning. |
| `cli.py` | JSON-först-kommandon: `prepare`, `status`, `resources`, `joint-parameters`, `optimize-joint` och `validate-joint-run`. |
| `canonical_demand.py` | Validerar fullständiga scope-beslut och explicita relationer från Ladokaktiviteter via delgrupper till unika tentamensbehov. |
| `joint_contract.py` | Versionsmärkt JSON-kontrakt (v3, v2 läses) för gemensamma modellindata och resultat, inklusive delgrupper, stödstatus, kostnader, solvergränser, fasta bokningar, resursunderlag och betald personaltid. |
| `resource_data.py` | Resurspaketets kontrakt (`resource-data-v1`): namngivna salar, avtalsobjekt, externa debiteringar, personalregler och faktisk bemanning, var och en med ursprung (`observed`, `model_calculated`, `simulated`, `assumption`), källa och giltighet; inläsning, validering, hash och den frusna kopian per körning. |
| `joint_resources.py` | Lägger valt resurspaket i en körning: namn, kostnad, avtalsobjekt och restid för salar, externa salar, personalvärden (ändrad parameter gäller före paketet), bortvalda salar, spårning av vad som är data och vad som är proxy, och frysning av paketet. |
| `joint_reservations.py` | Fasta bokningar utanför de valda tentorna som reservationer: bara identifierade salar spärrar, oidentifierade bokningar räknas och redovisas. |
| `joint_blocking.py` | Reservationerna som villkor i CP-SAT-modellen (spärrad tid plus ställtid, sal med fast bokning är alltid använd). |
| `joint_paid_time.py` | Betald personaltid i CP-SAT-modellen: vaktar × betald längd per sal och pass. |
| `joint_costing.py` | Optimerarens egna salstillfällesrader omsatta till betald tid och kostnad (via `joint_pricing`). |
| `joint_pricing.py` | Prissätter vilken plan som helst (en körning eller den faktiska bokningen) med en sparad körnings regler: hyra, externa debiteringar, betalda pass och minuter, pool. Underlag för jämförelsen. |
| `cost_realization.py` | Kan en lokalbesparing realiseras? Klassar en lokal som inte längre används mot sitt avtalsobjekt (`verified`, villkorad, delat avtal, ej uppsägningsbart); aldrig verifierad av simulerade uppgifter. |
| `abc_ledger.py` | Kostnadsunderlag per alternativ: en körning ur sina artefakter, A prissatt med körningens regler och märkt modellberäknad (aldrig historisk eller observerad bemanning). |
| `abc_explain.py` | Den förklarade skillnaden mellan två alternativ: kostnadsposter som summerar till totalen, utnyttjande mot priser, namngivna lokaler, externa bokningar, betalda pass och timmar, tentor före/efter, realiserbarhet och de fyra kostnadsslagen; spärrar missvisande jämförelser. |
| `joint_optimizer.py` | Ny CP-SAT-kärna som gemensamt optimerar kalenderpass, faktiska salar, bemanningspool och jämförbar kostnad utan partiell placering. |
| `joint_inputs.py` | Adapter (inklusive tolkning av tidsintervallet `HH:MM-HH:MM` till minuter) och körningslagring för det verkliga urvalet (namngivna tentor eller hela vald underlagsperiod enligt regel). Sparar den använda scenariofilen som `joint_scenario.toml` i körningsmappen. |
| `joint_selection.py` | Urval av tentor ur `[subset]`: antingen `exam_event_ids` eller regeln `selection = "all_ready"` med valfritt `date_from`/`date_to`; exakt ett av sätten, annars svenskt fel. |
| `joint_period.py` | Valbar planeringsperiod: datatäckning per källa och dag (`GET /api/joint-runs/period`), kontroll av vald period (tentor som kan planeras, saknat deltagarantal, period utanför underlaget), det scenario en period ger (urval och kalender skärs till perioden) och `PLANNING_BASIS` som märker varje resultat som explorativt (känner inte bokningar utanför de valda tentorna). |
| `wishes.py` | Verksamhetens önskemål ur bokningsexporten (önskat datum, reservdatum 1 och 2, motivering) till `exam_wishes.csv`, ett tentamenstillfälle per rad: status, var det bokade datumet ligger bland önskemålen, motstridiga önskemål och en sammanfattning. Motiveringar tolkas inte. |
| `joint_wishes.py` | Önskemålen som indata till en körning: kandidatdatum enligt `wish.candidate_policy` och `wish.time_policy`; ett krav som behöver önskemålen vägrar köra om underlaget saknar dem. |
| `joint_preference.py` | Det andra målet efter kostnaden (`wish.tiebreak`): straffvikter per tentamen och pass, delade av hela modellen, relaxationen och dagdelproblemen. |
| `joint_observed_rooms.py` | Antagandet `rooms.include_observed_unregistered`: namngivna salar som bokningarna använt men som saknar registerkapacitet, med största bokade antal platser som kapacitet (en underkant, märkt `capacity_basis`). |
| `joint_report.py` | Textrapporten `joint_report.md` för en körning (utbruten ur `joint_inputs.py`). |
| `run_meta.py` | Det en körning sparar om sig själv i `joint_run.json`: namn, typ (B eller C), utgångskörning, ändringar, underlag och modellversion; märkning av äldre underlag. |
| `profile_actual.py` | A – faktisk bokning för ett urval tentor, läst ur bokningarna utan optimering: datum, tid, salar, bokade platser, önskemålsrang, och brister (bara adress, sal utanför registret, avbokad). |
| `profile_run.py` | B och C – en sparad körning i samma form som A, läst ur körningens egna filer; en körning utan verifierad lösning har ingen placering eller kostnad. |
| `profile_common.py` | Mått som är gemensamma för A och körningar: salanvändning och kapacitetsutnyttjande per dag. |
| `profile_compare.py` | Jämförelse av två profiler (A, B eller C): nyckeltal, önskemål, ändrad tid och sal, salar, kostnad per sort, vad som krävs för att kostnaden ska kunna minska, parametrar som skiljer. |
| `abc_compare.py`, `abc_api.py` | Körningslistan, profiler och jämförelse (`/api/abc/runs`, `/profile`, `/compare`, `/wishes`); `/compare` ger även den förklarade skillnaden (`explained`). |
| `joint_options.py` | Valmöjligheter för ett scenario (`GET /api/joint-runs/options`): salarna motorn kan överväga i planeringsområdet (samma urval som motorn bygger sina salar av) med läsbar etikett, byggnad, kapacitet och digitalt stöd, samt de observerade tentamenstyperna med antal tentor. Innehåller också kontrollen av `rooms.selection` (okänt sal-id är ett svenskt fel, aldrig tyst ignorerat). Saknas underlaget blir listorna tomma. |
| `booking_views.py` | Skrivskyddade vyer över historiska bokningar utan optimeringskörning: platser med bokningar, en lokal över ett datumintervall (bokningar, bokad tid utan dubbelräkning av överlapp, bokade platser, högsta samtidiga bokning mot salens kapacitet), sökning av bokade tentamina och en tentamen med alla sina placeringar och Ladok-kopplingens säkerhet. Kapacitet används bara för namngiven sal; verklig närvaro redovisas som okänd. |
| `booking_api.py` | Rutterna `/api/bookings/locations`, `/location`, `/exams` och `/exams/{id}`; fel som 404 (saknat underlag) eller 422 (ogiltig begäran) med svensk text. |
| `booking_overview.py` | Översikt över bokningar för en dag eller period per adress och sal, utan körning: tentamina räknas en gång i totalen men i varje lokal de använder, bokningar som bara anger adress ligger kvar under sin adress som "sal ej angiven" (aldrig hänförda till en sal), bokningar utan adress är en egen rad, avbokade räknas för sig. Bokad tid, bokade platser och verklig närvaro (okänd) hålls isär. |
| `booking_compare.py` | Jämför en bokad tentamens ursprungliga bokning med dess placering i en sparad körning, via den provisoriska kopplingen bokning–Ladok-aktivitet–körningens tentamen: ursprunglig och simulerad tid, bokade och simulerade adresser och salar. Saknad koppling (`no_link`) och tentamen utanför körningen (`not_in_run`) redovisas, inget gissas. Salar jämförs bara när alla bokade lokaler har salnamn. |
| `booking_quality/` | Fristående datakvalitets- och klassificeringslager för bokningar (påverkar inte optimeringsmotorn). Beskriver varje bokningsrad längs fyra oberoende dimensioner: resursidentifiering, datakvalitet (flaggor), källtäckning (Ladok-fönster härlett ur data) och kopplingssäkerhet. Overifierade regler klassificerar inget; de ger bara kandidatnoteringar. `config.py` läser och validerar konfigurationen, `classify.py` klassificerar, `report.py` sammanställer en rapport, `__main__.py` ger `python -m tentaoptimering.booking_quality`. |
| `joint_strategy/` | Lösningsstrategin `decomposed`: `aggregate.py` (relaxation utan salstilldelning som väljer datum, lokalportfölj och pool och ger en giltig undre kostnadsgräns), `subproblems.py` (exakt kontroll av dagar och dagblock med den oförändrade gemensamma modellen inom körningens deadline, minsta orsakande tentamensmängd), `verification.py` (`Checker` med cache och parallella, ordnade dagkontroller; kontroll av planer, reparation, snitt, övre gräns, historikbyte per länkad dagsgrupp, kostnad och pool), `resources.py` (gemensam trådbudget och minnesbudget, ordnad parallellkörning och avbrottstoken), `warm_start.py` (omkontroll av en tidigare placering mot den nya instansen, med redovisning av varför den accepteras eller avvisas), `batch_progress.py` (rapportering av en omgång dagkontroller, inklusive när varje kontroll startar, till en `ProgressSink`; bara observation) och `decomposed.py` (styrning av varven och resultat). |
| `joint_progress.py` | Insyn i en gemensam körning: trådsäker `ProgressSink` med löpnummer (`seq`) och tid (`t`) per händelse, valfri rad-för-rad-fil `joint_events.jsonl` i körningsmappen, händelsetyper (`phase`, `batch`, `day_started`, `day`, `incumbent`, `bound`, `warm_start`, `resources`, `finished`) och hjälpfunktioner. Händelserna är bara observationer: de påverkar aldrig lösaren och fel vid skrivning sväljs. |
| `joint_api.py` | Logiken bakom `/api/joint-runs` och `/api/runs/{run_id}/events`: lista scenarier (inbyggda och egna), parametrar och valmöjligheter (salar, tentamenstyper) per scenario, starta körning som bakgrundsjobb (med ändrade parametrar i en ögonblicksfil av scenariot), spara eget scenario, läsa händelser, avbryta, spela upp sparad körning, sammanfatta och jämföra körningar. |
| `joint_scenarios.py` | Scenarier som filer: inbyggda (`config/scenarios`) och egna i `joint_scenarios/` under appens datamapp, sammanslagning av parameterändringar till en ögonblicksfil (originalet ändras aldrig), sparande av eget scenario och scenariolistan. |
| `joint_toml.py` | Skriver ett gemensamt scenario tillbaka till TOML (citerade nycklar med punkt, listor av inline-tabeller). |
| `joint_parameters.py` | Parameterkatalogen så som gränssnittet visar den: sex grupper i fast ordning, ordning inom grupp, avancerade parametrar och nyttolasten för `GET /api/joint-runs/parameters`. |
| `parameter_validation.py` | `validate_overrides`: kontrollerar okända parametrar, `contract_only`, värdetyp, intervall, tillåtna val, bemanningstrappans stigande ordning och datum/tid mot katalogen; svarar med `{id, message}` på svenska. |
| `joint_precheck.py`, `joint_precheck_api.py` | Förkontroll före körning: bygger problemet som en körning, räknar tentor utan tillåtet tillfälle och tentor som måste flyttas, och låter lösaren försöka bevisa omöjlighet i högst 20 s. Sparar ingenting. |
| `joint_diagnosis.py` | Utredning av en körning utan lösning: vad körningen ändrade jämfört med sitt scenario, och prov (utgångsscenariot, sedan en ändring i taget, högst 30 s) som visar vilken ändring som bevisat gör problemet omöjligt. Sparas som `joint_diagnosis.json`. |
| `joint_diagnosis_api.py` | Rutterna `GET/POST /api/joint-runs/{run_id}/diagnosis`. |
| `joint_savings.py` | Besparingspotential: bygger referensoptimeringen med låsta datum (tidigare referensen med låsta datum: scenariot utan flyttbara tentor; inte den faktiska bokningen A), löser och sparar det under `baselines/`, och räknar potentialen (referensen med låsta datum minus körning) med intervall och kostnadsposter. |
| `joint_savings_api.py` | Rutterna `GET/POST /api/joint-runs/{run_id}/savings`. |
| `joint_summary.py` | Sammanfattning av en sparad körning ur dess artefakter: kostnad, undre gräns, gap, flyttade tentor, tre domar, scenario, starttid och antal ändrade parametrar. |
| `joint_compare.py` | Jämförelse mellan två sparade körningar: parameterändringar, nyckeltal, osäkerhet (största gapet) och en klartextbedömning; jämför aldrig körningar med olika dataunderlag eller tentamängd. |
| `joint_warm_start.py` | Tidigare sparade körningar som startpunkt: val av körning (`auto`, `none` eller körnings-id), kontroll av filernas integritet och ny oberoende teknisk eftervalidering, samt beslutsfilen `joint_warm_start.json` i den nya körningen. Placeringen kontrolleras alltid mot de nya reglerna av lösaren. |
| `joint_validation/` | Fristående eftervalidering av gemensamma körningar. Läser bara sparade `joint_input.json`, `joint_result.json` och `joint_manifest.json`; delar ingen regel-, bemannings- eller kostnadskod med optimeraren. `context.py` (rå JSON-vy), `derive.py` (egen bemanningstrappa, salstillfällen, tidslinje, betalda pass, kostnad), `rules_placement.py` (behov, kalender), `rules_rooms.py`, `rules_staffing_cost.py`, `rules_resources.py` (fasta bokningar, betald tid, resursdatans ursprung), `rules_business.py` (verksamhetsgrund), `integrity.py` (hashar, versioner), `report.py` (regelstatus, sammanfattning, rapport), `run.py` (körning och skrivning av `joint_validation.json/.md`). |
| `parameter_catalog.py` | Läser och fryser den gemensamma parameterkatalogen och bevarar explicit motorstöd och tillåtna val. |
| `api.py` | FastAPI-lager: hälsa, inställningar, jobb, `/api/joint-runs/*`, händelser och varmstart för sparade körningar samt statisk frontend. |
| `app_paths.py` | Resurs- och användarskrivbara sökvägar för utveckling och paketerad applikation. |
| `underlay_api.py` | Rutterna för sidan Underlag: `/api/preparation` (tillstånd, senaste jobb, start), `/api/source-check` och `/api/settings/choose-source-directory`. |
| `underlay_manifest.py` | Underlagets manifest (`underlay.json`), tillstånd (aktuellt, föråldrat, ofullständigt, ospårat, saknas) och stegen i förberedelsen. |
| `underlay_prepare.py` | Atomär förberedelse: bygger i en tillfällig katalog, byter in resultatet först när det är komplett, och rapporterar steg. |
| `underlay_sources.py` | Förhandskontroll av källkatalogen: vilka förväntade filer som finns, med storlek och ändringstid. |
| `directory_picker.py` | Windows mappväljare (tkinter) som öppnas i den lokala processen. |
| `app_storage.py` | Appens användarskrivbara tillstånd: inställningar (skrivs atomärt), körningsmapp med validerade körnings-id, varmstartsuppgifter och katalogerna för underlag, rapporter och ögonblicksfiler. |
| `desktop.py` | Windowsstartpunkt som startar localhost-server och öppnar standardwebbläsaren. |
| `job_manager.py` | Enkeltrådig lokal jobbkö som hindrar samtidiga resultatskrivningar; ett jobb kan bära en avbrottstoken och en händelsesink. |
| `linkage.py` | Kandidatdiagnostik mellan bokningsplaceringar och Ladok; gör inga verifierade kopplingar. |
| `loaders.py` | Läsning och schemakontroll av de tre Excelkällorna. |
| `model_inputs.py` | Bygger provisoriska bokningshändelser, kandidatrelationer, rumsinventering och optimeringsinmatningar. |
| `normalize.py` | Normalisering av text, datum, tal och tekniska nycklar. |
| `paths.py` | Reporot (hittas via `config/data_preparation.toml`), standardkällmapp och validering av källfilernas existens. |
| `pipeline.py` | Orkestrerar inläsning, normalisering, diagnostik, CSV-utdata och rapportering. |
| `provenance.py` | Skapar ett deterministiskt körmanifest med SHA-256 och radantal för in- och utdata. |
| `reporting.py` | Skriver baslinje-, kvalitets- och kandidatkopplingsrapporter. |
| `validation.py` | Beräknar kvalitetsmått och kvalitetsfynd per datakälla. |

## Tester och utvecklingsverktyg

| Fil | Ansvar |
|---|---|
| `tests/test_cli.py` | Säkrar JSON som standard, statuskontraktet, maskinläsbara fel, att `optimize-joint` och `validate-joint-run` kräver sina argument och att den borttagna motorns kommandon inte finns. |
| `tests/test_canonical_demand.py` | Säkrar scope-täckning och att flera källaktiviteter kan bilda ett tentamensbehov utan dubbelräkning. |
| `tests/test_file_policy.py` | Säkrar filstorlekströsklarna och att ingen Python-fil passerat den obligatoriska delningsgränsen. |
| `tests/test_documentation.py` | Säkrar att kanoniska dokument finns, att pensionerade dokument inte återinförs, att historik är märkt och att lokala Markdown-länkar fungerar. |
| `tests/test_joint_optimization_effects.py` | Handräknade optimeringsresultat per parameter (kostnad och utfall på tvåtentafall), tolkning av sammanslagna digitala värden och att solverparametrar når CP-SAT. |
| `tests/test_joint_parameter_effects.py` | Effekttest för varje implementerad parameter, spårning mot gamla registret, startider och referenstillfälle, digital grund och samtentor. |
| `tests/joint_validation_cases.py` | Delade handräknade referensfall och skrivning av sparade körningar för valideraren. |
| `tests/test_joint_validation.py` | Referensfall, 34 injicerade fel, gränsfall, bevis kontra brott, integritet och AST-test av oberoende. |
| `tests/test_joint_validation_run.py` | Körflöde, CLI, oförändrade lösningsartefakter och regression mot den verkliga 12-tentakörningen. |
| `tests/test_joint_validation_differential.py` | 40 slumpade småfall där optimerarens resultat måste godkännas av valideraren. |
| `tests/test_joint_strategy.py` | Relaxationen är en undre gräns och den nedbrutna strategin når samma optimum som den monolitiska modellen på slumpade och handräknade fall, även när snitt behövs; resultaten passerar eftervalideringen; gapbegränsade resultat redovisas aldrig som bevisade. |
| `tests/test_joint_parallel_checks.py` | Parallella dagkontroller: gemensam trådbudget och minnesgräns, resultatet oberoende av vilken kontroll som avslutas först, samma optimum som sekventiell och monolitisk körning, tidsbudget, avbrott och fel. |
| `tests/test_joint_review_fixes.py` | Granskningens fynd: misslyckad slutlagring avslutar loggen som misslyckad, felmeddelande som text och verklig förbrukad tid, sammanfattning som valideras på nytt utan kostnad för ej verifierad körning, och jämförelse som inte visar kostnadsskillnad vid ändrade antaganden. |
| `tests/test_joint_contract_snapshots.py` | Delat kontrakt mellan backend och frontend: svarens form jämförs mot ögonblicksbilderna i `frontend/src/lib/testing/contract/`. Förnyas med `UPDATE_CONTRACT=1`. |
| `tests/test_joint_staffing_ladder.py` | Handräknat test av en bemanningstrappa med minst två vakter (underlagets trappa, ett preliminärt värde): steg per sal, gränsen 250, delad tenta och att en sal aldrig rymmer mer än trappans högsta gräns. |
| `tests/test_joint_cancel_regressions.py` | Avbrott: ostartad lösare läses aldrig, ett avbrutet dagbeslut är `unknown` och aldrig ogenomförbart, och den monolitiska strategin stoppar i båda faserna och bevarar en verifierad lösning men aldrig en ofullständig. |
| `tests/test_joint_warm_start.py` | Varmstart: accepteras och avvisas med redovisade skäl, kostnaden räknas om med de nya priserna, sparad verifieringsstatus godtas aldrig, körningsval via sparade artefakter och CLI. |
| `tests/test_joint_progress.py` | Händelseström: trådsäker ordning, fil per rad, svalda fel, identiskt lösarresultat med och utan sink, händelser för faser/dagkontroller/lösningar/gränser/varmstart, samt samma artefakter plus `joint_events.jsonl`. |
| `tests/test_joint_precheck.py` | Förkontrollen: går att köra, tentor utan tillåtet tillfälle, felaktigt värde nekas per parameter, inget sparas. |
| `tests/test_joint_diagnosis.py` | Ändringar jämfört med scenariot, att ett prov tillämpar exakt en ändring, att bara bevisad omöjlighet räknas som orsak och att en avbruten utredning sparas som ofullständig. |
| `tests/test_joint_savings.py` | Referensen med låsta datum flyttar ingen tentamen och rör inte scenariot, återanvänds bara för samma scenario och underlag, potentialen och dess intervall, och att körning eller Referensen med låsta datum utan verifierad lösning inte ger någon besparing. |
| `tests/wish_cases.py` | Testdata för önskemål: en `exam_wishes.csv` till syntetiska underlag. |
| `tests/test_wishes.py` | Önskemålsraderna, rang för bokat datum, status utan tolkning, motstridiga önskemål och en oberoende räkning mot verkliga data. |
| `tests/test_joint_wishes.py` | Önskemålen styr kalendern och avgörandet vid lika kostnad (handräknat), orsakar inget dyrare resultat, vägrar köra utan önskemål och godkänns/underkänns av den oberoende valideringen. |
| `tests/test_abc_actual.py` | A återger bokningen som den är, utan optimering: flera salar, sal utanför registret, bara adress, avbokad, önskemålsrang och att modulen inte använder optimeraren. |
| `tests/test_abc_runs.py` | B och C: sparas med namn, typ och värden; en sparad körning ändras inte av nästa; körningar kan köras om och användas som utgångspunkt; jämförelse mot A och mellan körningar; äldre underlag och körning utan lösning; rutterna över HTTP. |
| `tests/test_joint_api.py` | Gemensamma körningar via API-lagret: start, händelser med `after`, avbrott (fullständigt verifierat resultat eller inget), uppspelning, sammanfattning, id-validering och rutter över HTTP. |
| `tests/test_joint_period.py` | Periodval på syntetiskt underlag: täckning, dag och vecka, period utanför eller delvis utanför underlaget, tomma och omvända perioder, scenario med namngivna tentor, oförändrat originalscenario och unika körnings-id inom samma sekund. |
| `tests/test_joint_period_run.py` | Körning för en dag och en vecka mot det riktiga underlaget genom ordinarie API, motor och eftervalidering (kräver `data/processed`): antal tentor mot oberoende räkning, märkning som explorativ, ojämförbara perioder, avvisad period utanför underlaget. |
| `tests/test_joint_options.py` | Val av salar och tentamenstyper: salar och typer med rätt antal på syntetiskt underlag, tomt underlag, okänd sal (422 på båda rutterna och `ValueError` i dataadaptern), oförändrat beteende för giltiga val, id-validering och, om data finns, antal mot pandas för hela terminen. |
| `tests/test_booking_views.py` | Bokningsvyerna på syntetiska rader med exakta förväntningar (överlapp, avbokade, bara adress, saknad kapacitet, period utanför underlaget, tvetydig Ladok-koppling), HTTP-rutterna och, om data finns, antal mot oberoende pandas-räkning. |
| `tests/test_booking_overview_compare.py` | Översikt och jämförelse på syntetiska bokningar och en handgjord körning: dubbelräkning av tentamina över flera salar, bokningar utan sal och utan adress, avbokade, adresslistan, `no_link`/`not_in_run`/`compared`, plus oberoende pandas-räkning mot riktiga data. |
| `tests/test_booking_quality.py` | Datakvalitetslagret på syntetiska uttag (S-A–S-F): fullständiga, adressnivådeklarerade, blandade och bristfälliga data, de fyra dimensionernas oberoende, verifierade regler utan kodändring, kolumnbyte, konfigurationsvalidering och rapporten, samt oberoende räkning mot riktiga data. |
| `tests/test_joint_parameters.py` | Valparametrarnas val (och att motorn godtar dem), validering av varje värdetyp, parametrarnas gruppordning och nyttolast, scenariofilers rundresa i TOML samt regelurvalet (syntetiskt och, om data finns, hela terminen). |
| `tests/test_joint_scenarios_api.py` | Scenariolista, sparade egna scenarier, körning med ändrade parametrar via ögonblicksfil (originalet orört, samma resultat som ändrad fil), jämförelse mellan körningar (parameterdiff, osäkerhet, föregående körning, olika data), `day_started`-händelser och rutterna över HTTP. |
| `tests/test_joint_optimizer.py` | Handräknade referensfall för kostnadsavvägning, full täckning, samtentor, digitalt krav, kurskrock, ställtid och kontraktsrundresa. |
| `tests/test_joint_paid_time.py` | Betald personaltid och fasta bokningar med handräknade svar: pass, kortaste pass, restid, fler betalda timmar när lokalbesparingen är större, spärrade salar, ställtid och oanvänd men bokad sal; monolitisk och dekomponerad strategi och den oberoende valideraren. |
| `tests/test_joint_paid_time_differential.py` | 30 slumpade problem med betald tid, restid, externhyra och fasta bokningar: optimerare, `joint_pricing` och validerare överens, och båda strategierna når samma optimum. |
| `tests/test_resource_data.py` | Resurspaketets kontrakt (ursprung, felaktiga paket nekas), hur paketet prissätter salar och personal i en körning, bortvalda salar, frysning och reservationsbyggaren på syntetiska bokningar. |
| `tests/test_abc_explain.py` | Förklarad skillnad med handräknade fall: poster som summerar till totalen, namngivna salar, undviken extern bokning, färre och fler betalda timmar, villkorad besparing, utnyttjande mot priser, spärrade jämförelser, A prissatt med körningens regler. |
| `tests/test_explained_saving_chain.py` | Hela kedjan på riktiga filer: resursdata och bokningar in, körningar, oberoende validering och förklarad jämförelse (A mot C, C mot C med spärrande bokningar, bortvald sal, ändrade priser, körning utan lösning). |
| `tests/test_parameter_catalog.py` | Säkrar att alla parametrar exponeras och att motorstöd samt frusna experimentvärden är explicita. |
| `tests/test_api.py` | Säkrar hälsa, inställningar, krav på källkatalog före förberedelse, att den borttagna motorns rutter inte finns och att osäkra körnings-id avvisas. |
| `tests/test_underlay.py` | Förhandskontroll, manifest och tillstånd (aktuellt/föråldrat/ofullständigt/ospårat), atomär förberedelse (fel lämnar gamla underlaget orört) samt rutterna över HTTP. |
| `tests/test_app_storage.py` | Säkrar katalogerna, inställningarna och att körnings-id inte kan peka utanför körningsmappen. |
| `tests/test_linkage.py` | Säkrar kurskodsextraktion och att kandidatmatchningens tvetydighet bevaras. |
| `tests/test_model_inputs.py` | Säkrar kandidatrelationer, flera placeringar per efterfrågepost och behandling av saknat efterfrågevärde. |
| `tests/test_normalize.py` | Säkrar central textnormalisering och synliggör blandat bokningskorn. |
| `tools/inventory.py` | Utvecklingsverktyg: importgraf, nåbarhet, oreferererade symboler, API-rutter, CLI-kommandon och frontendfiler. |
| `tools/check_code_file_lengths.py` | Fristående kontroll: mål 500 rader, stark varning vid 800 och fel vid 1 000 rader. |
| `tools/check_documentation.py` | Fristående regressionskontroll för dokumentationsstruktur, historikmärkning, pensionerade filer och lokala Markdown-länkar. |
| `tools/measure_period_runs.py` | Mäter dag, vecka, månad och hela underlaget genom samma API och motor som gränssnittet (tid till första verifierade lösning och total körtid) i en tillfällig lagringsmapp. |

## Frontend: vyer för gemensam körning

| Fil | Ansvar |
|---|---|
| `frontend/src/App.tsx` | Tunn skal med sidorna Optimering (startsida) och Underlag. Båda hålls monterade så att en pågående körning eller förberedelse inte tappas vid sidbyte. |
| `frontend/src/components/abc/abc-page.tsx`, `compare-view.tsx` | Fliken A, B, C och jämförelse: de tre alternativen, körningshistoriken, hur komplett önskemålen är och jämförelsen av två valfria alternativ. |
| `frontend/src/lib/abcTypes.ts`, `abcApi.ts`, `abcView.ts`, `abcView.test.ts` | Typer, anrop mot `/api/abc/*` och rena funktioner (testade): körnings-id som utgångspunkt, utfall i klartext, kostnadssidor per sort och beläggningsserie. |
| `frontend/src/components/abc/explained-savings.tsx`, `explained-detail.tsx` | Den förklarade skillnaden i jämförelsen: total, förbehåll, kostnadsposter som fälls ut till lokaler, externa bokningar, personalpass och tentor, bedömning av realiserbarhet och de fyra kostnadsslagen. |
| `frontend/src/lib/abcExplainView.ts`, `abcExplainView.test.ts` | Rena funktioner (testade): tecken och timmar, rubrik utan ordet besparing, kontroll att posterna summerar, realiserbarhetstexter där bara observerade uppgifter är verifierade, tentor per kostnadspost. |
| `frontend/src/lib/jointTypes.ts` | TypeScript-typer för API-kontraktet `/api/joint-runs`: scenarier, parametrar, händelser, varmstartsbeslut, sammanfattning och jämförelse. |
| `frontend/src/lib/jointApi.ts` | Tunn typad API-klient med översättning av backendens sammanfattning (saknade domar blir `not_evaluated`, aldrig godkända). |
| `frontend/src/lib/jointState.ts` | Ren avledning av fasband, kostnadsserier, dagrutnät och gap ur händelselistan (samma kod för live och uppspelning). |
| `frontend/src/lib/jointFormat.ts` | Svenska etiketter och formatering; ärlig kostnadsredovisning (intervall utan bevisat optimum) och tolkning av domar. |
| `frontend/src/lib/jointCompare.ts` | Vymodell för parameterändringar mellan två körningar (används av jämförelsen), utan beräknade skillnader när körningarna inte är jämförbara. |
| `frontend/src/lib/jointScenarioInfo.ts` | Urval i klartext och uppgift om körtid för scenariot. |
| `frontend/src/lib/jointJobMemory.ts` | Minne för pågående körning så att den återupptas efter omladdning. |
| `frontend/src/lib/runClock.ts` | Körningens klocka: serverns förbrukade tid plus lokal klocka mellan svaren, och visningen går aldrig bakåt. |
| `frontend/src/lib/jointEvents.ts`, `jointKinds.ts`, `jointSteps.ts` | Händelser, svenska rubriker och förklaringar per kontrolltyp (även "Går inte"-texter) och körningens steg i klartext. |
| `frontend/src/lib/jointTimeline.ts`, `jointTimelineDetail.ts`, `jointTimelineSummary.ts` | Vymodell för tidslinjen: varv, segment, bredder, pågående segment, detaljer och sammanfattningsrad i klartext. |
| `frontend/src/lib/jointSummaryView.ts` | Vymodell för sammanfattningen: ingen kostnad utan verifierad lösning, ändrade parametrar med etiketter. |
| `frontend/src/lib/useJointJob.ts` | React-hook för start, polling var sekund, stopp och återupptagning av pågående jobb. |
| `frontend/src/lib/paramUnits.ts` | Enheter och omräkning mellan kronor i vyn och öre i API:et. |
| `frontend/src/lib/paramValues.ts` | Utkast, tolkning och lokal validering av parametervärden, inklusive bemanningstrappan. |
| `frontend/src/lib/paramFormat.ts` | Parametervärden i klartext. |
| `frontend/src/lib/paramDiff.ts` | Ändringar jämfört med scenariot, grupper, filter och serverfel per parameter. |
| `frontend/src/lib/useParameterEditor.ts` | Hook för parameterredigering: utkast, ändringslista, återställning och serverfel. |
| `frontend/src/lib/runOptions.ts` | Val av start från förra körningen och datorresurser. |
| `frontend/src/lib/dates.ts` | Datumräkning i UTC (giltigt datum, addera dagar, dagar emellan, veckodag). |
| `frontend/src/lib/bookingTypes.ts` | Typer för svaren från bokningsrutterna. |
| `frontend/src/lib/bookingApi.ts` | Anrop till `/api/bookings/*`. |
| `frontend/src/lib/bookingView.ts` | Rena funktioner för lokalvyn: tidslinjens skala och staplar (överlapp i egna rader), gruppering per dag, intervallsteg och mått med definitioner. |
| `frontend/src/lib/useBookings.ts` | Hämtar lokaler, en lokals bokningar, sökträffar och en tentamen. |
| `frontend/src/components/rooms/rooms-page.tsx` | Sidan Lokaler: välj lokal och datumintervall, mått, tidslinje och bokningstabell. |
| `frontend/src/components/rooms/day-timeline.tsx` | Tidslinje per dag; avbokade bokningar streckade, dagar utan bokning visas inte som lediga. |
| `frontend/src/components/rooms/exam-panel.tsx` | Sök och visa en bokad tentamen med alla salar och tider samt märkning av osäker Ladok-koppling. |
| `frontend/src/components/rooms/overview-view.tsx` | Vyn Dag eller period per adress: datum, adressval, mått, tabell per adress och sal, tidslinje för vald adress och tentamenslista. |
| `frontend/src/components/rooms/findings.tsx` | Visar fynd i datat (räkningar från datakvalitetslagret) och rader som liknar overifierade mönster, utan att förklara varför uppgifter saknas. |
| `frontend/src/components/rooms/compare-panel.tsx` | Jämförelse mellan den ursprungliga bokningen och placeringen i en vald körning, med märkning av provisorisk koppling. |
| `frontend/src/lib/bookingView.test.ts` | Test av datum, tidslinje, intervall och mått (verklig närvaro okänd, aldrig noll). |
| `frontend/src/lib/period.ts` | Planeringsperiod: genvägar (dag, vecka, månad, hela underlaget), kontroll av valet och texter om täckning och kontroll. |
| `frontend/src/lib/usePeriod.ts` | Hämtar underlagets täckning och serverns kontroll av vald period. |
| `frontend/src/components/joint/savings-card.tsx` | Besparingspotentialen överst i resultatet: belopp, jämförelse mot referensoptimeringen med låsta datum, intervall och kostnadsposter; knapp som beräknar referensen. |
| `frontend/src/lib/savingsApi.ts`, `savingsView.ts`, `useSavings.ts` | Anrop, rubriktexter (testade) och hook som följer jobbet för referensen med låsta datum. |
| `frontend/src/components/joint/scenario-facts.tsx`, `params/params-section.tsx` | Raden med det som körs (en gång per uppgift) och parametersektionen med de vanligaste parametrarna överst och resten hopfällt. |
| `frontend/src/lib/featuredParams.ts`, `scenarioFacts.ts`, `useUnderlayInfo.ts` | Vilka parametrar som visas överst, uppgifterna om det som körs (testade) och underlagets datum. |
| `frontend/src/components/joint/diagnosis-card.tsx`, `constraint-list.tsx` | "Vad gick fel?" för en körning utan lösning och hopfälld lista för en med: begränsningarna som gällde (ditt val markerat), utredningsknapp, förlopp och slutsats. |
| `frontend/src/components/joint/precheck-result.tsx`, `lib/precheckApi.ts`, `precheckView.ts`, `usePrecheck.ts` | Förkontrollen på startfliken: knapp, utfall och hook (utfallet försvinner när inställningarna ändras). |
| `frontend/src/components/ui/info-tip.tsx`, `notice.tsx` | ⓘ-ikon som visar en förklaring vid klick, och varning/fel med hopfällda detaljer. |
| `frontend/src/lib/diagnosisApi.ts`, `diagnosisView.ts`, `useDiagnosis.ts` | Anrop, namn och slutsats i klartext (testade) samt hook som följer utredningsjobbet, även efter omladdning. |
| `frontend/src/components/joint/period-picker.tsx` | Periodval i gränssnittet: datum, genvägar, täckning, kontrollresultat och märkningen som explorativ planering. |
| `frontend/src/lib/underlay.ts`, `underlayApi.ts`, `useUnderlay.ts` | Underlag: texter och format, anrop mot `/api/settings`, `/api/preparation`, `/api/source-check` och mappväljaren, samt hook som följer serverns jobb (även efter omladdning) och förhandskontrollerar sökvägen. |
| `frontend/src/lib/testing/jointFixture.ts`, `paramFixture.ts` | Syntetiska händelser och parametrar som bara används av testerna. Appkod får aldrig importera dem. |
| `frontend/src/lib/testing/contract/*.json` | Riktiga API-svar (sammanfattning, jämförelse, händelser, valmöjligheter) som ögonblicksbilder av kontraktet. `tests/test_joint_contract_snapshots.py` jämför deras form mot backend och `jointContract.test.ts` matar dem genom klientens adaptrar. |
| `frontend/src/lib/*.test.ts` | Tester (`npm test`, endast Node): kontraktsform, tillståndsavledning, ärliga texter, parametervalidering och enhetsomräkning, ändringsberäkning, jämförelse, körval, underlag och en gränskontroll som fäller bygget om appkod importerar testdata eller anropar borttagna rutter. |
| `frontend/src/components/joint/joint-page.tsx` | Sidan Optimering med flikarna A, B, C och jämförelse, Ställ in och kör och Resultat. |
| `frontend/src/components/joint/scenario-picker.tsx`, `start-panel.tsx`, `run-options.tsx`, `save-scenario.tsx` | Val av scenario med urval i klartext, startpanel med Kör, start från förra körningen med datorresurser, och sparande av ändringarna som nytt scenario. |
| `frontend/src/components/joint/params/` | Parameterredigeringen: lista per grupp, rad med enhet, hjälptext och återställning, inmatning per typ, listor, bemanningstrappa och fältet med antalet ändringar. |
| `frontend/src/components/joint/live-run.tsx`, `run-panels.tsx`, `cost-panel.tsx`, `day-grid.tsx`, `resource-box.tsx` | Pågående körning överst i Resultat: status och stopp, kostnadsgraf, dagrutnät med verkligt "pågår" och resursruta; besked när en körning inte gav något resultat. |
| `frontend/src/lib/runLabel.ts` | Körningens namn för användaren: scenario och klockslag. |
| `frontend/src/components/joint/run-timeline.tsx`, `timeline-detail.tsx`, `timeline-look.tsx` | Tidslinje över det som körs: ett block per varv med segment efter körordning, bredd efter tid, pulserande pågående segment och detaljer per segment. Används i livevy, resultat och förlopp i efterhand. |
| `frontend/src/components/joint/result-view.tsx`, `summary-card.tsx`, `verdict-cards.tsx`, `warm-start-card.tsx`, `how-to-read.tsx`, `replay.tsx`, `status-chip.tsx` | Resultatvy: sammanfattning, länk till jämförelsen med A, B eller en annan körning, de tre domarna isär, beslut om start från förra körningen, förklaring av hur resultatet läses och uppspelning av en avslutad körning. |
| `frontend/src/components/joint/underlay-notice.tsx` | Ruta när underlaget saknas, med knapp till sidan Underlag. |
| `frontend/src/components/underlay/` | Sidan Underlag: källdatakatalog med Bläddra och filkontroll, förberedelse med steg och tillstånd, och sammanfattning ur manifestet. |

## Rapporter och genererade filer

| Fil eller katalog | Ansvar |
|---|---|
| `reports/baseline.md` | Granskningsbar sammanfattning av baslinjens mått och kvalitetsfynd. |
| `reports/data_quality.json` | Maskinläsbar version av datakvalitetsresultatet. |
| `reports/candidate_linkage.md` | Granskningsbar sammanfattning av kandidatdiagnostiken mellan bokningar och Ladok. |
| `reports/candidate_linkage.json` | Maskinläsbara mått från kandidatdiagnostiken. |
| `reports/optimization_readiness.md` | Kort rapport om vad underlaget kan användas till och vilka spärrar som återstår. |
| `reports/optimization_readiness.json` | Maskinläsbara mått om täckning och beredskap för explorativa PoC-körningar. |
| `reports/run_manifest.json` | Deterministiska källhashar, konfigurationshash och radantal/hashar för genererade CSV-filer. |
| `data/processed/bookings.csv` | Reproducerbar normaliserad tabell för bokningsplaceringar; inte versionshanterad. |
| `data/processed/ladok_activities.csv` | Reproducerbar normaliserad Ladoktabell; inte versionshanterad. |
| `data/processed/lease_rows.csv` | Reproducerbar normaliserad lokal- och kostnadstabell; inte versionshanterad. |
| `data/processed/candidate_linkage.csv` | Reproducerbar radnivå för kandidatdiagnostiken; inte versionshanterad. |
| `data/processed/exam_events.csv` | Reproducerbara provisoriska bokningshändelser; inte versionshanterad. |
| `data/processed/activity_booking_candidates.csv` | Reproducerbara Ladok–bokningskandidater; inte versionshanterad. |
| `data/processed/room_inventory.csv` | Reproducerbar observerad rumsinventering utan antagna kapaciteter; inte versionshanterad. |
| `data/processed/optimization_rooms.csv` | Reproducerbart, uttryckligen provisoriskt salunderlag för explorativ kapacitets-PoC; inte versionshanterat. |
| `data/processed/optimization_demands.csv` | Reproducerbara provisoriska efterfrågeposter; inte versionshanterad. |
| `data/processed/optimization_placements.csv` | Reproducerbara länkar från efterfrågeposter till historiska placeringar; inte versionshanterad. |
| `data/processed/demand_scope.csv` | Reproducerbar aktivitetsspecifik scope-rapport med status, orsak och evidens; inte versionshanterad. |
| `reports/demand_scope.md` och `reports/demand_scope.json` | Granskningsbar respektive maskinläsbar sammanfattning av scope-besluten. |
| `runs/<run-id>/` | Lokalt återskapbara optimeringsresultat med konfiguration, manifest, JSON, CSV och rapport; inte versionshanterade. |
| `runs/comparisons/` | Lokala maskin- och människoläsbara jämförelser mellan körningar; inte versionshanterade. |

`.git`, `.venv`, `__pycache__` och paketets `*.egg-info` är lokala eller härledda och ingår inte i innehållsförteckningen. Originalkällorna ligger utanför repot i `C:\lokalt\tentalokaler\underlag` och är alltid read-only.
