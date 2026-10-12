# Optimeringsstrategi: aggregerad relaxation och exakt kontroll dag för dag

**Status:** analys och avgränsad prototyp. Prototypen är lösningsstrategin `solver.strategy = "decomposed"`; den monolitiska modellen finns kvar som `"monolithic"`. Mätningarna gjordes 2026-10-11–12 på frysta verkliga instanser, och den slutliga koden är frusen i commit `5080899`.

PoC:n ska svara på två frågor: hur mycket lokalbehovet kan minska med bättre schemaläggning, och vad det motsvarar ekonomiskt. I modellen avgörs svaret av två storheter:

- **Lokalportföljen:** vilka salar som används någon gång under terminen (årskostnad per plats).
- **Bemanningspoolen:** den största samtidiga bemanningen (årskostnad per resurs).

Båda är maxvärden över terminen. Därför bestäms kostnaden av de dimensionerande dagarna, inte av hur varje enskild tenta placeras.

Alla belopp nedan är modellkostnader med proxypriserna 1 000 kr per plats och år och 50 000 kr per poolresurs och år. De är inte faktisk kostnad eller verifierad besparing.

## Sammanfattning

1. **Den onödiga beräkningskostnaden.** Den monolitiska modellen skapar variabler för varje tenta × pass × sal, alla salar × alla pass och en bemanningstidslinje per sal och pass. Hela terminen blir 112 071 variabler och 386 834 villkor. Lösaren arbetar lika hårt med varje tenta, fast de flesta dagar inte påverkar kostnaden, och dess undre gräns är svag. För hela vecka 3, vecka 4–14 och hela terminen hittade den ingen giltig lösning alls inom 3–5 minuter. Hela terminen krävde 8 GB minne.
2. **Rekommenderad strategi.** Räkna först ut datum, portfölj och pool i en aggregerad relaxation utan salstilldelning. Den ger en bevisad undre kostnadsgräns. Kontrollera sedan varje dag exakt med den oförändrade gemensamma modellen, begränsad till relaxationens portfölj och pool. Dagar som inte går ihop repareras med grannarna, ger ett snitt tillbaka till relaxationen eller placeras med mer bemanning (övre gräns).
3. **Mätt förbättring (frusen kod).**
   - Hela terminen: en fullständig, oberoende eftervaliderad lösning på 1 823 000 kr med bevisad undre gräns 1 773 000 kr, alltså 2,7 procents gap. Den monolitiska modellen gav ingen lösning alls på samma budget, 5 minuter.
   - Tre av fem parameterändringar avgörs som ogenomförbara på cirka 1 sekund. För de två av dem som den monolitiska modellen också kördes på tog det 26–50 sekunder och 3,5–5 GB.
   - Veckor: bevisat optimum eller 0–9 procents gap, mot 11–36 procent för den monolitiska modellen.
   - Undantag: på det minsta, täta fallet (60 tentor) bevisar den monolitiska modellen optimum på 14 s, medan den nya strategin stannar på 9 procents gap.
4. **Begränsningar och fel som mätningen visade.** Detta är inte rättat i den här PR:en, eftersom koden var frusen.
   - Tidsgränsen hålls inte: hela terminen tog 450 s mot gränsen 300 s.
   - Den frusna versionen kontrollerar två planer per varv. Det gav första fullständiga lösning för hela terminen efter cirka 7,5 minuter, mot 2 minuter i versionen före.
   - Med tre starttider kom ingen lösning inom 3 minuter.
   - Kostnaden varierar mellan körningar med samma kod (upp till 9 procent på en veckoinstans).
   - Antalet flyttade tentor vid samma kostnad varierar kraftigt (106–655 för vecka 4–14).
   - Lokalunderlaget begränsar slutsatsen mer än algoritmen (avsnitt 1).
5. **Minsta implementation.** Tre moduler i `src/tentaoptimering/joint_strategy/` på cirka 730 rader. Den gemensamma modellen, kontraktet och den oberoende eftervalideringen återanvänds oförändrade. Valet görs med en katalogparameter.

### Räcker det för interaktiv användning?

**Delvis.**

Det som redan fungerar interaktivt:
- **Snabb genomförbarhetsbedömning:** en parameterändring som gör terminen ogenomförbar avgörs med bevis på cirka 1 sekund.
- **Stabil undre gräns:** relaxationen bevisar en undre kostnadsgräns för hela terminen på 20–60 sekunder. Gränsen var densamma i alla mätta körningar där den bevisades.
- **Verifierade lösningar:** varje redovisad lösning är fullständig och passerar eftervalideringen.

Det som inte räcker ännu:
- **Fullständig terminslösning tar 2–7,5 minuter** och kan överskrida tidsgränsen. I ett av två genomförbara parameteralternativ (tre starttider) kom ingen lösning alls inom 3 minuter.
- **Små skillnader går inte att skilja från sökningens slump.** Både gapet (2,7–8 procent) och variationen mellan körningar motsvarar en eller flera poolresurser (50 000 kr styck). Skillnader mellan parameteralternativ som är mindre än det kan inte tolkas som verkliga.

En jämförelse mellan parameteralternativ bör därför redovisas som intervall från undre gräns till verifierad kostnad. Innan strategin används interaktivt behöver tidsgränsen hållas och varvtiden kortas, se avsnitt 7.

## 1. Den befintliga modellen

### Beslutsvariabler (`joint_optimizer._build_variables_and_constraints`)

| Variabelgrupp | Antal | Vad den beslutar |
|---|---|---|
| `selected` | Σ kandidatpass per tenta | Vilket pass tentan får |
| `use`, `seats` | Σ kandidatpass × kompatibla salar (två variabler) | Om tentan använder salen i passet, och hur många platser |
| `session`, `occupancy`, `staff`, `end` | salar × alla pass (fyra variabler) | Salstillfälle, beläggning, vakter enligt trappan, sluttid |
| `end_after`, `active`, `active_staff` | salar × pass × överlappande pass samma dag (tre variabler) | Bemanningstidslinjen med förberedelse och avslut |
| `owned`, `staff_pool` | salar + 1 | Portfölj och pool (det som kostar) |

Villkor som växer snabbt:

- byggnadsdelning, ett villkor per par av salar i olika byggnader för varje tenta × pass (O(salar²));
- icke-överlapp per sal och passpar samma dag;
- en trappuppslagning (`AddElement`) per sal och pass med en tabell lika stor som salens kapacitet.

### Tillväxt

Antalet kandidatpass per tenta är ungefär (2 × flyttfönster + 1) × starttider × andelen tillåtna veckodagar. Modellstorleken växer i tre led:

- linjärt i tentor × kandidatpass × salar;
- kvadratiskt i salar för byggnadsdelningen;
- med salar × pass för salstillfällen och tidslinje.

| Instans | Tentor | Pass | Kandidater/tenta | Monolitisk: variabler/villkor | Byggtid | Minne | Relaxation: variabler/villkor |
|---|---:|---:|---:|---:|---:|---:|---:|
| v3, 60 tentor | 60 | 10 | 5,1 | 5 148 / 17 571 | 0,1 s | 0,7 GB | 721 / 830 |
| v3, hela veckan | 285 | 14 | 5,6 | 24 736 / 86 792 | 0,8 s | 2,1 GB | 2 775 / 2 212 |
| v4–14 | 887 | 144 | 5,9 | 87 163 / 299 413 | 6,5 s | 6,4 GB | 11 208 / 12 095 |
| hela terminen | 1 172 | 158 | 5,8 | 112 071 / 386 834 | 7 s | 8,1 GB | 13 987 / 14 307 |
| terminen, flyttfönster ±2 | 1 172 | 158 | 9,6 | – | – | – | 18 402 / 14 449 |
| terminen, tre starttider | 1 172 | 237 | 8,8 | – | – | – | 19 247 / 18 636 |

### Vad som är nödvändigt och vad som är ekonomiskt ointressant

- **Nödvändigt för frågan:** datum per tenta (det bestämmer belastningen per dag), lokalportföljen, poolen och att varje dimensionerande dag faktiskt går att packa i portföljens salar med bemanningen.
- **Ekvivalent eller ointressant:**
  - Placeringen på icke-dimensionerande dagar: när portfölj och pool är givna kostar varje genomförbar placering där lika mycket. På hela terminen gäller det vecka 4–14, alltså 887 av 1 172 tentor. Deras bevisade optimum är 963 000 kr, mot 1 773 000 kr för terminens undre gräns.
  - Hur deltagarna fördelas mellan salar i samma pass när bemanningen blir densamma.
  - Poolens storlek på dagar under toppen.
- **Var lösaren förbrukar tid:**
  - *Första lösning:* 3–68 s för 60–160 tentor, ingen alls för hela vecka 3 (180 s) eller för flera veckor (300 s).
  - *Förbättring:* lösningar förbättras i steg under hela tidsgränsen.
  - *Bevis:* bevis nås bara på 60 tentor. Gränsen ligger 11–36 procent under bästa lösning efter 120 s, eftersom LP-relaxationen av salsägande och trappa är svag.

### Begränsningar som beror på lokalunderlaget, inte på algoritmen

- Bara sju Uppsalasalar har publicerad kapacitet (1 119 platser). Historiken använde fler lokaler, till exempel Danmarksgatan 30 och Fyrishov, som saknar kapacitetsuppgift.
- Vecka 3 har 13 656 deltagare. Den ryms bara genom att använda alla veckodagar inklusive helg och flytta tentor ±1 dag. Med måndag–fredag, utan flytt eller med 10 procent fler deltagare ryms terminen inte alls (bevisat, tabell 5.3).
- Externhyra och egna lokaler är `contract_only`. Modellen kan därför inte pröva att hyra in i stället för att äga, och den kan inte jämföra med den lokalmängd som faktiskt användes historiskt.
- Svaret på fråga 1 begränsas därför i dag till *vilka av de sju salarna som behövs* och *hur många vakter*. Det är inte hur mycket av universitetets totala tentamenslokaler som kan avvecklas. Det är ett datagap, inte en algoritmfråga.

## 2. Prövade metoder

| Metod | Prövad hur | Effekt | Infört? |
|---|---|---|---|
| Aggregerad relaxation (datum + portfölj + pool, utan salstilldelning) | `aggregate.py`, 14 instanser | Bevisat optimum för relaxationen på 0,5–60 s utom vid tre starttider (ej bevisat på 72 s). Undre gränsen är starkare än den monolitiska modellens efter 120 s i alla jämförbara fall. | Ja |
| Exakt kontroll dag för dag | `subproblems.py` | Exakt: den gemensamma modellen separerar per dag när datumen är givna (salbokning, ställtid, bemanningstidslinje och kurskrockar gäller bara samma datum). Icke-dimensionerande dagar kontrolleras på bråkdelar av en sekund. | Ja |
| Reparation av misslyckad dag med grannar (±1 dag) | `decomposed.py` | Lyckades i 7 av 87 försök i spåren. Resten var bevisat omöjliga (45) eller gav inget svar inom 20 s (35), oftast täta dagar i vecka 3. Ett veckoblock (±3 dagar) gav sällan svar inom 30 s och togs bort. | ±1 dag |
| Snitt till relaxationen (logikbaserad Benders) med minsta orsakande tentamängd | `subproblems.infeasible_core` | Giltiga, men lokala. Den undre gränsen höjdes inte i något av de stora fallen; relaxationen flyttar tentor runt snittet. | Ja, tidsbegränsat |
| Tidigt stopp vid tillräckligt gap | `solver.relative_gap_limit` (standard 1 %) | Avbryter när en verifierad lösning ligger nära den bevisade gränsen. I mätningarna nåddes 1 procent bara där optimum bevisades. CP-SAT:s `OPTIMAL` vid gapgräns redovisas inte längre som bevis i den monolitiska modellen. | Ja |
| Historiska placeringar som start | Andra fas i relaxationen som behåller historiska pass vid oförändrad kostnad, plus ledtråd och minsta antal ändringar i dagkontrollen. Den monolitiska modellen startad från historiken mättes inte i den förkortade mätserien. | Färre flyttade tentor (till exempel 655 → 106 för vecka 4–14 i version v2), men planen som behåller historik misslyckas oftare i dagkontrollen. Den frusna versionen kontrollerar därför också den rent ekonomiska planen, vilket fördubblar varvtiden. Den historiska placeringen är inte genomförbar för toppveckorna med dagens sju salar. | Ja |
| Förfiltrering av omöjliga tenta–pass–sal | Granskat | Den befintliga modellen filtrerar redan planeringsområde, tillgänglighet och digitalt krav; med sju kompatibla salar finns lite kvar att ta bort. | Nej |
| Dominans och symmetribrytning | Granskat | Salarna har olika kapacitet och kostnad per plats; det finns inga likvärdiga salar att bryta symmetri mellan. Fördelningssymmetrin mellan salar i samma pass försvinner i relaxationen. | Nej |

## 3. Tre ambitionsnivåer

| Nivå | Vad strategin levererar | Hur det redovisas |
|---|---|---|
| A. Genomförbar | Alla tentor och deltagare placerade, kontrollerade dag för dag med den gemensamma modellen och oberoende eftervaliderade | `technical_validation = pass` |
| B. Bra ekonomisk lösning | Verifierad kostnad, bevisad undre gräns från relaxationen och gap | `feasible_not_proven`, `best_objective_bound_ore`, `relative_gap`. Rapporten anger uttryckligen att kostnaden ligger mellan gränsen och lösningen och inte är bevisad maximal besparing. |
| C. Bevisat optimal | När alla dagar går ihop med relaxationens portfölj och pool är kostnaden lika med en bevisad undre gräns | `optimal` med gap 0 |

Strategin stannar vid nivå B när gapet är högst `solver.relative_gap_limit` och fortsätter mot C bara inom tidsgränsen.

## 4. Verksamhetsparametrarna

Strategin begränsar inte flyttfönster, starttider, veckodagar, lokaler eller andra krav. Varje körning använder samma kandidatpass, salar och hårda villkor som den monolitiska modellen. Relaxationen används bara som gräns och förslag, och varje redovisad lösning kontrolleras med de exakta villkoren.

| Kategori | Parametrar (exempel) | Hantering |
|---|---|---|
| Verifierade hårda villkor | Fysisk kapacitet (källdata), planeringsområde, digitalt krav enligt observation, samma kurskod | Hårda villkor i varje dagkontroll och i eftervalideringen |
| Verksamhetsbeslutade planeringsförutsättningar | Flyttfönster, veckodagar, starttider, tidigaste och senaste tid, spärrade perioder, flyttbara typer, max salar, byggnadsdelning, ställtid | Bestämmer kandidatpassen för en körning; justerbara mellan körningar; ändras aldrig av strategin |
| Explorativa antaganden | Kostnad per plats, kostnad per vakt, bemanningstrappa, förberedelse och avslut, digitala policyer, efterfrågevariation | Påverkar kostnad och genomförbarhet; märks som antaganden i parametrarnas grund |
| Preferenser | Behåll historiskt pass | Andra mål vid oförändrad kostnad; frångås när kostnaden kräver det |

## 5. Experiment

### 5.1 Uppställning

- **Indata.** Frysta `joint_input.json` byggda med produktadaptern (`build_real_subset_problem`) ur `data/processed`. Grundinställningarna är desamma som i `config/scenarios/joint_real_subset.toml`:
  - planeringsområde Uppsala, sju salar (1 119 platser);
  - flyttfönster ±1 dag, veckodagar måndag–söndag (katalogens standard), starttider 08:00 och 14:00, ställtid 30 min;
  - trappa 50/150/300 deltagare → 1/2/3 vakter, förberedelse och avslut 30 min vardera;
  - 1 000 kr per plats och år, 50 000 kr per poolresurs och år.
- **Instanser.** Veckoinstanserna har kalendern begränsad till veckan. Terminsvarianterna ändrar en parameter i taget. Fallen med 60, 120 och 160 tentor är de första tentorna (efter id) i vecka 3, måndag–fredag. Instanserna, mätskripten och alla loggar finns lokalt i `runs/strategiexperiment/` (ignoreras av Git och innehåller härledda verkliga data). De byggs om med `instances.py` och `variants.py`.
- **Dator och mjukvara.** Bärbar dator, Intel Core Ultra 7 165U (12 kärnor, 14 trådar), 31 GB RAM, Windows 11, Python 3.14.5, OR-Tools 9.15.6755. Alla körningar använde 8 trådar, en körning åt gången och ingen annan beräkningslast.
- **Mått.**
  - *Tid till första fullständiga lösning* räknas från processstart, med inläsning av indata (cirka 1 s). För den monolitiska modellen räknas den från lösarens start.
  - *Lokalbestånd* är de salar som används minst en gång, och *pool* är den dimensionerande samtidiga bemanningen.
  - *Eftervalidering* är den oberoende eftervaliderarens tekniska utfall på det sparade resultatet. Verksamhetsverifieringen är `not_evaluated` i samtliga körningar, enligt P-3.

### 5.2 Kodversioner och återanvända resultat

| Version | Kod | Vad som skiljer | Används till |
|---|---|---|---|
| Jämförelsemodell | `joint_optimizer._build_variables_and_constraints`, oförändrad sedan `main` (`afbc022`); mätt med `measure.py` (enbart kostnadsfasen, frö 1, ingen gapgräns) | – | Tabell 5.4. Återanvänd: modellbyggaren är identisk i den frusna versionen. |
| v1 | Arbetskopia 2026-10-11 före rättningarna | Ändringspreferensen i relaxationen verkade inte (startade utan fullständig ledtråd) och det fanns inget tidsskydd | Endast variation (5.5) |
| v2 | Arbetskopia 2026-10-11 | Ändringspreferens och tidsskydd rättade; en plan per varv | Endast variation (5.5) |
| Frusen | Commit `5080899` | Även den rent ekonomiska planen kontrolleras när planen som behåller historik misslyckas | Tabell 5.3. Veckorna kördes 2026-10-11 23:14 efter sista kodändringen (23:11). Övriga kördes 2026-10-12. |

### 5.3 Frusen slutversion

Budgeten är densamma som jämförelsemodellens, utom för de två genomförbara parameteralternativen. **De har 3 minuters budget mot jämförelsemodellens 5 minuter och kan inte jämföras som om förutsättningarna vore lika.**

| Instans | Tentor | Budget | Första fullständiga lösning | Kostnad (kr) | Undre gräns (kr) | Gap | Status | Lokalbestånd | Pool | Eftervalidering (teknisk) | Faktisk tid | Minne |
|---|---:|---:|---:|---:|---:|---:|---|---|---:|---|---:|---:|
| **hela terminen** | 1 172 | 300 s | 459 s | 1 823 000 | 1 773 000 | 2,7 % | `feasible_not_proven` | 6 salar, 1 023 platser | 16 | pass | **450 s** | 1,3 GB |
| v4–14 | 887 | 300 s | 115 s | 963 000 | 963 000 | 0 % | `optimal` | 3 salar, 563 platser | 8 | pass | 115 s | 0,4 GB |
| hela vecka 3 | 285 | 180 s | 142 s | 1 823 000 | 1 773 000 | 2,7 % | `feasible_not_proven` | 6 salar, 1 023 platser | 16 | pass | 180 s | 0,7 GB |
| v3, 60 tentor | 60 | 60 s | 14 s | 558 000 | 508 000 | 9,0 % | `feasible_not_proven` | 2 salar, 308 platser | 5 | pass | 60 s | 0,2 GB |
| v3, 120 tentor | 120 | 120 s | 46 s | 1 065 000 | 1 065 000 | 0 % | `optimal` | 3 salar, 615 platser | 9 | pass | 45 s | 0,5 GB |
| v3, 160 tentor | 160 | 120 s | 107 s | 1 493 000 | 1 365 000 | 8,6 % | `feasible_not_proven` | 5 salar, 943 platser | 11 | pass | 120 s | 0,7 GB |
| v8 | 147 | 120 s | 75 s | 882 000 | 832 000 | 5,7 % | `feasible_not_proven` | 3 salar, 482 platser | 8 | pass | 120 s | 0,4 GB |
| v12 | 157 | 120 s | 51 s | 1 215 000 | 1 135 000 | 6,6 % | `feasible_not_proven` | 4 salar, 715 platser | 10 | pass | 120 s | 0,3 GB |
| v13 | 133 | 120 s | 42 s | 913 000 | 913 000 | 0 % | `optimal` | 3 salar, 563 platser | 7 | pass | 41 s | 0,4 GB |
| terminen, flyttfönster ±2 (**3 min**) | 1 172 | 180 s | 188 s | 1 639 000 | 1 509 000 | 7,9 % | `feasible_not_proven` | 6 salar, 939 platser | 14 | pass | 180 s | 1,1 GB |
| terminen, tre starttider (**3 min**) | 1 172 | 180 s | ingen | – | (1 691 000, ej bevisad) | – | `no_feasibility_conclusion` | – | – | – | 180 s | 0,6 GB |
| terminen, flyttfönster 0 | 1 172 | 300 s | – | – | – | – | `infeasible` (bevisat) | – | – | – | 1,0 s | 0,2 GB |
| terminen, måndag–fredag | 1 172 | 300 s | – | – | – | – | `infeasible` (bevisat) | – | – | – | 1,2 s | 0,2 GB |
| terminen, +10 % deltagare | 1 172 | 300 s | – | – | – | – | `infeasible` (bevisat) | – | – | – | 0,6 s | 0,1 GB |

Kommentarer:

- *Första fullständiga lösning* är tiden när det första varvet avslutats, eftersom en lösning bara redovisas efter ett helt varv. Hela terminen överskred sin budget med 150 s. Spåret visar att ett enskilt delsteg (kontroll av en tät dag i vecka 3, med tidsgräns 10 s) tog cirka fyra minuter. Orsaken är inte utredd, se avsnitt 7.
- Undre gränsen för tre starttider (1 691 000 kr) är relaxationens bästa gräns när tiden tog slut, inte ett bevisat optimum för relaxationen.
- Ingen körning gav tekniskt fel i eftervalideringen. Ogenomförbara körningar och körningar utan slutsats har ingen placering att validera.

### 5.4 Jämförelsemodellen (monolitisk)

| Instans | Budget | Första lösning | Bästa kostnad (kr) | Gräns (kr) | Gap | Status | Minne |
|---|---:|---:|---:|---:|---:|---|---:|
| v3, 60 tentor | 60 s | 2,7 s | 509 000 | 509 000 | 0 % | optimal (14 s) | 0,7 GB |
| v3, 120 tentor | 120 s | 6,9 s | 1 085 000 | 963 000 | 11,2 % | feasible | 1,0 GB |
| v3, 160 tentor | 120 s | 67,8 s | 1 590 000 | 1 250 000 | 21,4 % | feasible | 1,2 GB |
| v8 | 120 s | 10,0 s | 963 000 | 618 000 | 35,8 % | feasible | 1,2 GB |
| v12 | 120 s | 17,0 s | 1 289 000 | 1 043 000 | 19,1 % | feasible | 1,3 GB |
| v13 | 120 s | 12,9 s | 963 000 | 742 000 | 22,9 % | feasible | 1,0 GB |
| hela vecka 3 | 180 s | ingen | – | – | – | ingen slutsats | 2,1 GB |
| v4–14 | 300 s | ingen | – | – | – | ingen slutsats | 6,4 GB |
| **hela terminen** | 300 s | ingen | – | – | – | ingen slutsats | 8,1 GB |
| terminen, flyttfönster 0 | 300 s | – | – | – | – | ogenomförbar (26 s) | 3,5 GB |
| terminen, måndag–fredag | 300 s | – | – | – | – | ogenomförbar (50 s) | 5,1 GB |

Jämförelsemätningen registrerade varken lokalbestånd och pool eller körde eftervalideringen för veckornas lösningar. Den mätte bara kostnadsfasen. Den monolitiska modellen kördes inte på flyttfönster ±2, tre starttider eller +10 procent deltagare.

### 5.5 Observerad variation mellan körningar

**Samma kod (frusen):**

| Instans | Körning 1 (kontroll före mätserien) | Körning 2 (mätserien) |
|---|---|---|
| v3, 120 tentor | optimum 1 065 000 kr på 92 s | optimum 1 065 000 kr på 45 s |
| v3, 160 tentor | optimum 1 365 000 kr på 39 s | 1 493 000 kr, gap 8,6 %, efter 120 s |

**Olika kodversioner, samma indata och budget:**

| Instans | v1 | v2 | Frusen |
|---|---|---|---|
| hela terminen | 1 823 000 / 1 773 000 | 1 823 000 / 1 773 000, första lösning 120 s | 1 823 000 / 1 773 000, första lösning 459 s |
| hela vecka 3 | 1 823 000 / 1 773 000 | 1 823 000 / 1 773 000 | 1 823 000 / 1 773 000 |
| v4–14 | optimum 963 000, 655 flyttade | optimum 963 000, 106 flyttade | optimum 963 000, 651 flyttade |
| v3, 120 tentor | optimum 1 065 000 | 1 145 000 / 1 065 000 | optimum 1 065 000 |
| v8 | 882 000 / 832 000 | 882 000 / 832 000 | 882 000 / 832 000 |
| v12 | 1 215 000 / 1 135 000 | 1 215 000 / 1 135 000 | 1 215 000 / 1 135 000 |
| flyttfönster ±2 (300 s i v1 och v2, 180 s frusen) | optimum 1 509 000 | 1 639 000 / 1 509 000 | 1 639 000 / 1 509 000 |
| tre starttider (300 s i v1 och v2, 180 s frusen) | 1 839 000 / 1 701 000 (363 s) | 1 919 000 / 1 693 000 | ingen lösning |

Vad mätningarna stöder:

- **Undre gränsen är stabil.** När relaxationen bevisades gav den samma gräns i varje körning och version.
- **Den verifierade kostnaden varierar.** Både mellan körningar med samma kod (v3 med 160 tentor: 1 365 000 eller 1 493 000 kr) och mellan versioner. Variationen är i hela poolresurser eller salar, upp till cirka 9 procent.
- **Antalet flyttade tentor vid samma kostnad varierar kraftigt** (106–655 för v4–14).
- Det är för få upprepningar för att ange någon spridning statistiskt. Ett enskilt resultat ska läsas som ”inom intervallet gräns–kostnad”, och skillnader mindre än gapet mellan parameteralternativ ska inte tolkas.

### 5.6 Vilka parameterändringar som påverkar beräkningstiden

- **Ändringar som gör terminen ogenomförbar avgörs snabbast.** Flyttfönster 0, bara vardagar och +10 procent deltagare avgjordes på cirka 1 s.
- **Fler kandidatpass gör det tyngre.**
  - Flyttfönster ±2 dagar (9,6 kandidater per tenta mot 5,8) ger ett tyngre relaxationssteg: 60 s mot 28 s.
  - Tre starttider gör även dagkontrollerna tyngre. Relaxationen blev inte bevisad på 72 s, och ingen fullständig lösning kom inom 3 minuter.
- **Täta dimensionerande dagar** (vecka 3) styr tiden för dagkontroll och reparation. Glesa veckor (v4–14) bevisades optimala på under 2 minuter.

## 6. Korrekthet

- **Relaxationen är en undre gräns.** Varje lösning i den gemensamma modellen ger en lösning i relaxationen med samma portfölj och minst lika stor pool och sessionsbemanning:
  - deltagare som upptar salar vid samma passstart ryms i ägda salar;
  - en tenta som inte får delas över byggnader ryms i en ägd byggnad;
  - salstillfällen som startar i ett pass ligger i olika salar och bemannas enligt trappan;
  - pågående tillfällen begränsas av trappans undre hölje.
- **Snitt är giltiga.** Ett snitt läggs bara när den exakta modellen har *bevisat* att tentorna inte ryms på dagen med portföljens salar, eller kräver minst en viss pool. Fler tentor eller färre salar kan inte göra det lättare. En tidsgräns ger aldrig ett snitt.
- **Dagdelningen är exakt.** Givet datum kopplar den gemensamma modellen bara tentor samma dag. Undantaget är portföljen och poolen, och de räknas om på den sammansatta lösningen.
- **Tester** (`tests/test_joint_strategy.py`):
  - 24 slumpade småfall: relaxationen ligger aldrig över det bevisade optimumet, en ogenomförbar relaxation förekommer bara när den monolitiska modellen också är ogenomförbar, och ett bevisat optimum i den nedbrutna strategin är lika med det monolitiska optimumet. Alla resultat passerar eftervalideringen.
  - Ett tätt fall där snitt behövs och ändå ger samma optimum.
  - Ett handräknat tvådagarsfall.
  - En kontroll av att ett gapbegränsat resultat aldrig redovisas som bevisat.
- **Mätningarna:** alla 10 körningar med placering i den frusna mätserien passerade eftervalideringen tekniskt, liksom alla körningar i v1 och v2. Samtliga mätta lösningar var alltså fullständiga och uppfyllde de hårda villkoren.

## 7. Kvarstående fel, risker och nästa steg

Ordnat efter betydelse för interaktiv användning. Inget av detta är rättat, eftersom koden var frusen för mätomgången.

1. **Tidsgränsen hålls inte.** Hela terminen tog 450 s mot gränsen 300 s, och ett enskilt delsteg med tidsgräns 10 s tog cirka fyra minuter. Orsaken är inte utredd. Möjliga förklaringar är att CP-SAT inte avbryter ett pågående steg, eller att modellbygget och snittberäkningen ligger utanför tidsgränserna. Katalogens hjälptext beskriver därför inte längre tidsgränsen som hård.
2. **Varvtiden fördubblades i den frusna versionen,** eftersom två planer kontrolleras per varv. Första fullständiga terminslösning kom efter 120 s i v2 och efter 459 s i den frusna versionen. Den ekonomiska planen bör kontrolleras först, eller bara för de dagar där planerna skiljer sig.
3. **Tre starttider gav ingen lösning inom 3 minuter.** Tyngre dagkontroller och en relaxation som inte bevisades.
4. **Gapet på dimensionerande dagar** (oftast en poolresurs) kvarstår, eftersom snitten är lokala. Starkare bemanningsgräns i relaxationen för pågående tillfällen kan minska det.
5. **Ändringspreferensen är otillförlitlig:** 106–651 flyttade tentor för samma kostnad. Ett efterföljande steg kan minimera ändringar över hela terminen med fast portfölj och pool.
6. **Små täta fall:** den monolitiska modellen är bättre på 60 tentor. Den finns kvar som val.
7. **Reproducerbarhet:** tidsgränserna per steg är väggtid. Därför ger `solver.deterministic` inte full reproducerbarhet i den nedbrutna strategin.
