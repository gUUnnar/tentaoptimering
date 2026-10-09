# Första leverans – gemensam CP-SAT-kärna

## Levererat

Den nya produktionskärnan använder ett versionsmärkt kontrakt (`joint-optimization-input-v1`) och optimerar i samma CP-SAT-problem:

- val av datum och skrivpass bland uttryckliga kandidater;
- hela deltagarvolymen för varje tentamensbehov;
- användning och kostnad för faktiska salar;
- fysisk kapacitet, ort, digital kompatibilitet och rumstillgänglighet;
- samlokalisering, uppdelning, byggnadsregel och ställtid;
- regelberäknat vaktbehov per aktivt salstillfälle;
- dimensionerande anonym samtidig bemanningspool;
- fast lokalårskostnad, extern kostnad per salstillfälle, årlig poolkostnad och rörlig kostnad per vaktsalstillfälle.

Kostnaden minimeras först. Endast när minsta kostnad är bevisad låses kostnaden och en andra solve minimerar antalet ändrade tentamenstillfällen. Därmed kan en historisk placering inte ändras enbart för att hitta en annan ekonomiskt likvärdig lösning.

`participant_group` äger deltagarantalet. En grupp kan hänvisa till flera källaktiviteter utan att talet räknas flera gånger. En källaktivitet får förekomma exakt en gång i hela kontraktet. Samtentor kan bestå av flera uttryckliga, disjunkta delgrupper under samma `exam_demand`.

## Solverstatus

Resultatkontraktet skiljer följande utfall:

| Utfall | Betydelse |
|---|---|
| `optimal` | Fullständig lösning finns och minsta jämförbara kostnad är bevisad. |
| `feasible_not_proven` | Fullständig lösning finns men kostnadsoptimum är inte bevisat. |
| `infeasible` | CP-SAT har bevisat att hela den modellerade efterfrågan inte kan placeras. |
| `no_feasibility_conclusion` | Sökningen gav varken en fullständig lösning eller ett bevis på ogenomförbarhet. |

En lösning kan aldrig få lägre kostnad genom oplacerad efterfrågan. Partiell placering returneras inte av huvudmodellen. Resultatet redovisar funnet kostnadsmål, bästa kostnadsgräns, relativt gap, körtid och separat status för ändringspreferensen.

Teknisk placeringsfullständighet avser endast den uttryckligen modellerade omfattningen. Oavgjorda aktiviteter i källpopulationen redovisas separat och hindrar påståenden om hela verksamheten.

## Handräknade referensfall

`tests/test_joint_optimizer.py` innehåller oberoende småfall med exakta svar:

- två 40-personers tentor väljer en större sal för 600 öre och en vaktpool för 1 000 öre (totalt 1 600), eftersom två billigare småsalar skulle kräva två samtidiga vakter (totalt 2 200);
- 25 deltagare i två delgrupper placeras som exakt 25, trots att en delgrupp har två källaktiviteter;
- lika ekonomisk kostnad bevarar originalpasset;
- 60 deltagare, en 50-platsers sal och max en sal ger `infeasible`, aldrig en 50-personers dellösning;
- digitalt krav använder bara digital sal och samma kurs tvingas till icke överlappande pass;
- 30 minuters ställtid accepterar nästa start exakt vid gränsen och avvisar en start en minut för tidigt.

## Avgränsat verkligt datafall

Körningen är reproducerbar från de genererade, ignorerade underlagen:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
.\.venv\Scripts\python.exe -m tentaoptimering.cli optimize-joint `
  --config config\scenarios\joint_real_subset.toml
```

Konfigurationen namnger exakt tolv verkliga bokningshändelser den 12–13 januari 2026 och tillåter pass den 12–14 januari. Händelser med flera Ladokaktiviteter byggs som ett behov med flera delgrupper. Endast Uppsalasalar med publicerad kapacitet används; Campus Gotland B40 filtreras bort både av planeringsområde och tillgänglighetsdatum.

Verifierad utvecklingskörning den 9 oktober 2026:

- 12 av 12 modellerade tentamensbehov och 1 028 av 1 028 deltagare placerades;
- solverutfall `optimal`, funnet mål och bästa gräns 37 900 000 öre, gap 0;
- 22 900 000 öre lokalproxy och 15 000 000 öre bemanningspoolproxy;
- en faktisk sal och tre dimensionerande samtidiga anonyma resurser;
- fyra tentamensbehov flyttades efter sekundär minimering;
- uppmätt väggtid cirka 1,85 sekunder på utvecklingsdatorn.

Beloppen följer uttryckliga proxyer (1 000 kr per plats och år samt 50 000 kr per anonym poolresurs och år). De är varken faktisk kostnad, teoretisk besparing mot nuläge eller verifierad realiserbar besparing.

## Kända begränsningar och nästa steg

Första kärnan planerar anonym samtidig bemanning och inte individuella vakters arbetspass, raster, vila, resor eller bomtid. Studentöverlapp, tentamensperioder, kursordning och annualisering finns i parameterkatalogen som `contract_only` och listas därför som ej implementerade i varje körning. Externa salstillfälleskostnader stöds av motorn men det verkliga delurvalet saknar verifierade externa hyresobjekt och använder därför noll i den komponenten.

Nästa vertikala steg är att bygga samma kontrakt för en längre kalender och större kanonisk population, lägga till oberoende eftervalidering för den nya resultattypen och därefter koppla individuella vaktkedjor och jämförbart nuläge. Den äldre konstruktiva motorn tas bort först när dessa funktioner har flyttats och den nya vägen har bevisad motsvarande täckning.
