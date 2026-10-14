# Lokalt gränssnitt för optimeringen

React-klienten är en separat Vite-komponent under `frontend/`. FastAPI är ett tunt lokalt integrationslager: optimerings-, regel- och kostnadslogik ligger kvar i Pythonpaketet. I distribuerad version serverar FastAPI den byggda klienten och lyssnar endast på `127.0.0.1:8765`.

## Utveckling från källkod

Förutsätter Python 3.11+ och Node.js på utvecklingsdatorn.

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
npm --prefix frontend install
npm --prefix frontend run dev
.\.venv\Scripts\python.exe -m uvicorn tentaoptimering.api:app --host 127.0.0.1 --port 8765
```

Vite proxar `/api` till FastAPI. Välj källdatakatalog under **Underlag** och kör **Förbered underlag** före den första optimeringen. Användarscenarier, bearbetat underlag, rapporter och körresultat ligger under `%LOCALAPPDATA%\Uppsala universitet\Tentaoptimering`, aldrig i installationsmappen.

Resultatet är en modellkostnad, inte faktisk kostnad. Teknisk eftervalidering, verksamhetsmässig verifiering och ursprung redovisas som tre separata domar; regeldata som saknas eller endast är antaganden blir aldrig godkända.

## Paketerad Windowsversion

På byggdatorn körs:

```powershell
.\packaging\build_windows.ps1 -Python .\.venv\Scripts\python.exe
```

Skriptet låser frontendens npm-paket med `npm ci`, bygger Vite-resurserna och skapar `dist\Tentaoptimering\Tentaoptimering.exe` med PyInstaller. Slutanvändaren startar endast denna `.exe`: den startar lokal server, öppnar standardwebbläsaren och kräver varken Node.js, Python, Docker eller databasserver.

Före leverans ska distributionen provas på en dator utan utvecklingsverktyg och utan nätverk: kopiera hela `dist\Tentaoptimering` till en skrivbar plats, koppla ur nätverket, starta `.exe`, välj en lokal källdatakatalog och genomför förberedelse, optimeringskörning och eftervalidering. Kontrollera särskilt att `127.0.0.1` är enda lyssnaradressen och att data skrivs under användarprofilen.

## Sidor

Menyn har tre sidor: **Optimering** (startsida), **Lokaler** och **Underlag**. Båda hålls monterade när man byter sida, så att ändringar, en pågående körning och en pågående förberedelse inte tappas.

## Underlag

Sidan **Underlag** gör det som krävs före en optimering och har två steg samt en sammanfattning.

**1. Källdatakatalog.** Mappen med Excel-källorna skrivs in eller väljs med **Bläddra…** (öppnar Windows mappväljare i den lokala Pythonprocessen, `POST /api/settings/choose-source-directory`; en webbläsare kan inte själv ge en sökväg). Valet fyller bara fältet. Sökvägen sparas i användarprofilen först med **Spara sökväg** (`GET` och `PUT /api/settings`; filen skrivs atomärt). Medan du skriver görs en **förhandskontroll** (`GET /api/source-check?path=…`) som visar vilka av de tre förväntade filerna som finns, med storlek och ändringsdatum, och namnger de som saknas. Kontrollen listar inget annat och läser inga filinnehåll. Filnamnen är fasta i `paths.py` (`SourceFiles`). Originalfilerna läses bara och ändras aldrig. Sökvägen kan inte ändras medan en förberedelse pågår.

**2. Förbered underlaget.** `POST /api/preparation` startar ett jobb, men bara om förhandskontrollen av den *sparade* katalogen är godkänd (annars 422 med de saknade filnamnen). Jobbet bygger i en tillfällig katalog (`<användarprofil>\.staging`) och ersätter det gamla underlaget först när allt, inklusive manifestet, är färdigt: ett fel eller avbrott lämnar det tidigare underlaget orört. Sidan följer jobbet via `GET /api/preparation` en gång i sekunden och visar sju steg med det pågående markerat. Svaret innehåller det senaste jobbet, så ett jobb som pågår känns igen efter en omladdning. Är underlaget redan aktuellt heter knappen **Förbered om** och frågar först. Efter en lyckad förberedelse hämtar Optimerings- och Lokalsidorna sina data på nytt, och en knapp leder till Optimering.

**Underlagets tillstånd.** `GET /api/preparation` svarar också med `underlay.state`: `current` (stämmer med källfilerna), `stale` (en källfil har ändrats eller försvunnit, katalogen är en annan eller konfigurationen i `config/` har ändrats; skälen listas), `incomplete` (en fil saknas eller har ändrats), `unverified` (underlag utan manifest, till exempel från en äldre version) eller `missing`. Tillståndet bygger på manifestet `data/processed/underlay.json` (`underlay_manifest.py`): förberedelsetid, källkatalog, källfilernas storlek, ändringstid och SHA-256, konfigurationens SHA-256, radantal per tabell, bokningarnas period och en kvalitetssammanfattning. Sammanfattningen visas under knappen "Förbered". Föråldring bedöms på filstorlek och ändringstid, inte på innehåll; en fil som skrivs över med samma storlek och tid upptäcks inte.

Sidan visar alltså inte längre underlagets finns-status ur scenariolistan. Optimeringssidans eget besked om saknat underlag (se nedan) är oförändrat.

## Optimering

Sidan **Optimering** är den gemensamma optimeringen av datum, salar och bemanning. Den har två flikar.

**Saknat underlag.** Om det valda scenariot är ett regelbaserat urval utan känt antal tentor, eller om servern svarar att underlaget inte kan läsas (vid scenariolistan, vid start eller under körningen), visas en ruta "Underlaget är inte förberett" med knappen "Gå till Underlag". Start är avstängd så länge antalet tentor saknas. Gränssnittet gör inga särskilda anrop för detta; det tolkar svaren från de vanliga anropen.

**1. Ställ in och kör.** Överst ligger en fast rad (den följer med när man bläddrar) med scenariovalet, antalet ändringar och **Kör**, och under den en rad med det som körs, var och en en gång: antal tentor, planeringsområde, period och när underlaget förbereddes (varnar om det inte är aktuellt). Längre förklaringar (scenariots beskrivning, underlagets täckning, planeringsunderlaget) ligger bakom ⓘ på den raden och visas inte någon annanstans. Därunder:
- **Period** på en rad: från och till inom underlagets täckning samt genvägarna En dag, En vecka, En månad och Hela underlaget. En period utanför underlaget avvisas med skälet, och en delvis täckt period måste godkännas uttryckligen. Scenarier med namngivna tentor tar inget periodval.
- **Parametrar**: de vanligaste överst och direkt ändringsbara (veckodagar, starttider, flyttfönster, flyttbara typer, salar, efterfrågevariation, lokal- och vaktkostnad, längsta beräkningstid; listan finns i `frontend/src/lib/featuredParams.ts`), därefter *Fler parametrar* (grupperade, med sökning och avancerade) hopfällt. Varje rad visar etikett och inmatning; hjälptext, standardvärde, grund och id ligger bakom ⓘ. Ändringarna listas bara när det finns några, med Återställ per rad. Belopp ligger i öre i API:et men visas och matas in i kronor (`lib/paramUnits.ts`). Salar och tentamenstyper väljs med kryssrutor över det som finns i underlaget (`GET /api/joint-runs/options`). Parametrar som finns i modellen men inte går att sätta (`editable: false`) är dolda tills "Visa parametrar som inte kan ändras" väljs. Fel från servern (HTTP 422) visas vid rätt rad.
- **Körningsinställningar och spara som scenario** är hopfällt: start från förra körningen, datorresurser och "Spara som nytt scenario" (originalscenariot ändras aldrig). Uppskattad körtid ligger bakom ⓘ vid Kör.

**2. Resultat.** Det finns två flikar: *Ställ in och kör* och *Resultat*. Startas en körning går sidan till Resultat. Medan körningen pågår visas överst en rad med scenario, förbrukad tid och Stoppa, de ändringar körningen gjordes med, och körningens steg (tidslinje, kostnad över tid, resurser, dagrutnät). När körningen är klar försvinner den delen och den nya körningen väljs automatiskt i resultatet; en körning som inte gav något resultat får ett besked överst i stället. Rutan "pågår" bygger på händelsen `day_started`; för körningar utan den händelsen uppskattas den och sidan säger det. Körningar benämns för användaren som *scenario och klockslag* (till exempel "Alla tentor i underlaget, 13 okt 14:12"; `lib/runLabel.ts`); det tekniska id:t visas bara bakom en ⓘ. Utan val visas den senaste körningen. Resultatet innehåller sammanfattning, jämförelse mot föregående körning av samma scenario (eller en vald) via `GET /api/joint-runs/{id}/compare`, de tre bedömningarna isär, körningens tidslinje, start från förra körningen och "Förlopp i efterhand".

**Besparingspotential överst.** För en körning med verifierad lösning är det första kortet **Besparingspotential, teoretisk**: skillnaden i modellens årliga kapacitetskostnad mellan **Nuläge** och körningen (`GET/POST /api/joint-runs/{run_id}/savings`). Nuläge är samma scenario, data och kostnadsantaganden med `flex.movable_types = []`, så att varje tentamen behåller sitt ursprungstillfälle medan salar och bemanning planeras så billigt som möjligt. Knappen "Beräkna besparingspotential" löser Nuläge som ett bakgrundsjobb; resultatet sparas under `baselines/` i användarprofilen (utanför körningslistan) och återanvänds för varje körning med samma scenario och underlag. Potentialen visas som belopp per år och andel av Nuläge; när någon sökning inte är bevisat optimal visas ett intervall från de bevisade gränserna. En tabell visar vilka kostnader (lokaler, vaktpool) skillnaden kommer från. Den är teoretisk, för de valda tentorna och med scenariots proxypriser, inte en verifierad realiserbar besparing (avtal, uppsägningstider och undvikbarhet ingår inte). Saknar körningen verifierad lösning, eller hittar Nuläge ingen, redovisas ingen potential och skälet sägs.

**Körning utan lösning: "Vad gick fel?"** Saknar en körning verifierad lösning visas först ett kort besked med skälet (bevisad omöjlighet eller ingen lösning hittad inom tidsgränsen) och därunder kortet "Vad gick fel?". Det listar vad användaren ändrade jämfört med scenariot körningen startade från (parametrar och vald period, med gammalt och nytt värde; `GET /api/joint-runs/{run_id}/diagnosis`). Knappen "Utred vilken ändring som orsakade det" (`POST` samma väg, ett bakgrundsjobb som följs via samma `GET`) löser utgångsscenariot en gång och därefter scenariot med bara en av ändringarna i taget, högst 30 sekunder per prov, utan att något prov sparas som en körning. Ett prov är *Omöjlig ensam* (bevisat), *Går att lösa* eller *Oklart*; bara bevisad omöjlighet pekas ut som orsak. Är utgångsscenariot självt omöjligt sägs det. Resultatet sparas som `joint_diagnosis.json` i körningens katalog. Utredningen testar ändringar var för sig: samverkande ändringar och orsaker som kräver mer än tidsgränsen hittas inte, och det sägs i texten.

**Förklaringar och varningar.** Förklaringar och instruktioner ligger bakom en ⓘ-ikon (`components/ui/info-tip.tsx`) och visas när man klickar. Varningar och fel visas med en rubrik som tar lite plats och med detaljerna hopfällda (`components/ui/notice.tsx`). Sidorna Optimering är omgjorda efter denna regel; Underlag och Lokaler följer.

**Utseende.** Standardtypsnitt är "Helvetica Neue", Helvetica, Arial, sans-serif; grundstorleken är 17 px och rubriker är större och fetare (h1 25 px, kortrubriker 17 px, alla i fetstil). Färg används bara för att signalera något (fel, varning, godkänt, osäkert) och alltid tillsammans med en ikon och en text; dekorativa färgytor, till exempel färgade kostnadsrutor, används inte. Texter ska ha hög kontrast (mörk text på ljus eller vit botten). Dubbla uppgifter visas inte två gånger: är kostnaden bevisat lägsta räcker rubriken, och verifierad kostnad, undre gräns och gap visas först när de skiljer.

- Sammanfattningen visar vilka parametrar som avviker från standardvärdet (etikett ur parameterlistan, annars id). Har körningen ingen verifierad lösning (`has_verified_solution: false`) visas bara ett besked med skälet (`unverified_reason`) och domarna: aldrig en kostnad, ett intervall eller andra lösningsmått, och inte heller kostnadsgrafen.
- Har kostnads- eller efterfrågeantaganden ändrats mellan två körningar (`assumption_changes`) visas rutan "Antaganden har ändrats" före måtttabellen. Kostnadsraderna visar Tidigare och Nu men ingen skillnad och är märkta "Jämförs inte (andra antaganden)"; salar, vaktpool och flyttade tentor framhävs och behåller sin skillnad. En jämförelse mot en körning utan verifierad lösning visas utan skillnader.
- "Förlopp i efterhand" är hopfälld som standard och spelar upp hur körningen gick till ur den sparade händelseloggen. Inget körs om.

Kostnad utan bevisat optimum visas som intervallet "undre gräns–verifierad kostnad" och aldrig som besparing. Saknat värde tolkas som `not_evaluated`.

## API-kontrakt

Klienten använder bara dessa rutter:

| Rutt | Används av |
| --- | --- |
| `GET` och `PUT /api/settings` | Underlag: källdatakatalog |
| `POST /api/preparation`, `GET /api/jobs/{id}` | Underlag: förberedelse och jobbstatus |
| `GET` och `POST /api/joint-runs/scenarios`, `GET /api/joint-runs/parameters` | Optimering: scenarier och parametrar |
| `GET /api/joint-runs/options` | Optimering: salar och tentamenstyper i underlaget (kryssrutor) |
| `POST /api/joint-runs`, `GET /api/joint-runs/{id}/events`, `POST /api/joint-runs/{id}/cancel` | Optimering: starta, följa och stoppa en körning |
| `GET /api/joint-runs/{id}/summary`, `GET /api/joint-runs/{id}/compare` | Optimering: resultat och jämförelse |
| `GET /api/joint-runs/warm-start-candidates` | Optimering: sparade körningar och val av startpunkt |
| `GET /api/runs/{id}/events`, `GET /api/runs/{id}/warm-start` | Optimering: uppspelning och startbeslut |

Typerna ligger i `frontend/src/lib/jointTypes.ts` och `frontend/src/lib/underlayApi.ts`. Appen skickar aldrig inspelade eller påhittade händelser. Testdata för logiktesterna ligger under `frontend/src/lib/testing/` och ett test säkerställer att appkod inte importerar dem och att inga borttagna rutter anropas. `npm --prefix frontend test` kör logiktesterna med Node utan extra beroenden.

## Kontraktstester

Riktiga svar från backend finns som ögonblicksbilder i `frontend/src/lib/testing/contract/` (sammanfattning med och utan verifierad lösning, jämförelse med ändrade antaganden, utan tidigare körning och mot en körning utan verifierad lösning, alternativen ur underlaget (`options.json`) samt `/events` för en klar och en misslyckad körning). `jointContract.test.ts` matar dem genom klientens adaptrar och kräver att varje fält i svaret är hanterat, så att ett nytt eller omdöpt fält fångas i testerna och inte först i webbläsaren. När backend ändrar kontraktet: uppdatera ögonblicksbilderna och låt testet visa vad klienten saknar.
