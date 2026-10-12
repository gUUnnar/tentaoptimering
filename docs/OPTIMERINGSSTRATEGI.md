# Optimeringsstrategi: aggregerad relaxation och exakt kontroll dag för dag

**Status:** analys och avgränsad prototyp; avsnitt 9 beskriver PR #10 (parallella dagkontroller och varmstart). Prototypen är lösningsstrategin `solver.strategy = "decomposed"`; den monolitiska modellen finns kvar som `"monolithic"`. Mätningarna i avsnitt 5 gjordes 2026-10-11–12 med koden frusen i commit `5080899`. Rättningarna efter granskningen av PR #9 och deras riktade kontroller redovisas i avsnitt 8.

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
4. **Begränsningar och fel som mätningen visade.** Status efter rättningarna står i avsnitt 8.
   - Tidsgränsen hölls inte: hela terminen tog 450 s mot gränsen 300 s. *Efter rättning:* 302 s.
   - Den frusna versionen kontrollerade två hela planer per varv, så första fullständiga terminslösning kom efter cirka 7,5 minuter. *Efter rättning:* 134 s.
   - Med tre starttider kom ingen lösning inom 3 minuter. *Efter rättning, med varmstart från en tidigare lösning:* 39 s.
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
- **En fullständig terminslösning tar cirka 2 minuter** utan varmstart (134 s efter rättningarna). Med varmstart från en tidigare eftervaliderad lösning tar den 39 s, när den nya instansen tillåter alla tidigare placeringar. Varmstarten är ännu inte kopplad till kommandoraden eller gränssnittet.
- **Små skillnader går inte att skilja från sökningens slump.** Både gapet (2,7–8 procent) och variationen mellan körningar motsvarar en eller flera poolresurser (50 000 kr styck). Skillnader mellan parameteralternativ som är mindre än det kan inte tolkas som verkliga.

En jämförelse mellan parameteralternativ bör därför redovisas som intervall från undre gräns till verifierad kostnad. Efter rättningarna i avsnitt 8 hålls tidsgränsen i den kontrollerade körningen, och första lösningen kommer snabbare. Det som återstår för interaktiv användning står i avsnitt 7.

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

- *Första fullständiga lösning* är tiden när det första varvet avslutats, eftersom en lösning bara redovisas efter ett helt varv. Den mättes från processstart, med cirka 10 s import och inläsning av den stora indatafilen. Faktisk tid mättes från lösarens start. Det förklarar att hela terminen har 459 s till första lösning men 450 s total tid: det första varvet slutade först vid tidsgränsen. Efter rättningen mäts båda från lösarens start, och tiden till första lösning står i `raw_status`. Hela terminen överskred sin budget med 150 s. Spåret visar att ett enskilt delsteg (kontroll av en tät dag i vecka 3, med tidsgräns 10 s) tog cirka fyra minuter. Orsaken är inte utredd, se avsnitt 7.
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

Ordnat efter betydelse för interaktiv användning, efter rättningarna i avsnitt 8.

1. **Varmstarten är inte inkopplad i kommandoraden eller gränssnittet.** *Åtgärdat i PR #10 (avsnitt 9):* `optimize-joint --warm-start auto|none|RUN_ID`. Gränssnittet har skrivskyddade ändpunkter men ingen vy.
2. **Dagkontrollerna körs i tur och ordning.** Mätt på 73 dagar (varmstartskontrollen för tre starttider): 77 s med 8 CP-SAT-trådar per dag, 51 s med en tråd, 18 s med 4 dagar parallellt och 2 trådar var, och 11 s med 8 dagar parallellt och en tråd var. Alla dagar fick samma utfall. Parallella dagkontroller är den största återstående tidsvinsten. *Infört i PR #10 (avsnitt 9), med lägre vinst än i provet: 2,4–3,1 gånger på samma 73 dagar.*
3. **Gapet på dimensionerande dagar** (oftast en poolresurs) kvarstår, eftersom snitten är lokala. Starkare bemanningsgräns i relaxationen för pågående tillfällen kan minska det.
4. **Antalet flyttade tentor är fortfarande högre än nödvändigt** (300 för hela terminen i kontrollkörningen, varav 56 tvingade). Förslag i avsnitt 8.5.
5. **Tre starttider utan varmstart:** relaxationen blir inte bevisad på 72 s och de täta dagarna i vecka 3 tar slut på tid. Utan en tidigare lösning är resultatet fortfarande osäkert på 3 minuter.
6. **Ett CP-SAT-anrop kan inte avbrytas utifrån.** Fyraminutersstoppet i den frusna körningen kunde inte återskapas (avsnitt 8.2). Om det beror på ett enskilt anrop som hänger, är det enda sättet att garantera tidsgränsen att köra anropet i en separat process som kan avslutas.
7. **Små täta fall:** den monolitiska modellen är bättre på 60 tentor. Den finns kvar som val.
8. **Reproducerbarhet:** tidsgränserna per steg är väggtid. Därför ger `solver.deterministic` inte full reproducerbarhet i den nedbrutna strategin.

## 8. Rättningar efter granskning av PR #9 (2026-10-12)

Verifierat med riktade tester och två större kontrollkörningar, inte med en ny mätserie.

### 8.1 Kostnadskorrekthet: extern salhyra (rättat)

`external_session_cost_ore` saknades i både relaxationens och dagkontrollernas mål. Det gjorde att den nedbrutna strategin kunde välja en dyrare lösning än den monolitiska.

- **Relaxationen** räknar nu en extern kostnad för varje sal som används i ett pass. Gränsen förblir giltig: varje salstillfälle i en verklig lösning motsvarar en använd sal i relaxationen.
- **Dagkontrollerna** minimerar alla kostnader per tillfälle (rörlig bemanning och extern hyra) i båda lägena.
- **Gränsbeviset för poolen** används bara när poolen är den enda kostnaden.

Tester:

- **Handräknat fall:** en tenta per dag, egen sal för 1 000 öre per år eller inhyrd sal för 400 öre per tillfälle. Över två dagar vinner inhyrning (900 öre totalt), över tre dagar den egna salen (1 100 öre). Båda strategierna och relaxationens gräns ger exakt dessa värden.
- **12 slumpade fall med slumpad extern kostnad:** gränsen ligger aldrig över det monolitiska optimumet, och ett bevisat optimum är lika med det monolitiska.
- **Kontroll:** testerna fallerar på den tidigare koden (relaxationens gräns blev 100 i stället för 900 och 1 100).

### 8.2 Tidsgränsen (rättat i kontrollkörningen; orsaken till det tidigare stoppet ej fastställd)

Gemensam tidsbudget:

- Varje delsteg får sin egen budget men aldrig mer än vad som återstår till körningens deadline.
- Modellbygget räknas in, så CP-SAT får bara den tid som återstår efter bygget.
- Ett delsteg startas inte med mindre än 0,5 s kvar.
- Relaxationens bygge räknas in i dess budget.
- En körning som missar deadline cachas inte.

Instrumentering: varje delsteg loggar byggtid och CP-SAT:s faktiska lösningstid separat. En varning skrivs om CP-SAT överskrider sin gräns med mer än 1 s.

Kontrollkörning av hela terminen med 300 s budget:

- total tid 302 s (tidigare 450 s);
- alla CP-SAT-anrop höll sin gräns med högst 0,3 s marginal;
- modellbyggena tog högst 0,8 s (relaxationen) och 0,4 s (ett femdagarsblock).

Tid per delsteg i körningen:

| Delsteg | Tid | Anrop |
|---|---:|---:|
| Dagkontroll | 102 s | 144 |
| Snitt | 60 s | 6 |
| Historikbyte | 53 s | 85 |
| Reparation | 20 s | 1 |
| Diagnos | 10 s | 7 |
| Relaxation | cirka 55 s | 2 varv |

Fyraminutersstoppet i den frusna körningen kunde inte återskapas, och orsaken är inte fastställd. Filtiderna visar att den frusna mätserien gick utan avbrott (07:55–08:13). Datorns viloläge senare samma morgon påverkade alltså inte den.

Moment som inte kan avbrytas omedelbart:

- modellbygget (mätt högst 0,8 s);
- CP-SAT:s stopp efter tidsgränsen (mätt högst 0,3 s);
- uttag och kostnadsberäkning av en lösning (under 0,1 s).

Ett CP-SAT-anrop som av någon anledning inte stannar kan inte avbrytas från samma process.

### 8.3 Inga dubbla terminskontroller (rättat)

Relaxationens ekonomiska plan kontrolleras först och ger den första fullständiga lösningen.

Därefter tar relaxationen fram en plan som behåller fler historiska pass, med *samma* lokalportfölj och högst samma pool. Den prövas bara för de dagar där planerna skiljer sig:

- Tentor som planerna lägger olika dagar binder ihop de dagarna till grupper.
- En grupp byts in bara om alla dess dagar klarar den exakta kontrollen och totalkostnaden inte ökar.
- Kostnadskorrektheten påverkas inte: kostnaden kan bara bli lika eller lägre.

| Hela terminen | v2 | Frusen | Rättad |
|---|---:|---:|---:|
| Första fullständiga lösning | 120 s | 459 s* | 134 s |
| Kostnad | 1 823 000 kr | 1 823 000 kr | 1 823 000 kr |
| Undre gräns | 1 773 000 kr | 1 773 000 kr | 1 773 000 kr |

\* Mätt från processstart.

I kontrollkörningen byttes 5 av 6 grupper in i första varvet. Eftervalideringen gav `pass`.

### 8.4 Tre starttider och varmstart (analyserat; varmstart infört i biblioteket)

Varför ingen lösning kom inom 3 minuter (spåret från den frusna körningen):

1. Relaxationen blir större (19 247 variabler mot 13 987) och var inte bevisad efter sina 72 s. Den gav en svagare gräns och ingen historikplan.
2. Varje dagmodell blir tyngre med tre pass per dag, eftersom salstillfällen och bemanningstidslinje växer med antalet pass.
3. Två täta dagar i vecka 3 tog slut på tid (10 s vardera), och kontrollen av övriga dagar hann inte klart före deadline. Utan en komplett kontrollerad plan finns inget resultat.

Varmstart: `solve_joint_optimization(problem, start)` tar ett tidigare sparat resultat.

- Om varje tentas tidigare pass fortfarande är tillåtet och salarna finns kvar, kontrolleras placeringen dag för dag med den exakta modellen och blir första övre gräns.
- Annars används den inte. Den litas aldrig på utan kontroll.
- Den monolitiska modellen använder placeringen som ledtråd.
- Tester:
  - Ett tidigare optimum med fasta datum ger en giltig start i en friare instans, och resultatet blir det handräknade optimumet.
  - En placering som instansen inte längre tillåter ignoreras: fel dag, saknad tenta eller borttagen sal.

Kontrollkörning: tre starttider, 180 s, varmstart från den frusna terminslösningen (två starttider).

| | Utan varmstart (frusen) | Med varmstart (rättad) |
|---|---|---|
| Första fullständiga lösning | ingen inom 180 s | 39 s |
| Kostnad | – | 1 823 000 kr |
| Undre gräns | – | 1 687 000 kr (relaxationen ej bevisad) |
| Gap | – | 7,5 % |
| Eftervalidering | – | `pass` |

Ingen billigare lösning hittades inom tiden. Det är därför oavgjort om tre starttider sänker kostnaden.

### 8.5 Tidsmätningen och antalet flyttade tentor

- **459 s mot 450 s:** se kommentaren till tabell 5.3. Tiden till första lösning räknades från processstart, totaltiden från lösarens start, och första varvet slutade vid tidsgränsen. Nu mäts båda från lösarens start.
- **Varför flyttantalet varierar.** När portfölj och pool är givna är alla genomförbara placeringar på icke-dimensionerande dagar lika dyra. Relaxationens första lösning väljer bland dem utan hänsyn till historiken.
  - Historikfasen är tidsbegränsad och verkade inte alls i v1 (655 flyttade).
  - I den frusna versionen klarade historikplanen inte dagkontrollen för vecka 4–14 (651 flyttade). Den ekonomiska planen accepterades då oförändrad.
  - Gruppbytet i 8.3 räddar nu de delar av historikplanen som klarar kontrollen. Hela terminen fick 300 flyttade, varav 56 tvingade, eftersom deras historiska pass inte är tillåtna.
- **Föreslagen billig förbättring (inte implementerad):** när portfölj och pool är fastställda är kostnaden låst. Lös därför om varje grupp av dagar där tentor flyttats, inklusive ±1 dag, med den exakta modellen. Lås salarna till portföljen och poolen till sitt värde, och minimera bara antalet flyttade tentor. Varje block är litet, blocken kan köras parallellt och ett block byts bara in om det klarar kontrollen. Det ger ett lokalt minimum av flyttar till oförändrad kostnad.

### 8.6 Parallellisering

Ja, det går. Dagarna är oberoende givet datum, portfölj och pool. CP-SAT släpper Pythons GIL under lösningen, så flera dagar kan lösas samtidigt i trådar.

Mätt på 73 dagars varmstartskontroll:

| Uppställning | Tid |
|---|---:|
| Sekventiellt, 8 CP-SAT-trådar per dag (dagens uppställning) | 77 s |
| Sekventiellt, 1 tråd per dag | 51 s |
| 4 dagar parallellt, 2 trådar var | 18 s |
| 8 dagar parallellt, 1 tråd var | 11 s |

Alla dagar fick samma utfall i alla fyra. Små dagmodeller tjänar alltså mer på att köras parallellt än på flera trådar per modell. Relaxationen och de få täta dagarna har fortsatt nytta av flera trådar. Detta är inte infört i den här PR:en (avsnitt 7, punkt 2).

## 9. PR #10: parallella dagkontroller och varmstart som normal väg

Detta steg handlar om genomförandets effektivitet. Parametrar, kostnadsdefinitioner, verksamhetskrav och relaxationens och dagmodellens villkor är oförändrade. Mätningarna gjordes 2026-10-12 på samma dator och med samma frysta instanser som i avsnitt 5 (8 trådar, en körning åt gången). De körningar som redovisas som slutliga använder koden i den slutliga commiten, utom där det anges.

### 9.1 Vad som ändrats

**Gemensam budget för trådar och minne** (`joint_strategy/resources.py`).
- Körningen har ett antal CP-SAT-trådar (standard: scenariots `solver.workers`; `--threads` ändrar) och en minnesgräns (`--memory-mb`; standard hälften av ledigt minne).
- Ett batch oberoende dagkontroller delar trådarna: samtidiga kontroller × trådar per kontroll överstiger aldrig budgeten. Åtta kontroller får alltså inte åtta trådar var.
- Minnet uppskattas per kontroll ur modellens storlek (konstanterna är grovt kalibrerade, se 9.6) och begränsar antalet samtidiga kontroller.
- Uppdelningen beror bara på batchens storlek, inte på vilken kontroll som blir klar först.

**Vilka kontroller som körs parallellt.**
- Parallellt: dagkontrollerna i `verify` (en per dag), omkontrollen vid varmstart och dagkontrollerna för historikbytet.
- Sekventiellt: diagnos och reparation av misslyckade dagar. De delar granndagar och cacheposter, och är få.
- Antalet samtidiga kontroller är det största `trådar/2^k` där varje plats får minst två kontroller. En kontroll med en tråd är flera gånger långsammare än med åtta, och små batcher fick annars en lång svans. Första versionen delade alltid upp i en tråd per kontroll. Det gjorde `w13` långsammare (17,8 s mot 6,9 s sekventiellt) och `w8` fick sämre lösning i den mätningen (1 010 000 mot 855 000 kr). Den versionen rättades innan slutmätningen.
- En kontroll som tar slut på tid med färre trådar upprepas ensam med alla trådar innan den räknas som misslyckad.

**Deterministisk sammanställning.**
- Resultaten läggs in i begärd ordning, aldrig i färdigordning.
- Cache, statistik och räknare uppdateras bara i huvudtråden.
- Dubbletter i ett batch löses en gång.
- En kontroll som missar deadline eller avbryts cachas inte och ger aldrig ett snitt.

**Fel och avbrott.**
- Om en kontroll kastar fel stoppas de andra, trådarna avslutas och felet från den lägst numrerade kontrollen kastas, oavsett vilken som föll först.
- `CancelToken` stoppar pågående CP-SAT-anrop med `StopSearch`, och inga nya startar.
- Ctrl+C i kommandoraden stoppar lösaren och sparar den bästa fullständiga, verifierade lösningen hittills. Den redovisas som `feasible_not_proven` med `_cancelled` i `raw_status`, eller som `no_feasibility_conclusion` om ingen lösning fanns. En partiell placering skrivs aldrig.
- Ett andra Ctrl+C avbryter utan att spara.

**Varmstart** (`joint_strategy/warm_start.py`, `joint_warm_start.py`, `joint_inputs.py`, `cli.py`).
- *Val av startkörning.* `--warm-start auto` (standard) tar den senaste användbara körningen av samma `problem_id` bland de fem nyaste. `none` stänger av, och ett körnings-id väljer en bestämd körning. Endast sparade körningsartefakter och deras id används.
- *Krav på kandidaten.*
  - Filerna stämmer med manifestets SHA-256.
  - Resultatversionen är känd.
  - Det finns en fullständig placering.
  - **Den oberoende eftervalideringen körs på nytt** och måste ge teknisk `pass`. En sparad `joint_validation.json` godtas aldrig, och en sparad underkänd status utesluter kandidaten. Kontrollen tog 1,0 s på hela terminen.
- *Omkontroll mot de nya reglerna.* Lösaren kontrollerar varje dag exakt med fasta pass och den nya instansens salar, kapacitet, bemanningstrappa, kurskrockar och ställtid.
  - Kostnad, pool och lokalbestånd räknas om med de nya priserna.
  - Placeringen blir första övre gräns bara om alla dagar klarar kontrollen. Omkontrollen får använda högst hälften av tidsgränsen.
- *Delvis återanvändning.* Om placeringen inte kan återanvändas som helhet ges de tentor vars tidigare pass fortfarande är tillåtna som ledtråd till relaxationen. Tidigare fick tentor utan tidigare placering en ledtråd om att inte läggas någonstans; det är rättat.
- *Redovisning.*
  - Beslutet och skälen sparas i `joint_warm_start.json` i den nya körningen, och källkörningens id och hash i dess manifest.
  - Beslutet står även i rapporten och i CLI-utdata: accepterad, avvisad eller endast ledtråd. Skälen är t.ex. "N tentors tidigare pass tillåts inte längre", "tentorna ryms inte längre på dagen (bevisat ogenomförbart)", "tentor saknar tidigare placering" och saknade salar.
  - Ändrade parametrar sedan startkörningen listas, och om underlaget skiljer sig anges det.
- *Fallback.* En avvisad varmstart ger samma optimering som utan start. Testerna jämför kostnaden med en kall körning.

**Gränssnitt (förberett, ingen vy).** `GET /api/runs/{run_id}/warm-start` och `GET /api/joint-runs/warm-start-candidates` läser sparade artefakter. Det finns inget separat lagringssystem. Gränssnittet kör ännu bara den äldre termmotorn.

### 9.2 Korrekthet

- **Kostnadsfunktion och tillåtna lösningar är oförändrade.** Dagmodellen, relaxationen och kostnadsberäkningen är samma kod. Parallelliseringen och varmstarten ändrar bara när och i vilken ordning kontroller körs, och vad som är första sökpunkt.
- **En sparad lösning godkänns aldrig av tidigare status.** Se kandidatkraven och omkontrollen ovan. Den nya körningen eftervalideras dessutom oberoende som alla körningar.
- **Tester** (`tests/test_joint_parallel_checks.py`, `tests/test_joint_warm_start.py`; hela sviten: 211 tester gröna):
  - trådbudgeten överskrids aldrig (invariant över batchstorlekar och trådantal), och minnesgränsen begränsar samtidigheten;
  - resultatet är identiskt när kontrollerna fördröjs slumpmässigt, så att färdigordningen blandas (deterministisk CP-SAT);
  - parallell och sekventiell körning når samma optimum som den monolitiska modellen på 10 slumpade fall med extern hyra och på snittvägen, och alla resultat passerar eftervalideringen;
  - tidsgränsen hålls med parallella kontroller (1 och 3 s);
  - avbrott före start ger ingen lösning. Avbrott mitt i körningen ger en fullständig validerad lösning eller ingen. Avbrott efter en verifierad varmstart ger `feasible_not_proven` med samma kostnad. Ett fel i en kontroll stoppar körningen utan kvarlämnade trådar;
  - en kontroll som missat deadline eller avbrutits cachas inte;
  - varmstart: accepterad (kostnad omräknad med nya priser: 1 900 öre för den gamla placeringen, 1 800 öre optimum), avvisad p.g.a. otillåtet pass, tentor utan tidigare placering, dag som inte längre ryms (bevisat) och påhittad placering. En saknad sal noteras, och kontrollen görs med återstående salar. Kostnaden är i alla fall lika med den kalla körningens;
  - körningsval: fel hash, ändrat resultat med uppdaterat manifest (ny validering underkänner trots sparad pass), sparad underkänd status, körning utan placering, ogiltiga id:n, körningar av annat problem, och CLI-flöden med `--warm-start`, `--threads`, `--memory-mb` och `--sequential-day-checks`.
  - Testerna hittade ett fel i avbrottsvägen: loggningen läste en lösares tid när lösaren aldrig startats. Det är rättat.

### 9.3 Samma dagkontroller, sekventiellt och parallellt

Samma plan (den frusna terminslösningen, 73 dagar, tre starttider), samma budget, 8 trådar (`runs/strategiexperiment/equiv.py`):

| Kontroll | Sekventiellt (8 trådar per dag) | Parallellt (8 × 1 tråd) | Vinst | Samma beslut per dag |
|---|---:|---:|---:|---|
| Omkontroll med fasta pass | 35,4 s | 11,3 s | 3,1 × | 73 av 73 (status, rörlig kostnad, antal flyttade) |
| Dagkontroll mot poolen, minsta antal flyttar | 99,1 s | 41,1 s | 2,4 × | 72 av 73. På en dag: sekventiellt `optimal` med 14 flyttade, parallellt `feasible` med 15. Samma kostnad, men kontrollen med en tråd nådde sin 10-sekundersgräns innan flyttantalet bevisats minimalt. |

Uppdelning av 8 trådar på samma dagkontroll mot poolen (73 dagar):

| Uppdelning | Tid |
|---|---:|
| 1 kontroll åt gången, 8 trådar | 100,7 s |
| 2 samtidiga × 4 trådar | 63–67 s |
| 4 × 2 | 66 s |
| 8 × 1 | 45 s |

Vinsten är lägre än i provet i avsnitt 8.6 (77 s mot 11 s). Provet mätte omkontroll med fasta pass, där kontrollerna är lätta. Dagkontrollen med minsta antal flyttar är tyngre per dag, och en tråd är då klart långsammare. Några få dagar sätter svansen (10-sekundersgränsen). Att starta de största dagarna först hjälpte inte (45,0 mot 45,2 s) och infördes inte.

### 9.4 Hela körningar, sekventiella och parallella (utan varmstart)

`Första` är tid från lösarens start till första fullständiga, dag för dag verifierade lösning. Kostnad och undre gräns i kr (modellkostnad med proxypriserna som i avsnitt 5). Alla körningar passerade eftervalideringen tekniskt.

| Instans | Budget | Läge | Första lösning | Kostnad / undre gräns | Utfall | Total tid |
|---|---:|---|---:|---|---|---:|
| v3, 120 tentor | 120 s | parallellt | 33,5 s | 1 065 000 / 1 065 000 | optimal | 33,5 s |
| v3, 120 tentor | 120 s | sekventiellt\* | 35,3 s | 1 065 000 / 1 065 000 | optimal | 35,3 s |
| v13 (2 körningar) | 120 s | parallellt | 2,7 och 3,8 s | 913 000 / 913 000 | optimal | 4,2 och 5,8 s |
| v13 (2 körningar) | 120 s | sekventiellt | 3,6 och 42,8 s | 913 000 / 913 000 | optimal | 6,0 och 45,9 s |
| v8 (2 körningar) | 120 s | parallellt | 30,2 och 52,1 s | 882 000 / 832 000 | genomförbar | 120 s |
| v8 (2 körningar) | 120 s | sekventiellt | 37,3 och 41,5 s | 882 000 / 832 000 | genomförbar | 120 s |
| hela terminen | 300 s | parallellt | 109,6 s | 1 823 000 / 1 773 000 | genomförbar (gap 2,7 %) | 299 s |
| hela terminen | 300 s | sekventiellt\* | 136,6 s | 1 823 000 / 1 773 000 | genomförbar (gap 2,7 %) | 280 s |

\* Mätt i första mätomgången. Den sekventiella vägen påverkades inte av de senare ändringarna, men varmstartens tidsandel och relaxationens budget ändrades efteråt. Ingen av dessa körningar använder varmstart.

Vad mätningarna stöder:
- **Samma ekonomiska resultat.** I varje par med samma instans och budget blev kostnad och undre gräns lika. Pool och antal salar var lika där båda körningarna avslutades med bevisat optimum. Antalet flyttade tentor varierar mellan körningar (v13: 28–86, hela terminen: 242–284) i båda lägena, som i avsnitt 5.5.
- **Tiden till första lösning är något kortare eller lika, inte radikalt kortare.** Hela terminen 110 mot 137 s. Relaxationen och de få täta dagarna dominerar en kall körning. Den stora vinsten ligger i omkontrollen (9.3) och i varmstarten (9.5).
- **Variationen mellan körningar är stor jämfört med skillnaden** (v13 sekventiellt 6,0 respektive 45,9 s, utan koppling till parallellisering). Det är för få upprepningar för att ange en spridning.
- **Minne:** högsta arbetsminne var jämförbart (hela terminen 1 192 MB parallellt mot 1 134 MB sekventiellt).

### 9.5 Varmstart: tid till första verifierade lösning

Startkörning: den kontrollerade terminskörningen med två starttider från PR #9 (`term-decomposed-300-fix`, 1 823 000 kr). Startkörningen kontrollerades på nytt av den oberoende valideraren (1,0 s), och alla varmstarter nedan accepterades efter omkontroll mot den nya instansen.

| Instans | Budget | Utan varmstart | Med varmstart (parallell omkontroll) | Omkontroll sekventiellt |
|---|---:|---|---|---|
| hela terminen, samma parametrar | 300 s | 109,6 s | **13,7 s** | – |
| tre starttider | 180 s | **ingen lösning inom 180 s** | **15,7 s** | 47,9 s |
| flyttfönster ±2 dagar | 180 s | 117,8 s | **16,2 s** | – |

Slutresultat i samma körningar (kostnad / undre gräns, kr):

| Instans | Utan varmstart | Med varmstart |
|---|---|---|
| hela terminen | 1 823 000 / 1 773 000 (genomförbar) | 1 823 000 / 1 773 000 (genomförbar) |
| tre starttider | – | 1 823 000 / 1 685 000 (gap 7,5 %, genomförbar; samma som startlösningen) |
| flyttfönster ±2 | 1 593 000 / 1 509 000 (genomförbar, 156 s) | 1 509 000 / 1 509 000 (**optimal**, 105,5 s) |

Förbehåll:
- Varmstarten ger snabbt en första verifierad lösning. Den garanterar inte en bättre slutlösning. I första mätomgången gav flyttfönster ±2 utan varmstart det bevisade optimumet 1 509 000 kr på 117 s. I slutmätningen gav det ingen bevisad lösning, medan varmstarten gjorde det. Utfallet hör till sökningens slump (avsnitt 5.5), inte till varmstarten.
- Hela terminen med samma parametrar gav samma kostnad. I första omgången gav en varmstartskörning 1 789 000 kr (under 1 823 000), men den gjordes med en tidigare version av koden och gick inte att återskapa.
- Tre starttider: ingen billigare lösning än startlösningen hittades inom tiden. Det är därför fortfarande oavgjort om tre starttider sänker kostnaden.
- Sekventiell omkontroll tog 47,9 s mot 15,7 s parallellt. Med en fjärdedel av tidsgränsen som andel (första versionen) avvisades den sekventiella varmstarten för att tiden tog slut, och körningen fick ingen lösning alls. Andelen är nu hälften.
- Verkliga data: den verkliga 12-tentorskörningen (`joint_real_subset`) kördes två gånger via kommandoraden. Den andra körningen accepterade placeringen från den första efter omkontroll, och eftervalideringen gav `pass`.

### 9.6 Begränsningar och kvarstående

1. **Resultat som beror på väggtid.** Vilken kontroll som når sin tidsgräns beror på datorns last, i båda lägena. Resultatet är därför inte bitvis reproducerbart mellan körningar när tidsgränser nås (se även avsnitt 7, punkt 8). Innehåll och ordning är däremot oberoende av färdigordningen när tidsgränserna inte nås (testat).
2. **Diagnos och reparation är sekventiella.** De är få i de mätta körningarna. Reparationer av olika, disjunkta block är oberoende och kan parallelliseras senare.
3. **Minnesuppskattningen är grov.** Konstanterna (32 MB + 0,02 MB per kandidat × sal) gäller små dagmodeller med högst cirka 2 000 variabler. Mätt högsta arbetsminne ändrades inte märkbart av parallelliseringen, men gränsen är inte prövad nära ett verkligt minnestak.
4. **Modellbygget (under 1 s) kan inte avbrytas,** och ett CP-SAT-anrop som inte stannar av sig självt stoppas inte heller (avsnitt 7, punkt 6).
5. **Varmstart är allt eller inget för första lösningen.** Delvis återanvändning används bara som ledtråd. En nästan fungerande placering kunde reparera enbart de dagar som misslyckas, men det är inte infört.
6. **Automatiskt val av startkörning gör att två körningar med samma indata kan skilja sig** i antal flyttade tentor och tid. Beslutet sparas i körningen, och `--warm-start none` ger den kalla vägen. Optimum påverkas inte.
7. **En vy i gränssnittet saknas.** Endast ändpunkterna är förberedda.
8. **Mätningarna är enstaka körningar** på en bärbar dator och ska läsas som storleksordning.
