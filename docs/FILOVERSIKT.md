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
| `Uppdrag_Claude_Codex_tentalokaler_PoC.md` | Ursprungligt avgränsat uppdrag för första leveransen. |
| `Slutsatser_tentalokaler_2026-10-06.md` | Dokumenterad krav- och datagenomgång samt rekommenderad fortsatt inriktning. |

## Konfiguration

| Fil | Ansvar |
|---|---|
| `config/data_preparation.toml` | Konfiguration för dataförberedelsen (`prepare`): efterfrågemått och de explicita PoC-antagandena om lokalbestånd. Ersätter det borttagna `config/parameters.toml`. |
| `config/joint_parameter_catalog.toml` | Gemensam v2-katalog för GUI, lagring, validering och ny motor, inklusive explicit motorstöd per parameter och tillåtna val (`choices`) för valparametrar. |
| `config/room_register.toml` | Versionsmärkt officiellt rumsreferenslager med publicerade kapaciteter, källadress och tidsmässig osäkerhet. |
| `config/source_files.toml` | Namn, blad och rubrikrad för de tre lästa källexporterna. |
| `config/scenarios/joint_real_subset.toml` | Reproducerbart avgränsat verkligt datafall för den nya gemensamma CP-SAT-kärnan. |
| `config/scenarios/joint_underlay_period.toml` | Hela vårterminen 2026 som bundet scenario (`joint_underlay_period_2026`): urvalet anges med regel (`selection = "all_ready"` med datumintervall) i stället för en id-lista, och ger samma 1 172 tentor som den frusna terminsinstansen. |

## Dokumentation

| Fil | Ansvar |
|---|---|
| `docs/BLOCKERANDE_DATAGAP.md` | Datagap som måste lösas före tillförlitlig optimering eller kronberäkning. |
| `docs/DATAMODELL.md` | Korn, nycklar och gränser mellan beställning, placering, Ladokaktivitet och lokalrad. |
| `docs/FILOVERSIKT.md` | Denna innehållsförteckning och filernas ansvar. |
| `docs/GEMENSAM_OPTIMERINGSDESIGN.md` | Teknisk specifikation för kanoniskt tentamensbehov, salstillfällen, integrerad bemanning och konsekvent årskostnad. |
| `docs/GEMENSAM_CP_SAT_FORSTA_LEVERANS.md` | Levererad modell, solverstatus, handräknade facit, verklig delmängdskörning och kvarstående begränsningar. |
| `docs/OBEROENDE_EFTERVALIDERING.md` | Valideringens design, regelkatalog, verkliga statusar för 12-tentakörningen, kvarstående datagap och hur den körs. |
| `docs/OPTIMERINGSSTRATEGI.md` | Analys av den monolitiska modellens beräkningskostnad, den rekommenderade strategin (aggregerad relaxation och daglig kontroll), mätningar på frysta verkliga instanser och kvarstående risker. |
| `docs/VERKSAMHETSPAVERKAN_2026-10-12.md` | Hur verksamhetsunderlaget 2 oktober påverkar modellen: period (Ladok slutar 31 mars), bemanningstrappa, tre pass, lokalbestånd och RPS, kostnadsbegrepp och Nuläge, med körda experiment. Inget preliminärt värde görs till verifierad regel. |
| `docs/ARKITEKTURPRINCIPER_DATAKVALITET.md` | Principer för att hålla verksamhetsmodell och datakvalitet isär: vad saknad sal är i dagens uttag (mätt), granskning av PR #13–15 mot principerna, föreslagen arkitektur med resurstillstånd och policy per planeringsläge, begränsade korrigeringar, testmatris och frågor till verksamhetsägaren. |
| `docs/KOSTNADSMODELL.md` | Avgränsning mellan resursbehov, intern kostnadsfördelning och realiserbar besparing. |
| `docs/OPTIMERINGSUNDERLAG.md` | Korn, relationsregler och tillåten användning av det maskinläsbara underlaget före motorbygge. |
| `docs/MALARKITEKTUR_ANALYS_2026-10-09.md` | Beslutsunderlag och leveransplan för omtaget (arkitektur, Nuläge, CP-SAT-restriktioner, steg, rensningsverifiering). Tillfälligt tills omtaget är genomfört. |
| `docs/PARAMETERKATALOG.md` | Utkast till den enda parameterkatalogen (endast parametrar som motorn läser) med grund och effektfall. |
| `docs/DOMANMODELL.md` | Utkast till domänmodellen: Dataunderlag, Simulering, Förutsättning, Körning, Resultat; lagring och jämförbarhet. |
| `docs/KAPACITETSFORTECKNING.md` | Varje funktion i dagens system med beslut (behåll, bygg om, ersätt, ta bort) och beroenden. |
| `docs/KRAVUPPFYLLNAD.md` | Kravmatris: status idag och efter första leveransen, bevis och datakrav. |
| `docs/DATAANALYS_S0.md` | Analys av population, delade tillfällen, `canonical_demand`, hemtentor, institution och kapacitetsavvikelser. |
| `docs/ANALYS_KOLLEKTIVAVTAL.md` | Analys av lokalt kollektivavtal för tentamenspersonal och vad som kan bli verifierat. |
| `docs/prototyp/index.html` | Fristående klickbar prototyp av användarflödet (ingen produktkod; uppmätta förprovsvärden). |
| `docs/LOKALT_GRANSSNITT.md` | Arkitektur, API-kontrakt, källkodsutveckling och offlineverifiering av Windowsdistributionen. |

## Python-paket: `src/tentaoptimering`

| Fil | Ansvar |
|---|---|
| `__init__.py` | Paketidentifiering och kort paketbeskrivning. |
| `cli.py` | JSON-först-kommandon: `prepare`, `status`, `resources`, `joint-parameters`, `optimize-joint` och `validate-joint-run`. |
| `canonical_demand.py` | Validerar fullständiga scope-beslut och explicita relationer från Ladokaktiviteter via delgrupper till unika tentamensbehov. |
| `joint_contract.py` | Versionsmärkt JSON-kontrakt för gemensamma modellindata och resultat, inklusive delgrupper, stödstatus, kostnader och solvergränser. |
| `joint_optimizer.py` | Ny CP-SAT-kärna som gemensamt optimerar kalenderpass, faktiska salar, bemanningspool och jämförbar kostnad utan partiell placering. |
| `joint_inputs.py` | Adapter (inklusive tolkning av tidsintervallet `HH:MM-HH:MM` till minuter) och körningslagring för det verkliga urvalet (namngivna tentor eller hela terminen enligt regel). Sparar den använda scenariofilen som `joint_scenario.toml` i körningsmappen. |
| `joint_selection.py` | Urval av tentor ur `[subset]`: antingen `exam_event_ids` eller regeln `selection = "all_ready"` med valfritt `date_from`/`date_to`; exakt ett av sätten, annars svenskt fel. |
| `joint_options.py` | Valmöjligheter för ett scenario (`GET /api/joint-runs/options`): salarna motorn kan överväga i planeringsområdet (samma urval som motorn bygger sina salar av) med läsbar etikett, byggnad, kapacitet och digitalt stöd, samt de observerade tentamenstyperna med antal tentor. Innehåller också kontrollen av `rooms.selection` (okänt sal-id är ett svenskt fel, aldrig tyst ignorerat). Saknas underlaget blir listorna tomma. |
| `joint_strategy/` | Lösningsstrategin `decomposed`: `aggregate.py` (relaxation utan salstilldelning som väljer datum, lokalportfölj och pool och ger en giltig undre kostnadsgräns), `subproblems.py` (exakt kontroll av dagar och dagblock med den oförändrade gemensamma modellen inom körningens deadline, minsta orsakande tentamensmängd), `verification.py` (`Checker` med cache och parallella, ordnade dagkontroller; kontroll av planer, reparation, snitt, övre gräns, historikbyte per länkad dagsgrupp, kostnad och pool), `resources.py` (gemensam trådbudget och minnesbudget, ordnad parallellkörning och avbrottstoken), `warm_start.py` (omkontroll av en tidigare placering mot den nya instansen, med redovisning av varför den accepteras eller avvisas), `batch_progress.py` (rapportering av en omgång dagkontroller, inklusive när varje kontroll startar, till en `ProgressSink`; bara observation) och `decomposed.py` (styrning av varven och resultat). |
| `joint_progress.py` | Insyn i en gemensam körning: trådsäker `ProgressSink` med löpnummer (`seq`) och tid (`t`) per händelse, valfri rad-för-rad-fil `joint_events.jsonl` i körningsmappen, händelsetyper (`phase`, `batch`, `day_started`, `day`, `incumbent`, `bound`, `warm_start`, `resources`, `finished`) och hjälpfunktioner. Händelserna är bara observationer: de påverkar aldrig lösaren och fel vid skrivning sväljs. |
| `joint_api.py` | Logiken bakom `/api/joint-runs` och `/api/runs/{run_id}/events`: lista scenarier (inbyggda och egna), parametrar och valmöjligheter (salar, tentamenstyper) per scenario, starta körning som bakgrundsjobb (med ändrade parametrar i en ögonblicksfil av scenariot), spara eget scenario, läsa händelser, avbryta, spela upp sparad körning, sammanfatta och jämföra körningar. |
| `joint_scenarios.py` | Scenarier som filer: inbyggda (`config/scenarios`) och egna i `joint_scenarios/` under appens datamapp, sammanslagning av parameterändringar till en ögonblicksfil (originalet ändras aldrig), sparande av eget scenario och scenariolistan. |
| `joint_toml.py` | Skriver ett gemensamt scenario tillbaka till TOML (citerade nycklar med punkt, listor av inline-tabeller). |
| `joint_parameters.py` | Parameterkatalogen så som gränssnittet visar den: sex grupper i fast ordning, ordning inom grupp, avancerade parametrar och nyttolasten för `GET /api/joint-runs/parameters`. |
| `parameter_validation.py` | `validate_overrides`: kontrollerar okända parametrar, `contract_only`, värdetyp, intervall, tillåtna val, bemanningstrappans stigande ordning och datum/tid mot katalogen; svarar med `{id, message}` på svenska. |
| `joint_summary.py` | Sammanfattning av en sparad körning ur dess artefakter: kostnad, undre gräns, gap, flyttade tentor, tre domar, scenario, starttid och antal ändrade parametrar. |
| `joint_compare.py` | Jämförelse mellan två sparade körningar: parameterändringar, nyckeltal, osäkerhet (största gapet) och en klartextbedömning; jämför aldrig körningar med olika dataunderlag eller tentamängd. |
| `joint_warm_start.py` | Tidigare sparade körningar som startpunkt: val av körning (`auto`, `none` eller körnings-id), kontroll av filernas integritet och ny oberoende teknisk eftervalidering, samt beslutsfilen `joint_warm_start.json` i den nya körningen. Placeringen kontrolleras alltid mot de nya reglerna av lösaren. |
| `joint_validation/` | Fristående eftervalidering av gemensamma körningar. Läser bara sparade `joint_input.json`, `joint_result.json` och `joint_manifest.json`; delar ingen regel-, bemannings- eller kostnadskod med optimeraren. `context.py` (rå JSON-vy), `derive.py` (egen bemanningstrappa, salstillfällen, tidslinje, kostnad), `rules_placement.py` (behov, kalender), `rules_rooms.py`, `rules_staffing_cost.py`, `rules_business.py` (verksamhetsgrund), `integrity.py` (hashar, versioner), `report.py` (regelstatus, sammanfattning, rapport), `run.py` (körning och skrivning av `joint_validation.json/.md`). |
| `parameter_catalog.py` | Läser och fryser den gemensamma parameterkatalogen och bevarar explicit motorstöd och tillåtna val. |
| `api.py` | FastAPI-lager: hälsa, inställningar, förberedelse, jobb, `/api/joint-runs/*`, händelser och varmstart för sparade körningar samt statisk frontend. |
| `app_paths.py` | Resurs- och användarskrivbara sökvägar för utveckling och paketerad applikation. |
| `app_storage.py` | Appens användarskrivbara tillstånd: inställningar, körningsmapp med validerade körnings-id, varmstartsuppgifter och katalogerna för underlag, rapporter och ögonblicksfiler. |
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
| `tests/test_joint_api.py` | Gemensamma körningar via API-lagret: start, händelser med `after`, avbrott (fullständigt verifierat resultat eller inget), uppspelning, sammanfattning, id-validering och rutter över HTTP. |
| `tests/test_joint_options.py` | Val av salar och tentamenstyper: salar och typer med rätt antal på syntetiskt underlag, tomt underlag, okänd sal (422 på båda rutterna och `ValueError` i dataadaptern), oförändrat beteende för giltiga val, id-validering och, om data finns, antal mot pandas för hela terminen. |
| `tests/test_joint_parameters.py` | Valparametrarnas val (och att motorn godtar dem), validering av varje värdetyp, parametrarnas gruppordning och nyttolast, scenariofilers rundresa i TOML samt regelurvalet (syntetiskt och, om data finns, hela terminen). |
| `tests/test_joint_scenarios_api.py` | Scenariolista, sparade egna scenarier, körning med ändrade parametrar via ögonblicksfil (originalet orört, samma resultat som ändrad fil), jämförelse mellan körningar (parameterdiff, osäkerhet, föregående körning, olika data), `day_started`-händelser och rutterna över HTTP. |
| `tests/test_joint_optimizer.py` | Handräknade referensfall för kostnadsavvägning, full täckning, samtentor, digitalt krav, kurskrock, ställtid och kontraktsrundresa. |
| `tests/test_parameter_catalog.py` | Säkrar att alla parametrar exponeras och att motorstöd samt frusna experimentvärden är explicita. |
| `tests/test_api.py` | Säkrar hälsa, inställningar, krav på källkatalog före förberedelse, att den borttagna motorns rutter inte finns och att osäkra körnings-id avvisas. |
| `tests/test_app_storage.py` | Säkrar katalogerna, inställningarna och att körnings-id inte kan peka utanför körningsmappen. |
| `tests/test_linkage.py` | Säkrar kurskodsextraktion och att kandidatmatchningens tvetydighet bevaras. |
| `tests/test_model_inputs.py` | Säkrar kandidatrelationer, flera placeringar per efterfrågepost och behandling av saknat efterfrågevärde. |
| `tests/test_normalize.py` | Säkrar central textnormalisering och synliggör blandat bokningskorn. |
| `tools/inventory.py` | Utvecklingsverktyg: importgraf, nåbarhet, oreferererade symboler, API-rutter, CLI-kommandon och frontendfiler. |
| `tools/check_code_file_lengths.py` | Fristående kontroll: mål 500 rader, stark varning vid 800 och fel vid 1 000 rader. |

## Frontend: vyer för gemensam körning

| Fil | Ansvar |
|---|---|
| `frontend/src/App.tsx` | Tunn skal med sidorna Optimering (startsida) och Underlag. Båda hålls monterade så att en pågående körning eller förberedelse inte tappas vid sidbyte. |
| `frontend/src/lib/jointTypes.ts` | TypeScript-typer för API-kontraktet `/api/joint-runs`: scenarier, parametrar, händelser, varmstartsbeslut, sammanfattning och jämförelse. |
| `frontend/src/lib/jointApi.ts` | Tunn typad API-klient med översättning av backendens sammanfattning (saknade domar blir `not_evaluated`, aldrig godkända). |
| `frontend/src/lib/jointState.ts` | Ren avledning av fasband, kostnadsserier, dagrutnät och gap ur händelselistan (samma kod för live och uppspelning). |
| `frontend/src/lib/jointFormat.ts` | Svenska etiketter och formatering; ärlig kostnadsredovisning (intervall utan bevisat optimum) och tolkning av domar. |
| `frontend/src/lib/jointCompare.ts` | Vymodell för jämförelsen mot föregående körning, utan beräknade skillnader när körningarna inte är jämförbara. |
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
| `frontend/src/lib/underlay.ts`, `underlayApi.ts`, `useUnderlay.ts` | Underlag: avgör om underlaget saknas, anrop mot `/api/settings`, `/api/preparation` och `/api/jobs/{id}`, samt hook med jobbpollning. |
| `frontend/src/lib/testing/jointFixture.ts`, `paramFixture.ts` | Syntetiska händelser och parametrar som bara används av testerna. Appkod får aldrig importera dem. |
| `frontend/src/lib/testing/contract/*.json` | Riktiga API-svar (sammanfattning, jämförelse, händelser, valmöjligheter) som ögonblicksbilder av kontraktet. `tests/test_joint_contract_snapshots.py` jämför deras form mot backend och `jointContract.test.ts` matar dem genom klientens adaptrar. |
| `frontend/src/lib/*.test.ts` | Tester (`npm test`, endast Node): kontraktsform, tillståndsavledning, ärliga texter, parametervalidering och enhetsomräkning, ändringsberäkning, jämförelse, körval, underlag och en gränskontroll som fäller bygget om appkod importerar testdata eller anropar borttagna rutter. |
| `frontend/src/components/joint/joint-page.tsx` | Sidan Optimering med flikarna Ställ in och kör, Körning och Resultat och jämförelse. |
| `frontend/src/components/joint/scenario-picker.tsx`, `start-panel.tsx`, `run-options.tsx`, `save-scenario.tsx` | Val av scenario med urval i klartext, startpanel med Kör, start från förra körningen med datorresurser, och sparande av ändringarna som nytt scenario. |
| `frontend/src/components/joint/params/` | Parameterredigeringen: lista per grupp, rad med enhet, hjälptext och återställning, inmatning per typ, listor, bemanningstrappa och fältet med antalet ändringar. |
| `frontend/src/components/joint/live-view.tsx`, `run-panels.tsx`, `cost-panel.tsx`, `day-grid.tsx`, `resource-box.tsx` | Livevy: status och stopp, kostnadsgraf, dagrutnät med verkligt "pågår" och resursruta. |
| `frontend/src/components/joint/run-timeline.tsx`, `timeline-detail.tsx`, `timeline-look.tsx` | Tidslinje över det som körs: ett block per varv med segment efter körordning, bredd efter tid, pulserande pågående segment och detaljer per segment. Används i livevy, resultat och förlopp i efterhand. |
| `frontend/src/components/joint/result-view.tsx`, `summary-card.tsx`, `compare-section.tsx`, `verdict-cards.tsx`, `warm-start-card.tsx`, `how-to-read.tsx`, `replay.tsx`, `status-chip.tsx` | Resultatvy: sammanfattning, jämförelse mot föregående körning, de tre domarna isär, beslut om start från förra körningen, förklaring av hur resultatet läses och uppspelning av en avslutad körning. |
| `frontend/src/components/joint/underlay-notice.tsx` | Ruta när underlaget saknas, med knapp till sidan Underlag. |
| `frontend/src/components/underlay/` | Sidan Underlag: val av källdatakatalog och förberedelse av underlaget. |

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
