# Lokalt simuleringsgränssnitt

React-klienten är en separat Vite-komponent under `frontend/`. FastAPI är ett tunt lokalt integrationslager: optimerings-, regel- och kostnadslogik ligger kvar i Pythonpaketet. I distribuerad version serverar FastAPI den byggda klienten och lyssnar endast på `127.0.0.1:8765`.

## Utveckling från källkod

Förutsätter Python 3.11+ och Node.js på utvecklingsdatorn.

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
npm --prefix frontend install
npm --prefix frontend run dev
.\.venv\Scripts\python.exe -m uvicorn tentaoptimering.api:app --host 127.0.0.1 --port 8765
```

Vite proxar `/api` till FastAPI. Välj källdatakatalog i gränssnittet och kör **Förbered underlag** före en terminsimulering. Användarscenarier, bearbetat underlag, rapporter och körresultat ligger under `%LOCALAPPDATA%\Uppsala universitet\Tentaoptimering`, aldrig i installationsmappen.

Den inbyggda terminsmallen är explorativ. Eftervalideringen visar därför teknisk placeringsfullständighet separat från verksamhetsmässig genomförbarhet; regeldata som saknas eller endast är antaganden blir aldrig godkända.

## Paketerad Windowsversion

På byggdatorn körs:

```powershell
.\packaging\build_windows.ps1 -Python .\.venv\Scripts\python.exe
```

Skriptet låser frontendens npm-paket med `npm ci`, bygger Vite-resurserna och skapar `dist\Tentaoptimering\Tentaoptimering.exe` med PyInstaller. Slutanvändaren startar endast denna `.exe`: den startar lokal server, öppnar standardwebbläsaren och kräver varken Node.js, Python, Docker eller databasserver.

Före leverans ska distributionen provas på en dator utan utvecklingsverktyg och utan nätverk: kopiera hela `dist\Tentaoptimering` till en skrivbar plats, koppla ur nätverket, starta `.exe`, välj en lokal källdatakatalog och genomför förberedelse, terminskörning och eftervalidering. Kontrollera särskilt att `127.0.0.1` är enda lyssnaradressen och att data skrivs under användarprofilen.

## API-kontrakt

`/api/parameters` visar både parameterregistrets status för implementation och verifiering, samt `term_parameter_bindings`: den uttömmande listan över den aktuella terminsmotorns TOML-sökvägar och deras faktiska implementationsstatus. Terminsmallen har typade kontroller för kalender, skrivpass och -perioder, ställtid, bemanningstrappa, arbetspass, raster, arbetstidsgränser, dygnsvila, kostnader, kompatibilitet och krockpolicy; JSON är enbart ett avancerat alternativ. Vid varje scenariesparning synkroniseras redovisade antaganden från beräkningsvärdena, och kalenderperioder följer ändrade terminsgränser. `/api/scenarios` hanterar inbyggda mallar och redigerbara användarkopior och validerar nya innehåll atomiskt före lagring. `/api/preparation` och `/api/simulations` returnerar jobb-id:n; en lokal arbetskö med exakt en arbetare hindrar konkurrerande skrivningar till resultatfiler. Vid jobbinlämning kopieras scenariot till en oföränderlig snapshot som sedan följer med körningsartefakten. `/api/runs`, `/api/runs/{id}/validation` och `/api/runs/compare` exponerar sparade resultat, fristående eftervalidering samt både parameter- och resultatskillnader mellan frysta körningar.

Äldre kapacitetsscenarier är läsbara för spårbarhet men har inte den nya termins-eftervalideringsartefakten. Gränssnittet gör den begränsningen synlig.

## Optimering (den nya motorn)

Sidan **Optimering** i menyn är den enda sidan för den nya, gemensamma optimeringen. De äldre sidorna ligger under rubriken "Äldre motor" och är oförändrade. Sidan har tre flikar.

**1. Ställ in och kör.**
- Scenariovalet visar urvalet i klartext (till exempel "Hela terminen, Uppsala, 1 172 tentor") och, för stora urval, en ärlig körtidsuppgift.
- Parametrarna visas grupperade med etikett, enhet och hjälptext. Inmatningen följer värdetypen: tal, ja/nej-knapp, val, datum, klockslag, veckodagar som markerbara knappar, listor med lägg till och ta bort, perioder och bemanningstrappan som tabell. Belopp ligger i öre i API:et men visas och matas in i kronor; omvandlingen finns i `frontend/src/lib/paramUnits.ts` och är testad. Typer utan redigerare (matriser, regeluppsättningar, salslistor) visas skrivskyddat med en förklaring.
- Parametrar som finns i modellen men inte påverkar något än (`editable: false`) visas avstängda. Avancerade parametrar ligger bakom "Visa avancerade".
- Ett fast fält överst listar alla ändringar jämfört med scenariot (gammalt värde till nytt värde), med "Återställ" per rad och "Återställ alla". Bara ändringarna skickas med körningen i `parameters`.
- Lokal validering av uppenbara fel görs före start. Fel från servern (HTTP 422, `detail.errors`) visas vid rätt rad och i en sammanfattning.
- "Startar från förra körningen" kan vara automatisk, av eller en vald körning. Förra körningens placering kontrolleras alltid på nytt mot de nya reglerna.
- "Spara ändringarna som nytt scenario" skapar ett eget scenario. Originalscenariot ändras aldrig.

**2. Körning.** Steg i klartext, kostnadsgraf (verifierad kostnad, undre gräns och gap), dagrutnät, resurser, de parametrar körningen ändrat och stoppknapp. Rutan "pågår" bygger på händelsen `day_started`; för äldre körningar utan den händelsen uppskattas den och sidan säger det.

**3. Resultat och jämförelse.** Sammanfattning, jämförelse mot föregående körning av samma scenario (eller en vald körning) via `GET /api/joint-runs/{id}/compare`, de tre bedömningarna isär, start från förra körningen och uppspelning. En kort ruta förklarar hur resultatet läses.

Klienten följer API-kontraktet `/api/joint-runs/*`, `/api/runs/{id}/events` och `/api/runs/{id}/warm-start`; typerna ligger i `frontend/src/lib/jointTypes.ts`. Appen skickar aldrig inspelade eller påhittade händelser. Testdata för logiktesterna ligger under `frontend/src/lib/testing/` och ett test säkerställer att appkod inte importerar dem. `npm --prefix frontend test` kör logiktesterna med Node utan extra beroenden.

Kostnad utan bevisat optimum visas som intervallet "undre gräns–verifierad kostnad" och aldrig som besparing. Kostnaden är en modellkostnad, inte faktisk kostnad. Teknisk eftervalidering, verksamhetsmässig verifiering och ursprung redovisas som tre separata domar; saknat värde tolkas som `not_evaluated`.
