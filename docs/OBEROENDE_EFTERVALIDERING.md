# Oberoende eftervalidering

Eftervalideraren kontrollerar en sparad terminskörning utan att anropa den konstruktiva placeringsmetoden. Varje körning innehåller därför en kopia av scenariofilen och `model_inputs.json` med de konkreta behov, rum, spårbarhetsrelationer och scopebeslut som placeringsresultatet byggde på. `run_integrity.json` låser den frusna specifikationen, modellindatan och samtliga placeringsartefakter med SHA-256; en ändrad eller saknad artefakt kan aldrig ge tekniskt `pass`.

## Körning

```powershell
.\.venv\Scripts\python.exe -m tentaoptimering.cli validate-term-run --run-id <körnings-id>
```

Kommandot skriver `validation.json` och `validation.md` i samma körningsmapp. Varje regel har status `pass`, `fail`, `not_evaluated` eller `not_applicable`, en orsak och berörda objektidentifierare.

## Kontroller

| Regel | Nuvarande kontroll | Begränsning |
| --- | --- | --- |
| `model_inputs` | Sparade behov och rum har positiva heltalsantal, identifierare och planeringsområden. | Felaktiga modellindata stoppar teknisk godkänning. |
| `run_artifact_integrity` | Hashar den frusna specifikationen, modellindatan och de sparade resultatfilerna. | Äldre körningar utan manifest blir `not_evaluated`; ändrade filer blir `fail`. |
| `assignment_rows` | Fördelningsrader har positiva heltalsantal och kända behovs-, sal- och passidentifierare. | Felaktiga rader får inte maskeras av aggregat. |
| `included_demand_coverage` | Varje inkluderat behov har exakt dess deltagarantal och ett gemensamt startpass. | Gäller endast den valda preliminära omfattningen. |
| `calendar_pass_constraints` | Tentamenslängd ryms i valt pass och passet är tillåtet för behovet. | Kräver att passbehörighet finns i modellindata. |
| `room_capacity` | Summa deltagare per salstillfälle ryms i salens kapacitet. | Kapacitet är fortfarande scenario-/PoC-underlag. |
| `room_time_intervals` | Salintervall jämförs parvis över olika pass, med längsta tentamenslängd och ställtid. | Kontrollerar placeringsresultatet, inte framtida verksamhetsregler. |
| `plan_area` | Behov och sal måste ha samma planeringsområde. | Bygger på tillgänglig ortsinformation. |
| `digital_compatibility` | Kontrollerar sparad matris när digitalt krav och salkapabilitet finns; annars redovisar den aktiv global regel. | Global regel är `assumption_only` utan verifierad matris. |
| `room_availability` | Kontrollerar explicita tillåtna pass per sal; annars redovisar den aktiv global regel. | Global regel är `assumption_only` utan verifierad bokningskalender. |
| `course_program_conflicts` | Kontrollerar överlappande explicita kurs- och programrelationer när policy är aktiv. | Saknad programrelation blir `not_evaluated`, aldrig godkänd kontroll. |
| `aggregate_staffing` | Kontrollerar att den anonyma poolen minst når beräknad maximal samtidighet. | Överbemanning är inte ett regelbrott; ingen individuell vaktplan. |
| `individual_staffing_constraints` | Kontrollerar sparade anonymiserade vaktuppgifter mot trappa, pass, för-/efterarbete, faktiska rastsegment, dygnsvila, daglig arbetstid och byggnadsbyte. | Saknad uppgiftsartefakt eller scenariobaserad regeldata blir `not_evaluated`; en inställnings etikett kan inte göra regeln godkänd. |
| `source_scope_accounting` | Stämmer av att varje källaktivitet har ett sparat scopebeslut och att inkluderade aktiviteter har en efterfrågespårning. | Oavstämda scopevärden blir `fail`. |
| `unresolved_source_activities` | Redovisar identifierare för oavgjorda aktiviteter separat från teknisk placering. | Oavgjord efterfrågan blir `not_evaluated`, aldrig täckt eller implicit exkluderad. |

## Sammanfattande status

`technical_placement_completeness` avser endast hashade körningsartefakter, deltagartäckning, salkapacitet, intervall och ort. `business_feasibility` blir `fail` om en kontrollerad regel bryts och `not_verified` om obligatoriska regler är okontrollerbara eller endast täcks av antaganden. Den kan alltså vara `not_verified` även när 100 procent av inkluderade behov är placerade. Fritextstatus i en scenariofil, exempelvis `program_relation_data_status` eller ett antagandes `status`, används aldrig som bevis för `pass`.
