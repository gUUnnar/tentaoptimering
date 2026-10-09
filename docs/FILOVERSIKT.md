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
| `config/parameters.toml` | Maskinläsbart register över verksamhetsparametrar utan förhandslåsta värden eller intervall. |
| `config/room_register.toml` | Versionsmärkt officiellt rumsreferenslager med publicerade kapaciteter, källadress och tidsmässig osäkerhet. |
| `config/source_files.toml` | Namn, blad och rubrikrad för de tre lästa källexporterna. |
| `config/scenarios/reference.toml` | Komplett referensscenario med fasta historiska datum och tider. |
| `config/scenarios/flexible_start_60m.toml` | Tekniskt jämförelsescenario med ±60 minuters startflexibilitet. |
| `config/scenarios/integrated_term_exploratory.toml` | Versionshanterad explorativ terminskalender, kostnadsproxyer, bemanningsregel och fullständigt spårbara antaganden. |

## Dokumentation

| Fil | Ansvar |
|---|---|
| `docs/BLOCKERANDE_DATAGAP.md` | Datagap som måste lösas före tillförlitlig optimering eller kronberäkning. |
| `docs/DATAMODELL.md` | Korn, nycklar och gränser mellan beställning, placering, Ladokaktivitet och lokalrad. |
| `docs/FILOVERSIKT.md` | Denna innehållsförteckning och filernas ansvar. |
| `docs/GEMENSAM_OPTIMERINGSDESIGN.md` | Teknisk specifikation för kanoniskt tentamensbehov, salstillfällen, integrerad bemanning och konsekvent årskostnad. |
| `docs/FORSTA_TERMSKORNING.md` | Reproducerbar redovisning av första explorativa fullskalekörningen, täckning, kostnadsproxyer och begränsningar. |
| `docs/KOSTNADSMODELL.md` | Avgränsning mellan resursbehov, intern kostnadsfördelning och realiserbar besparing. |
| `docs/OPTIMERINGSUNDERLAG.md` | Korn, relationsregler och tillåten användning av det maskinläsbara underlaget före motorbygge. |
| `docs/OPTIMERINGSMOTOR.md` | CP-SAT-modell, scenarier, mål, validering, CLI-kontrakt och resultattolkning. |
| `docs/OBEROENDE_EFTERVALIDERING.md` | Regelvis och fristående kontroll av en sparad terminskörning samt betydelsen av de två statusmåtten. |
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
| `cli.py` | JSON-först-kommandon för förberedelse, resurser, parametrar, optimering, eftervalidering, resultat och jämförelse. |
| `canonical_demand.py` | Validerar fullständiga scope-beslut och explicita relationer från Ladokaktiviteter via delgrupper till unika tentamensbehov. |
| `integrated_term.py` | Första CP-SAT-modellen för full täckning över terminskalendern med salstillfällen, lokalportfölj och anonym samtidig bemanning. |
| `integrated_config.py` | Läser och validerar det integrerade terminscenariots kalender, ekonomi, bemanning och spårbara antaganden. |
| `integrated_inputs.py` | Adapter från reproducerbara scope- och optimeringsunderlag till terminsmodellens behov, rum och källspårbarhet. |
| `integrated_runs.py` | Skapar granskningsbara körningsartefakter för integrerade terminsresultat. |
| `integrated_validation.py` | Läser en sparad terminskörning och kontrollerar regelvis täckning, kapacitet, intervall, ort, antaganden och bemanning. |
| `run_integrity.py` | Fryser specifikation, modellindata och resultatfiler med SHA-256 och verifierar att eftervalideringen läser oförändrade artefakter. |
| `api.py` | FastAPI-lager för parametrar, scenarier, asynkrona lokala körningar, resultat och eftervalidering. |
| `app_paths.py` | Resurs- och användarskrivbara sökvägar för utveckling och paketerad applikation. |
| `app_storage.py` | TOML-baserade användarscenarier, inställningar och resultatinspektion utan databasserver. |
| `scenario_consistency.py` | Synkroniserar redigerbara terminsparametrar, kalenderperioder och de spårbarhetsantaganden som redovisar samma värden. |
| `desktop.py` | Windowsstartpunkt som startar localhost-server och öppnar standardwebbläsaren. |
| `job_manager.py` | Enkeltrådig lokal jobbkö som hindrar samtidiga resultatskrivningar. |
| `cost_model.py` | Datatyper och spärrat resultat för kostnader tills verifierade avtalskopplingar finns. |
| `cost_comparison.py` | Visar källans internhyreprofil och scenariokostnad utan att omvandla deras differens till besparing. |
| `linkage.py` | Kandidatdiagnostik mellan bokningsplaceringar och Ladok; gör inga verifierade kopplingar. |
| `loaders.py` | Läsning och schemakontroll av de tre Excelkällorna. |
| `model_inputs.py` | Bygger provisoriska bokningshändelser, kandidatrelationer, rumsinventering och optimeringsinmatningar. |
| `normalize.py` | Normalisering av text, datum, tal och tekniska nycklar. |
| `optimization_runs.py` | Körningslagring, manifest, rapporter, resultathämtning och scenariojämförelser. |
| `optimizer_config.py` | Typad inläsning och fullständig validering av körningskonfigurationer. |
| `optimizer_hint.py` | Deterministisk, kapacitetskontrollerad startlösning på historiska tider. |
| `optimizer_model.py` | CP-SAT-modell, daglig dekomposition, lösningsextraktion och kapacitetsmått. |
| `optimizer_time.py` | Tidsalternativ, tidskonvertering och analytisk kontroll av historisk toppkapacitet. |
| `optimizer_validation.py` | Oberoende eftervalidering av sparade solverplaceringar. |
| `paths.py` | Reporot, standardkällmapp och validering av källfilernas existens. |
| `pipeline.py` | Orkestrerar inläsning, normalisering, diagnostik, CSV-utdata och rapportering. |
| `provenance.py` | Skapar ett deterministiskt körmanifest med SHA-256 och radantal för in- och utdata. |
| `reporting.py` | Skriver baslinje-, kvalitets- och kandidatkopplingsrapporter. |
| `synthetic_integrated.py` | Litet CP-SAT-bevisfall där salstillfällen skapar bemanningskostnad och lokal- samt personalkostnad optimeras gemensamt. |
| `term_calendar.py` | Genererar scenariostyrda terminsdatum och skrivpass samt filtrerar pass som inte rymmer tentamenslängden. |
| `term_rules.py` | Delade hårda regler för kurs/programkrock, område, digitalt krav och sals tillgänglighet. |
| `staffing.py` | Bygger anonymiserade men individuellt genomförbara vaktuppgifter från trappa, pass, raster, vila och byggnadsbyte. |
| `staffing_validation.py` | Fristående kontroll av sparade vaktuppgifter utan att planeringsalgoritmen anropas. |
| `term_run.py` | Genomför första skalbara, konstruktiva terminskörningen genom portföljurval, hårda placeringsregler och integrerad bemanningskostnad. |
| `validation.py` | Beräknar kvalitetsmått och kvalitetsfynd per datakälla. |

## Tester och utvecklingsverktyg

| Fil | Ansvar |
|---|---|
| `tests/test_cost_model.py` | Säkrar att sparbelopp förblir spärrat utan verifierade kostnadskopplingar. |
| `tests/test_cost_comparison.py` | Säkrar att källinternhyra och scenariokostnad aldrig redovisas som verifierad besparing. |
| `tests/test_cli.py` | Säkrar JSON som standard, statuskontraktet och maskinläsbara fel. |
| `tests/test_canonical_demand.py` | Säkrar scope-täckning och att flera källaktiviteter kan bilda ett tentamensbehov utan dubbelräkning. |
| `tests/test_file_policy.py` | Säkrar filstorlekströsklarna och att ingen Python-fil passerat den obligatoriska delningsgränsen. |
| `tests/test_integrated_term.py` | Säkrar hård deltagartäckning och gemensam optimering av lokalportfölj samt anonym samtidig bemanning. |
| `tests/test_integrated_config.py` | Säkrar att det versionshanterade terminscenariot har validerbar kalender och spårbara antaganden. |
| `tests/test_integrated_inputs.py` | Säkrar adapterens källspårbarhet och synliga scope-fullständighet. |
| `tests/test_integrated_validation.py` | Säkrar oberoende eftervalidering, inklusive passöverlappning, kapacitet, ort och ej verifierbar verksamhetsstatus. |
| `tests/test_api.py` | Säkrar lokalt API-kontrakt för parametervisning, scenariekopia och validering. |
| `tests/test_app_storage.py` | Säkrar TOML-serialisering och användarscenariernas läs-/valideringsflöde. |
| `tests/test_staffing.py` | Säkrar bemanningstrappa, arbetspass, raster, vila och byggnadsbyten. |
| `tests/test_term_run.py` | Säkrar att schemaläggarens sparade vaktintervall kan valideras oberoende. |
| `tests/test_linkage.py` | Säkrar kurskodsextraktion och att kandidatmatchningens tvetydighet bevaras. |
| `tests/test_model_inputs.py` | Säkrar kandidatrelationer, flera placeringar per efterfrågepost och behandling av saknat efterfrågevärde. |
| `tests/test_normalize.py` | Säkrar central textnormalisering och synliggör blandat bokningskorn. |
| `tests/test_optimizer.py` | Säkrar kapacitet, överlappning, samlokalisering, uppdelning, tidsflexibilitet, reproducerbarhet och eftervalidering. |
| `tests/test_synthetic_integrated.py` | Säkrar att det integrerade syntetiska fallet väljer högre bemanning när lokalbesparingen är större och täcker samtliga deltagare. |
| `tests/test_term_calendar.py` | Säkrar att terminskalendern respekterar konfigurerade veckodagar, pass och tentamenslängder. |
| `tools/inventory.py` | Utvecklingsverktyg: importgraf, nåbarhet, oreferererade symboler, API-rutter, CLI-kommandon och frontendfiler. |
| `tools/check_code_file_lengths.py` | Fristående kontroll: mål 500 rader, stark varning vid 800 och fel vid 1 000 rader. |

## Rapporter och genererade filer

| Fil eller katalog | Ansvar |
|---|---|
| `reports/baseline.md` | Granskningsbar sammanfattning av baslinjens mått och kvalitetsfynd. |
| `reports/data_quality.json` | Maskinläsbar version av datakvalitetsresultatet. |
| `reports/candidate_linkage.md` | Granskningsbar sammanfattning av kandidatdiagnostiken mellan bokningar och Ladok. |
| `reports/candidate_linkage.json` | Maskinläsbara mått från kandidatdiagnostiken. |
| `reports/optimization_readiness.md` | Kort rapport om vad underlaget kan användas till och vilka spärrar som återstår. |
| `reports/optimization_readiness.json` | Maskinläsbara mått om täckning och beredskap för explorativa PoC-körningar. |
| `reports/optimization_runs.md` | Versionshanterad sammanfattning av de första eftervaliderade referens- och alternativkörningarna. |
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
