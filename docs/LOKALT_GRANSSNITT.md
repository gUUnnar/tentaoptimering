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

Menyn har två sidor: **Optimering** (startsida) och **Underlag**. Båda hålls monterade när man byter sida, så att ändringar, en pågående körning och en pågående förberedelse inte tappas.

## Underlag

Sidan **Underlag** gör det som krävs före en optimering och har två steg.

**1. Källdatakatalog.** Mappen med Excel-källorna väljs och sparas i användarprofilen (`GET` och `PUT /api/settings`). Originalfilerna läses bara och ändras aldrig. Sökvägen kan inte ändras medan en förberedelse pågår.

**2. Förbered underlaget.** `POST /api/preparation` startar ett jobb som läser källfilerna (tentaplaceringar, Ladok-uppgifter om tentander och lokalhyror), rensar och kopplar ihop dem och sparar det bearbetade underlag som optimeringen räknar på. Förberedelsen använder den *sparade* katalogen, så knappen är avstängd tills sökvägen är sparad. Jobbet följs via `GET /api/jobs/{id}` en gång i sekunden; misslyckas det visas serverns felmeddelande. Förberedelsen krävs före en optimering: hela terminen hämtar sina tentor ur det förberedda underlaget. Den körs första gången och igen när källfilerna har bytts ut.

Sidan visar också om underlaget verkar finnas. API:et har ingen särskild fråga för det, så det avgörs ur scenariolistan: ett regelbaserat urval (till exempel hela terminen) får sitt antal tentor ur det förberedda underlaget, och saknas antalet saknas underlaget. När en förberedelse är klar hämtar Optimeringssidan scenarierna på nytt.

## Optimering

Sidan **Optimering** är den gemensamma optimeringen av datum, salar och bemanning. Den har tre flikar.

**Saknat underlag.** Om det valda scenariot är ett regelbaserat urval utan känt antal tentor, eller om servern svarar att underlaget inte kan läsas (vid scenariolistan, vid start eller under körningen), visas en ruta "Underlaget är inte förberett" med knappen "Gå till Underlag". Start är avstängd så länge antalet tentor saknas. Gränssnittet gör inga särskilda anrop för detta; det tolkar svaren från de vanliga anropen.

**1. Ställ in och kör.**
- Scenariovalet visar urvalet i klartext (till exempel "Hela terminen, Uppsala, 1 172 tentor") och, för stora urval, en ärlig körtidsuppgift.
- Parametrarna visas grupperade med etikett, enhet och hjälptext. Inmatningen följer värdetypen: tal, ja/nej-knapp, val, datum, klockslag, veckodagar som markerbara knappar, listor med lägg till och ta bort, perioder och bemanningstrappan som tabell. Belopp ligger i öre i API:et men visas och matas in i kronor; omvandlingen finns i `frontend/src/lib/paramUnits.ts` och är testad. Typer utan redigerare (matriser, regeluppsättningar, salslistor) visas skrivskyddat med en förklaring.
- Parametrar som finns i modellen men inte påverkar något än (`editable: false`) visas avstängda. Avancerade parametrar ligger bakom "Visa avancerade".
- Ett fast fält överst listar alla ändringar jämfört med scenariot (gammalt värde till nytt värde), med "Återställ" per rad och "Återställ alla". Bara ändringarna skickas med körningen i `parameters`.
- Lokal validering av uppenbara fel görs före start. Fel från servern (HTTP 422, `detail.errors`) visas vid rätt rad och i en sammanfattning.
- "Startar från förra körningen" kan vara automatisk, av eller en vald körning. Förra körningens placering kontrolleras alltid på nytt mot de nya reglerna.
- "Spara ändringarna som nytt scenario" skapar ett eget scenario. Originalscenariot ändras aldrig.

**2. Körning.** Steg i klartext, kostnadsgraf (verifierad kostnad, undre gräns och gap), dagrutnät, resurser, de parametrar körningen ändrat och stoppknapp. Rutan "pågår" bygger på händelsen `day_started`; för körningar utan den händelsen uppskattas den och sidan säger det.

**3. Resultat och jämförelse.** Sammanfattning, jämförelse mot föregående körning av samma scenario (eller en vald körning) via `GET /api/joint-runs/{id}/compare`, de tre bedömningarna isär, start från förra körningen och uppspelning. En kort ruta förklarar hur resultatet läses.

Kostnad utan bevisat optimum visas som intervallet "undre gräns–verifierad kostnad" och aldrig som besparing. Saknat värde tolkas som `not_evaluated`.

## API-kontrakt

Klienten använder bara dessa rutter:

| Rutt | Används av |
| --- | --- |
| `GET` och `PUT /api/settings` | Underlag: källdatakatalog |
| `POST /api/preparation`, `GET /api/jobs/{id}` | Underlag: förberedelse och jobbstatus |
| `GET` och `POST /api/joint-runs/scenarios`, `GET /api/joint-runs/parameters` | Optimering: scenarier och parametrar |
| `POST /api/joint-runs`, `GET /api/joint-runs/{id}/events`, `POST /api/joint-runs/{id}/cancel` | Optimering: starta, följa och stoppa en körning |
| `GET /api/joint-runs/{id}/summary`, `GET /api/joint-runs/{id}/compare` | Optimering: resultat och jämförelse |
| `GET /api/joint-runs/warm-start-candidates` | Optimering: sparade körningar och val av startpunkt |
| `GET /api/runs/{id}/events`, `GET /api/runs/{id}/warm-start` | Optimering: uppspelning och startbeslut |

Typerna ligger i `frontend/src/lib/jointTypes.ts` och `frontend/src/lib/underlayApi.ts`. Appen skickar aldrig inspelade eller påhittade händelser. Testdata för logiktesterna ligger under `frontend/src/lib/testing/` och ett test säkerställer att appkod inte importerar dem och att inga borttagna rutter anropas. `npm --prefix frontend test` kör logiktesterna med Node utan extra beroenden.
