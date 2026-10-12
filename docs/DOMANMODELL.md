# Domänmodell (utkast för godkännande)

**Status:** S0-utkast. Fem begrepp, en parameterkatalog, en körnings- och valideringskedja. Lagring: SQLite (inbyggd, ingen databasserver) plus filer för större data. Datakatalogen börjar tom; ingen migrering.

## 1. Begrepp

| Begrepp | Betydelse | Föränderlig? | Ägs av |
|---|---|---|---|
| **Dataunderlag** | Oföränderlig ögonblicksbild av inläst källdata, omfattningsbeslut, tidsmässig täckning per datatyp och känd beläggning | Nej | Systemet (skapas vid inläsning) |
| **Simulering** | Namngivet arbetsobjekt: dataunderlag, vald planeringsperiod och förutsättningsvärden | Ja | Användaren |
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

- En simulering pekar på exakt ett dataunderlag och väljer explicit **planeringsperiod** (`start_date`, `end_date`) inom dokumenterad täckning. Perioden får vara kortare än en termin. Datumvalet avgränsar vilka tentor som omfattas och den tillåtna schemaläggningshorisonten enligt en redovisad gränsregel.
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

**Jämförbarhetsnyckel** = hash av dataunderlag, **vald planeringsperiod och gränsregel**, population (beräkningsbar, regeln "lokal används"), efterfrågemått, avrundning, lokalval, bemanningsparametrar, ställtid, kostnadsantaganden, motor- och katalogversion, *exklusive* flexibilitetsparametrar (`window.*`, `calendar.weekdays`, `calendar.blocked_ranges`, `calendar.start_times`, `flex.movable_types`, `rules.keep_course_order`) och mål (`objective.*`, `solver.*`, `analysis.*`) samt `demand.variation_pct`. Två körningar är jämförbara när nycklarna är lika; Nuläge och simulering delar nyckel.

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
| Kontext | Historiskt bokade placeringar per sal och tidsintervall; observerad beläggning, källans definition och datumtäckning separat från bokning och registrerat antal. |

## 6. Lagringsskiss (SQLite)

```
dataset(id, name, created_at, source_manifest_json, content_hash, status)
simulation(id, name, notes, dataset_id, planning_start_date, planning_end_date, created_at, modified_at, spec_hash, tags)
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

## 10. Frågevyer för lokal och bokad tentamen (PoC)

**Lokalutnyttjande:** användaren väljer sal (stabilt id om tillgängligt) och datumintervall, och ser historiska bokningar som tidsblock per dag/pass med tentakoppling, bokade platser och eventuellt uppmätt utfall. Utnyttjandet kan aggregeras per dag, vecka eller månad. Varje nyckeltal måste ange **nämnare** (t.ex. tillgängliga salstimmar eller bokad platskapacitet), källa och täckning; om någon del inte finns visas *saknas*, aldrig automatiskt noll.

**Tentamensuppslag:** hitta en bokad tentamen via boknings-/tentamens-ID eller sökfält (kurs, datum, m.m.). Visa ursprungligt tillfälle (datum, start/slut, ort, salplaceringar, bokat antal, känd beläggning) och, om en simulerad körning valts, beräknad placering och förändringar. En tentamen kan ha flera salplaceringar. Provisorisk/tvetydig koppling mellan `exam_event_id`, beställning och Ladokaktivitet får inte döljas.

**Datatäckning och import:** lagra start/slut och eventuella luckor per källtyp; kommande leverans anges som 1 januari–30 september med verklig beläggning (år, täckning, mått och kopplingsnycklar verifieras vid import). Det ska gå att inspektera data även utan optimeringskörning. Frånvarande beläggningsuppgifter kan inte räknas som lediga platser.

**Export:** ett framtida bokningssystemanpassat filformat ligger utanför PoC tills importspecifikation/identifierare finns. En enkel CSV/JSON med dokumenterat innehåll är tillåten som frivillig preliminär export; ingen produktionsimport utlovas.
