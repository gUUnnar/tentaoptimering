# Domänmodell (utkast för godkännande)

**Status:** S0-utkast. Fem begrepp, en parameterkatalog, en körnings- och valideringskedja. Lagring: SQLite (inbyggd, ingen databasserver) plus filer för större data. Datakatalogen börjar tom; ingen migrering.

## 1. Begrepp

| Begrepp | Betydelse | Föränderlig? | Ägs av |
|---|---|---|---|
| **Dataunderlag** | Oföränderlig ögonblicksbild av inläst källdata med omfattningsbeslut | Nej | Systemet (skapas vid inläsning) |
| **Simulering** | Namngivet arbetsobjekt: dataunderlag + förutsättningsvärden | Ja | Användaren |
| **Förutsättning** | Ett värde i en simulering, definierat i parameterkatalogen, med grund | Ja | Användaren |
| **Körning** | Genomförd beräkning av en simulering; frusen specifikation | Nej | Systemet |
| **Resultat** | Täckning, resursbehov, belastningskurva, påverkansmått, validering, kostnadsprofil | Nej | Körningen |
| **Referens (Nuläge)** | Körning med samma kedja och all flexibilitet avstängd | Nej | Systemet |

*Mall* (utgångspunkt för ny simulering) är kod som levereras med appen, inte en användarentitet. Termen *scenario* används inte.

## 2. Relationer

```
Dataunderlag 1 ──< Simulering 1 ──< Körning 1 ── 1 Resultat
                         │                │
                         └── Förutsättningsvärden (n)   Körning.roll ∈ {simulering, referens}
```

- En simulering pekar på exakt ett dataunderlag.
- En körning tillhör en simulering och bär en **fryst specifikation**: alla förutsättningsvärden med grund, parameterkatalogens version, dataunderlagets hash, motorversion och slumpfrö.
- En referenskörning skapas automatiskt och återanvänds mellan körningar med samma **jämförbarhetsnyckel**.
- Radering av en simulering tar bort dess körningar; referenser som ingen längre pekar på städas. Dataunderlag raderas bara om ingen simulering använder dem. Radering visar vad som tas bort och kräver bekräftelse.

## 3. Livscykel

| Objekt | Tillstånd |
|---|---|
| Dataunderlag | inläsning pågår → klar \| misslyckad |
| Simulering | utkast; markeras *körd* när en körning är klar; markeras *ändrad sedan körning* om specifikationens hash skiljer sig från senaste körningens |
| Körning | köad → pågår → klar \| misslyckad \| avbruten. Vid start av appen blir *pågår* → *avbruten* |

En ändring av en simulering ändrar aldrig en körning.

## 4. Specifikation och jämförbarhet

**Fryst specifikation** = kanonisk JSON av alla förutsättningsvärden (id, värde, grund, motivering), katalogversion, dataunderlagets hash, motorid och version, slumpfrö. Hashen av specifikationen är körningens identitet för reproducerbarhet.

**Jämförbarhetsnyckel** = hash av dataunderlag, population (beräkningsbar, regeln "lokal används"), efterfrågemått, avrundning, lokalval, bemanningsparametrar, ställtid, kostnadsantaganden, motor- och katalogversion, *exklusive* flexibilitetsparametrar (`window.*`, `calendar.weekdays`, `calendar.blocked_ranges`, `calendar.start_times`, `flex.movable_types`, `rules.keep_course_order`) och mål (`objective.*`, `solver.*`, `analysis.*`) samt `demand.variation_pct`. Två körningar är jämförbara när nycklarna är lika; Nuläge och simulering delar nyckel.

När `demand.variation_pct` ≠ 0 skapas två referenser: Nuläge med dagens efterfrågan och Nuläge med ändrad efterfrågan. Skillnaden mellan dem är efterfrågeeffekten; skillnaden mellan Nuläge med ändrad efterfrågan och simuleringen är planeringseffekten.

## 5. Innehåll i Dataunderlaget

| Del | Innehåll |
|---|---|
| Källmanifest | Filnamn, hashar, radantal, inläsningstid |
| Behov | Tentamenstillfällen (`exam_demand`): datum, starttid, längd, ort, kurskod, tentamenstyp, institutionskod, `uses_room` (härlett ur bokningen), deltagarantal med `count_basis` |
| Delgrupper | Delgrupp per behov och relation aktivitet → delgrupp, via `canonical_demand` (enda väg för att bilda behov) |
| Population | Inläst, beräkningsbar (1 258), delade tillfällen (separat), kvarstående gap med orsakskod |
| Lokaler | Rum med publicerad kapacitet, grund och källa; observerade bokningar per lokal som kontext; lokaler utan kapacitet markerade som datagap |
| Kvalitet | Avvikelser: bokningar över publicerad kapacitet, ej identifierade placeringar, kontrollsummor |
| Kontext | Historiskt bokade platser och faktisk lokalanvändning per dag |

## 6. Lagringsskiss (SQLite)

```
dataset(id, name, created_at, source_manifest_json, content_hash, status)
simulation(id, name, notes, dataset_id, created_at, modified_at, spec_hash, tags)
simulation_value(simulation_id, parameter_id, value_json, basis, rationale)
run(id, simulation_id NULL, role, spec_json, spec_hash, comparability_key,
    status, progress_json, engine_version, started_at, finished_at, error_text)
```

Filer: `datasets/<id>/…` (tabeller, manifest) och `runs/<id>/…` (placeringar, salstillfällen, vaktuppgifter, resultat, validering). Databasen har versionsnummer (`PRAGMA user_version`); någon annan migreringsmotor behövs inte.

## 7. Planeringskedja

1. **Planeringsproblem** byggs ur dataunderlag + specifikation: tentor med originaltillfälle, deltagarantal efter variation, längd, ort, kurskod, typ, flyttbarhet.
2. **Steg A (CP-SAT):** välj tillfälle per tentamen; minimera samtidiga platser, därefter antal flyttar. Redovisar gap.
3. **Steg B:** realisera det fasta schemat i vald lokalportfölj; brist redovisas, ingen lokal uppfinns.
4. **Steg C:** bemanning av salstillfällena.
5. **Resultat** och **fristående validering**.

Nuläge och simulering kör samma steg med samma kod.

## 8. Valideringsmodell

Per regel: `pass`, `fail`, `not_evaluated` eller `not_applicable`, med skäl och berörda objekt. Två axlar, alltid skilda: **teknisk placering** (alla tentor placerade, kapacitet, intervall) och **verksamhetsmässig genomförbarhet**. Verifieringsstatus härleds ur parametergrund och dataunderlagets bevis, aldrig ur ett värde användaren skrivit. Regler vars parametrar ingen motor läser är `not_evaluated`. Studentkrockar är `not_evaluated` med skäl och visas som en fotnot. Kalenderregler är `not_applicable` för oflyttbara tentor.

## 9. API-resurser (substantiv)

`/api/dataunderlag`, `/api/simuleringar` (med `/{id}/kopia`, `/{id}/forutsattningar`, `/{id}/korningar`), `/api/korningar/{id}` (med `/resultat`, `/validering`, `/avbryt`), `/api/jamforelser`, `/api/parameterkatalog`, `/api/mallar`. Typerna för frontend genereras ur OpenAPI. Källdatakatalogen väljs i applikationen (inbyggd mappväljare i den nya appen, byggd som del av dataunderlagets inläsning).
