# Omfattningsrapport för Ladokaktiviteter

Varje Ladokaktivitet redovisas i `demand_scope.csv` med ett scope-beslut, en orsak och evidensreferens.
En oavgjord aktivitet får inte räknas bort och förhindrar en fullständig verksamhetsberäkning.

## Mätvärden

| Mått | Värde |
|---|---:|
| `source_activity_count` | 1525 |
| `included_activity_count` | 1259 |
| `excluded_activity_count` | 0 |
| `unresolved_activity_count` | 266 |
| `scope_complete_for_whole_population` | False |
| `scope_decision_basis_counts` | {"technical_preparation": 1524, "not_assessed": 1} |

## Tolkning

- `included` i den första rapporten betyder endast inkluderad i uttrycklig teknisk PoC-omfattning. Ett verksamhetsbeslut krävs innan den får beskrivas som slutligt inkluderad.
- Flera aktiviteter kan tillhöra samma delgrupp; delgruppen äger deltagarantalet så att samma tentander inte dubbelräknas.
- `excluded` måste ha en dokumenterad verksamhetsorsak och evidens, exempelvis digital examination utanför vald fysisk omfattning.
- `unresolved` är synligt i rapporten och blockerar påståenden om full täckning för hela populationen.
