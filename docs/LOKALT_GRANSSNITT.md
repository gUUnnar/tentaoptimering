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

`/api/parameters` visar status för implementation och verifiering. Terminsmallen har typade kontroller för kalender, skrivpass, ställtid, bemanningstrappa och kostnadsantaganden; JSON är enbart ett avancerat alternativ. `/api/scenarios` hanterar inbyggda mallar och redigerbara användarkopior och validerar nya innehåll atomiskt före lagring. `/api/preparation` och `/api/simulations` returnerar jobb-id:n; en lokal arbetskö med exakt en arbetare hindrar konkurrerande skrivningar till resultatfiler. Vid jobbinlämning kopieras scenariot till en oföränderlig snapshot som sedan följer med körningsartefakten. `/api/runs`, `/api/runs/{id}/validation` och `/api/runs/compare` exponerar sparade resultat, fristående eftervalidering samt både parameter- och resultatskillnader mellan frysta körningar.

Äldre kapacitetsscenarier är läsbara för spårbarhet men har inte den nya termins-eftervalideringsartefakten. Gränssnittet gör den begränsningen synlig.
