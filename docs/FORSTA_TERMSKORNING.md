# Första terminskörningen – explorativ omfattning

Detta dokument redovisar den första fullständiga körningen för den **preliminärt inkluderade** omfattningen. Det är ett reproducerbart tekniskt test av adapter, kalender, salstillfällen och gemensam kostnadsutvärdering – inte en bekräftelse på ett genomförbart operativt schema eller en realiserbar besparing.

## Reproduktion

```powershell
.\.venv\Scripts\python.exe -m tentaoptimering.cli prepare
.\.venv\Scripts\python.exe -m tentaoptimering.cli optimize-term --config config\scenarios\integrated_term_exploratory.toml
```

Den andra körningen skriver scenario-kopia, placeringsrader, salstillfällen, källspårbarhet, JSON-resultat och Markdown-rapport under `runs/`. Artefakterna är avsiktligt inte versionshanterade eftersom de är genererade.

## Resultat från första körningen

Körningen den 8 oktober 2026 med den genererade baslinjen gav `constructive_feasible` på cirka 6,0 sekunder.

| Mått | Resultat |
| --- | ---: |
| Inkluderade `exam_demand` | 1 258 |
| Placerade `exam_demand` | 1 258 |
| Täckning inom inkluderad omfattning | 100,0 % |
| Totalt antal Ladokaktiviteter | 1 525 |
| Täckning av hela källpopulationen | 82,5 % |
| Oavgjorda aktiviteter | 267 |
| Använda scenariorum | 3 |
| Salstillfällen | 237 |
| Anonym samtidig bemanningspool | 3 resurser |
| Antagen målfunktion | 75 900 000 öre per år |
| Optimalitetsgap | Saknas – konstruktiv metod |

Den valda scenariolösningen använder `uu-bergsbrunnagatan-15-sal-2`, `uu-fyrislundsgatan-80-sal-1` och `uu-rabyvagen-95-sal-3`. Målfunktionen består av 60 900 000 öre i antagen lokalårskostnad och 15 000 000 öre i antagen personalårskostnad.

## Metod och tolkning

Den fullständiga CP-SAT-formuleringen finns för små och medelstora instanser. Den direkta korsprodukten för 1 258 behov, rum och 79 kalenderpass gav inte en lösning inom det första 20-sekundersförsöket ens med kandidatbegränsning. För första körningen används därför en deterministisk konstruktiv metod som prövar lokalportföljer och placerar störst behov först i minst belastade giltiga pass. Varje portfölj utvärderas med samma årliga lokal- och bemanningskostnad.

`constructive_feasible` betyder att samtliga inkluderade behov har en tilldelning som uppfyller scenariots kapacitet, ort, passlängd och ställtid. Det betyder **inte** att kostnaden är globalt optimal; därför publiceras inget numeriskt optimalitetsgap.

## Kvarstående begränsningar

- De 267 oavgjorda aktiviteterna är synliga i `demand_scope.csv`, men ingår inte i körningen. Resultatet får inte beskrivas som täckning av hela populationen.
- Salarnas kalender, framtida kapacitetsgiltighet och digitala kompatibilitetsmatris är inte verifierade. Scenariofilen gör antagandena ersättbara och spårbara.
- En anonym samtidighetspool visar högsta antal samtidiga vakter. Den bevisar inte att samma individer kan bemanna pass med korrekta raster, restider, kompetenser eller arbetstidsvillkor.
- Lokal- och personalkostnader är scenarioproxyer. De är inte avtalade kostnader och innebär ingen påvisad besparing.
