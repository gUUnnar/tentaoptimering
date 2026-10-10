# Oberoende eftervalidering av gemensamma körningar

Paket: `src/tentaoptimering/joint_validation/`. Gäller `joint-optimization-input-v2` och `joint-optimization-result-v2`.

## Princip

Valideraren läser bara de sparade artefakterna `joint_input.json`, `joint_result.json` och `joint_manifest.json`. Den kör aldrig optimeraren och importerar ingen regel-, bemannings- eller kostnadskod från den. Enda delade symboler är kontraktets versionskonstanter (`INPUT_SCHEMA_VERSION`, `RESULT_SCHEMA_VERSION`). Ett AST-test (`tests/test_joint_validation.py`) låser detta. Bemanningstrappa, salstillfällen, samtidig bemanning och kostnader räknas om från rå JSON.

Tre axlar redovisas åtskilda, jämte solverns eget utfall som bara återges:

| Axel | Frågar | Värden |
|---|---|---|
| Solverstatus | Vad påstod solvern (`optimal`, `feasible_not_proven`, `infeasible`, ...)? | Återges, bevisas inte |
| Teknisk eftervalidering | Uppfyller placeringen alla kontrollerbara regler i indata? | `pass`/`fail`/`not_evaluated`/`not_applicable` |
| Verksamhetsverifiering | Vilar reglerna på verifierad grund med motorstöd? | samma statusvärden |
| Proveniens | Är filer, versioner och underlag oförändrade? | samma statusvärden |

Regelstatus: `fail` om något regelbrott finns, `not_evaluated` när bevis eller motorstöd saknas, `pass` bara när regeln faktiskt prövats och hållit, `not_applicable` när regeln saknar objekt. En regel utan underlag blir aldrig `pass`. Teknisk korrekthet ger aldrig verksamhetsverifiering automatiskt: verifieringen härleds ur parametrarnas `basis` och `engine_support`, inte ur värden som en användare kan skriva.

## Regelkatalog (46 regler)

Teknisk: efterfrågan och omfattning (varje behov exakt en gång, alla deltagare placerade, summor per tenta/sal, ingen dubbelräkning, hemtentor utan sal, täckning korrekt rapporterad, omfattning redovisad, ingen partiell placering vid ogenomförbarhet); kalender (fasta tentor behåller historik, `slot_end_limit` för det valda passets egen sluttidsgräns, flyttbara följer fönster/veckodag/spärrdatum/starttid/senaste sluttid, referenspass är inte tillåtet val, passkatalog, kandidatgenerering, kurskrockar och uttryckliga konfliktgrupper); salar (välformade rader, planeringsområde, kapacitet, tillgänglighet, salar per tenta, byggnadsdelning, ställtid och dubbelbokning, digital kompatibilitet enligt indata, omräknade salstillfällen); bemanning (behov per salstillfälle enligt trappan vid alla gränser, pool täcker samtidig topp inklusive förberedelse/avslut, pool ej uppblåst); kostnad (fasta lokalkostnader, externa pass, pool, rörliga kostnader, komponenter summerar till rapporterad totalkostnad, antal flyttade tentor, konsistent solverrapport).

Verksamhet: kalender-, lokal-, bemannings-, kostnads- och efterfrågegrund; populationens fullständighet; studentöverlapp; verifierad digital kompatibilitet; samtentors disjunkthet; parametrar utan motorstöd.

Proveniens: artefakter finns och är läsbara, manifestets hashar, kontraktsversioner, resultat hör till indata, dataset-, konfigurations- och katalog-hash, rådatahashar.

## Användning

`optimize-joint` kör valideringen automatiskt och skriver `joint_validation.json` (maskinläsbart, schema `joint-validation-v1`) och `joint_validation.md`; sammanfattningen läggs även i `joint_report.md`. Vid tekniskt brott returneras status `technical_validation_failed` (exitkod 3) men solverns resultat och status lämnas orörda.

```bash
python -m tentaoptimering.cli validate-joint-run --run-id <id> --config config/scenarios/joint_real_subset.toml --source-dir <underlag>
```

Utan `--processed-dir`, `--config`, `--source-dir` bedöms motsvarande hashregler `not_evaluated`, inte `pass`. Kommandot skriver bara valideringsfilerna.

## Verklig körning: 12 tentor (reproducerbar med `config/scenarios/joint_real_subset.toml`)

Solver `optimal`, kostnad 37 900 000 öre, pool 3, 4 flyttade tentor. Teknisk validering `pass` (26 regler, `non_room_demands` och `fixed_exams_keep_history` är `not_applicable`), proveniens `pass` (8 regler, inklusive rådatahashar), verksamhetsverifiering `not_evaluated`: alla tio regler.

| Verksamhetsregel | Status | Skäl |
|---|---|---|
| kalender-, lokal-, bemannings-, kostnads-, efterfrågegrund | not_evaluated | parametrar vilar på antaganden/experiment eller saknar motorstöd |
| population_completeness | not_evaluated | 266 av 1 525 källaktiviteter är oavgjorda och ligger utanför |
| student_overlap | not_evaluated | ingen studentdata och inget motorstöd |
| digital_compatibility_verified | not_evaluated | 6 digitala behov; ingen verifierad kompatibilitetsmatris |
| group_disjointness | not_evaluated | 1 samtenta antar disjunkta grupper |
| unsupported_parameters | not_evaluated | 23 parametrar saknar motorstöd |

## Kvarstående datagap och ej verifierbara regler

- Studentöverlapp och programkrockar: bara kurskod och explicita konfliktgrupper prövas.
- Digital kompatibilitet prövas mot indatans kapabilitet; faktisk periodtillgänglighet är okänd.
- Samtentors disjunkthet och oavgjorda aktiviteter är antaganden, inte verifierade.
- Arbetstidsvillkor (raster, dygnsvila, individuell planering) saknar motorstöd; anonym samtidig pool prövas endast.
- Kostnadsparametrar är delvis antagna; kostnad verifieras som aritmetik, inte som faktisk kostnad.

## Testunderlag

`tests/test_joint_validation.py`: handräknat referensfall (5 salstillfällen, pool 3, kostnad 19 600), 34 injicerade fel som var och en måste flaggas av förväntad regel, gränsfall (kapacitet, ställtid, trappgränser, förberedelse/avslut, senaste sluttid), bevis kontra brott och integritet. `test_joint_validation_run.py`: körflöde, CLI och regression mot verkliga delmängden. `test_joint_validation_differential.py`: 40 slumpade småfall. Mutationsprov av själva valideraren: 38 av 38 mutanter fångades.

## Rättningar efter granskning av PR #8

- Ett resultat med utfall `optimal`/`feasible_not_proven` men tomt schema behandlas som en lösning och faller på `each_demand_scheduled_once`; det får inte längre bli tekniskt godkänt.
- Nya regeln `slot_end_limit` kontrollerar för alla tentor (även oflyttbara) att sluttiden ryms i det valda passets egen `latest_end_minute`, utöver den globala senaste sluttiden.
- Verksamhetsgrund-regler blir `not_evaluated` om någon av gruppens parametrar saknar definition i indata (tidigare räckte att någon fanns). `calendar.turnaround_minutes` ingår nu i lokalgruppen.
- Trasiga schema-, placerings- eller salstillfällesrader ger regeln `input_wellformed` = `fail`; övriga regelgrupper skyddas så att ett oväntat fel blir en `fail`-regel i rapporten i stället för ett programfel.
