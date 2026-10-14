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

Sidan **Optimering** är den gemensamma optimeringen av datum, salar och bemanning. Den har tre flikar.

**Saknat underlag.** Om det valda scenariot är ett regelbaserat urval utan känt antal tentor, eller om servern svarar att underlaget inte kan läsas (vid scenariolistan, vid start eller under körningen), visas en ruta "Underlaget är inte förberett" med knappen "Gå till Underlag". Start är avstängd så länge antalet tentor saknas. Gränssnittet gör inga särskilda anrop för detta; det tolkar svaren från de vanliga anropen.

**1. Ställ in och kör.**
- Överst ligger en fast rad (den följer med när man bläddrar bland parametrarna) med scenariovalet, antalet ändringar och knappen **Kör**, med hjälptexten "Körs med din ändring" eller "Körs med scenariots egna värden". Under raden visar gränssnittet vad scenariot omfattar: urval, **period** och beskrivning, allt ur scenariots egna uppgifter (perioden läses ur urvalets beskrivning; en upplysning om att underlaget saknar tentor efter perioden visas bara om scenariot själv anger den). Gränssnittet påstår aldrig "hela terminen" eller en viss termin.
- Parametrarna visas grupperade med etikett, enhet och hjälptext. Inmatningen följer värdetypen: tal, ja/nej-knapp, val, datum, klockslag, veckodagar som markerbara knappar, listor med lägg till och ta bort, perioder och bemanningstrappan som tabell. Belopp ligger i öre i API:et men visas och matas in i kronor; omvandlingen finns i `frontend/src/lib/paramUnits.ts` och är testad. Typer utan redigerare (matriser, regeluppsättningar) visas skrivskyddat med en förklaring.
- **Salar och tentamenstyper väljs med kryssrutor** över det som finns i underlaget (`GET /api/joint-runs/options?scenario=<id>`, hämtas när scenariot väljs och igen när underlaget har förberetts). `rooms.selection` visar salarna grupperade per byggnad med sal-id, antal platser och digitalstöd (alla platser, delvis, nej, okänt), "Markera alla" och "Ingen" per byggnad och en sammanfattning ("N av M salar valda, X platser"). Alla markerade är samma sak som en tom lista och står som "Alla salar"; annars skickas listan med de markerade. Ingen vald är ett fel ("Minst en sal måste vara vald") och borttagna salar kan göra körningen ogenomförbar, vilket körningens kontroll redovisar. Sal-id måste finnas bland alternativen. `flex.movable_types` visar typerna med antal ("Dugga (22)"); en typ är markerad om något ord i värdet är en delsträng av typens text (gemener), så "hybrid" träffar "Hybridtenta". Ändras markeringen inte behålls det ursprungliga värdet oförändrat; annars skrivs typernas text. Saknas underlaget (`data_available: false`) eller ger rutten fel visas de två parametrarna skrivskyddat med "Förbered underlaget för att kunna välja" och räknas som parametrar som inte kan ändras. Logiken finns i `lib/paramOptions.ts`, kryssrutorna i `components/joint/params/rooms-input.tsx` och `types-input.tsx`.
- Parametrar som finns i modellen men inte går att sätta än (`editable: false`) är bortfiltrerade som standard. Rutan "Visa parametrar som inte kan ändras (N)" visar dem, och "X av Y parametrar visas" räknar det som faktiskt visas. Avancerade parametrar ligger bakom "Visa avancerade".
- En ruta överst bland parametrarna listar alla ändringar jämfört med scenariot (gammalt värde till nytt värde), med "Återställ" per rad och "Återställ alla". Bara ändringarna skickas med körningen i `parameters`.
- Lokal validering av uppenbara fel görs före start. Fel från servern (HTTP 422, `detail.errors`) visas vid rätt rad och i en sammanfattning.
- "Startar från förra körningen" kan vara automatisk, av eller en vald körning. Förra körningens placering kontrolleras alltid på nytt mot de nya reglerna.
- "Spara ändringarna som nytt scenario" (längst ner) skapar ett eget scenario. Originalscenariot ändras aldrig.

**2. Körning.** Tidslinje över körningens steg, kostnadsgraf (verifierad kostnad, undre gräns och gap), dagrutnät, resurser, de parametrar körningen ändrat och stoppknapp. Rutan "pågår" bygger på händelsen `day_started`; för körningar utan den händelsen uppskattas den och sidan säger det.

*Tidslinjen* (`run-timeline.tsx`, modellen i `lib/jointTimeline.ts`) byggs av `phase`-händelserna och visar det som faktiskt körs, i körordning: först ett eget block "Kontroll av förra körningen" (tid och utfall, eller "Hoppades över" med skälet), sedan ett block per varv ("Varv 1", "Varv 2" …) med grov plan, kontroll av varje dag, rättning och försök att behålla ursprungliga tider i den ordning de kördes, och sist "Slutkontroll och sparande". Ett nytt varv börjar varje gång den grova planen körs. Segmentens bredd är proportionell mot tiden med en lägsta synlig bredd, varje steg har egen färg, ikon och text, och det pågående segmentet pulserar (inte med `prefers-reduced-motion`) och har markören "Nu". Vid hovring, fokus eller klick visas tid, hur många dagar som är klara av totalt, hur många som misslyckades och vad det ledde till. En sammanfattningsrad härleds ur händelserna ("4 varv: den grova planen ändrades 3 gånger eftersom 6 dagar inte gick att genomföra"); det som inte är känt utelämnas. Samma tidslinje används i livevyn, i resultatvyn och i "Förlopp i efterhand".

*Förklaringar per kontrolltyp* finns i `lib/jointKinds.ts`: varje typ (kontroll av förra körningen, dagkontroll, utredning, rättning, reservplan, ursprungliga tider, orsakssökning) har egen rubrik, egen förklaring och egen text för "Går inte". Lösarens engelska namn visas aldrig.

*Tiden.* Serverns `elapsed_seconds` i varje `/events`-svar är sanningen; mellan svaren räknar en lokal klocka (`lib/runClock.ts`) vidare, och visningen går aldrig bakåt (det största av det som redan visats och serverns värde plus lokalt förfluten tid). Samma klocka används för förbrukad tid, resursrutan, stegen och tidslinjen. Efter avslut visas serverns slutvärde. `error` i svaret normaliseras till text.

**3. Resultat och jämförelse.** Sammanfattning, jämförelse mot föregående körning av samma scenario (eller en vald körning) via `GET /api/joint-runs/{id}/compare`, de tre bedömningarna isär, körningens tidslinje, start från förra körningen och "Förlopp i efterhand". Sammanfattningen kommer först; jämförelse, domar, förlopp och uppspelning ligger i ett hopfällt avsnitt (öppet bara när det finns en verifierad lösning).

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
