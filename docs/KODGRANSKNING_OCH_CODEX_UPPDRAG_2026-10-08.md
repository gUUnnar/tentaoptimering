# Kodnära granskning och nästa Codex-steg
Datum: 2026-10-08  
Status: verifierad granskning av GitHub `main`, **inte** revision av lokal OR-Tools-kod.

## Utgångspunkt

Styrande dokument: [KONCEPTUELL_KRAVSPECIFIKATION.md](KONCEPTUELL_KRAVSPECIFIKATION.md) och [GAP_ANALYS_MOT_KRAVSPECIFIKATION.md](GAP_ANALYS_MOT_KRAVSPECIFIKATION.md). Det finns vid kontroll endast en GitHub-gren, `main`. Den innehåller den tidigare databaslinjen och inga synliga OR-Tools-moduler. Lokal implementation i `C:\lokalt\tentalokaler\PoC` är **inte granskad**.

## Verifierade kodfynd

1. **`cli.py` + `pipeline.py`**: kör enbart import, normalisering, validering och skrivning av `bookings.csv`, `ladok_activities.csv`, `lease_rows.csv`, `baseline.md`, `data_quality.json`. Ingen solver, scenariokörning eller gemensam ekonomisk optimering på GitHub-`main`.
2. **`normalize.py`**: `exam_order_id` härleds från normaliserat `prefix`, `placement_id` från radordning och `activity_id` från Ladokradordning. De är provisoriska identiteter. Radsummering får inte dubblera efterfrågan. Bygg vidare på gränsen mellan tentamensbehov och historisk fysisk placering; stabilisera identifiering vid bättre data.
3. **`validation.py`**: hittar och beskriver viktiga datagap: bokningarnas blandade korn, otydlig Ladokdefinition för faktisk närvaro, tvetydig koppling mellan Ladok/bokning, lokalrader som inte är salregister, internhyra som inte automatiskt är undvikbar samt tidsförskjutning mellan data. Behåll denna validering.
4. **`cost_model.py`**: `CostComponent` och `SavingsResult` finns, men `uncalculated_savings()` blockerar besparingsresultat. Det är rimligt för **verifierad realiserbar besparing**, men en separat **teoretisk långsiktig kostnadssimulering** krävs nu, med dokumenterade antaganden.
5. **`parameters.toml`**: definitioner av förskjutning i dagar, vardagar, start/sluttid, turnaround, efterfrågemått, salbestånd, digital kompatibilitet, samlokalisering, transport, bemanning och kostnadsdefinition. Värden saknas på flera håll; registret saknar kalendermängder med valbara perioder, procentuell efterfrågeändring, digital andel, personalmix och övergripande ekonomisk planeringshorisont.
6. **`README.md`, `AGENTS.md`**: anger uttryckligen att detta är en data-baslinje och att ingen solver ska byggas utan godkännande; det senare godkännandet avser nu **modellplanering**, inte att oreflekterat ändra kod. Käll-Excel under `underlag` ska aldrig ändras eller committas.
7. **`pyproject.toml`**: deklarerar `pandas` och `openpyxl`, men inte OR-Tools i GitHub-main. Det visar att eventuellt rapporterad CP-SAT-motor inte är representerad här.
8. GitHub har vid kontroll endast grenen `main`; det finns ingen alternativ gren att jämföra med.

## Viktig konsekvens

Den tidigare rapporterade lokala PoC:n gav vid två körningar 1 246 placerade av 1 258 behov, med 12 oplacerade poster. Det är uppgifter från användarens lokala körning, **inte verifierat genom granskning av koden**. En modell som får lämna obligatorisk efterfrågan utanför kan inte ge ett giltigt minimikostnadsresultat för hela efterfrågan.

## Rekommenderad minimal arkitektur

```
rådata (skrivskyddade)
    ↓
normaliserad källdatamodell + kvalitetsrapport
    ↓
verksamhetsmodell: unika tentamensbehov, lokaler, vakttyper, kalender
    ↕
antaganderegister + scenario med värden, källa, osäkerhet
    ↓
EN gemensam kostnadsoptimering (tid + rum + personal)
    ↓
validerat schema + årskostnad + solverstatus + revisionsspår
```

Minimalt nödvändiga beslut:
- datum/pass per tenta inom explicit tillåten kalender; historik som valbart fast krav/preferens;
- fördelning av dimensionerande tentander över lämpliga salar, med absolut platsgräns och ingen successiv insläppning;
- samtidiga vakttimmar/pass, arbetstid, transport och bemanningsminimum;
- val av långsiktig salportfölj och tillfälliga hyrperioder;
- en gemensam långsiktig årskostnad som målfunktion. Alla tentander inom deklarerad omfattning måste få plats eller körningen vara ej fullständigt genomförbar.

Innan större solverarbete: avgör om en integrerad CP-SAT/MIP-modell är beräkningsbar på hel termin med tillgänglig hårdvara och vald granularitet. Det är ett **arkitekturbeslut att testa**, inte ett skäl att låsa verksamhetsregler eller förenkla bort kostnader. Små syntetiska fall först.

## Första avgränsade uppdraget till Codex (ENBART INSPEKTION OCH FÖRSLAG)

1. Läs de tre dokumenten i `docs/`. Läs `README.md` och `AGENTS.md`.
2. Inventera lokala `C:\lokalt\tentalokaler\PoC`: `git status`, branch, remotes, ocommittade/ignorerade filer, opushade commits, installerat solverpaket, faktisk CLI, rapporter och tester. Skriv **inga** ändringar till kod, data eller repository utan nytt godkännande. Gör ingen reset, checkout, merge, rebase eller pull som kan skriva över lokalt arbete.
3. Beskriv den faktiska lokala solverns variabler, hårda/soft constraints, målfunktion, kostnadsmappning och orsaken till att vissa tentamina blev oplacerade; avgör vad som kan återanvändas.
4. Jämför varje princip i kravspecifikationen mot lokal kod och klassificera: redan implementerat/verifierat, delvis implementerat, saknas, okänt p.g.a. data.
5. Föreslå **minsta rimliga omstrukturering** för en integrerad terminssimulering, utan tre separata suboptimerare, och specificera antagandelagret så att inkommande data kan ersätta uppskattningar utan solverombyggnad.
6. Föreslå konkreta tester med kända utfall: 100 % tentandtäckning eller ej godkänd körning; peak-kapacitetsbrist; kurs-/programkrock; digitalt format; kapacitetstak; gemensam start/olika sluttider; ställtid; personaltransport/vila; dyrare personal som möjliggör större lokalbesparing.
7. Leverera en kodnära gap-tabell, prioriterad genomförandeplan och risker/beräkningskomplexitet. **Invänta användarens godkännande innan implementation**.

## Leveranskriterium för denna fas

Codex kan visa exakt hur och var den lokala implementationen avviker från målbilden; användaren kan ta ställning till föreslagen arkitektur innan ytterligare programmering. Vi ska inte uppge optimeringsresultat förrän alla ingående behov är täckta och både kostnader och antaganden är spårbara.
