# Frågor till dataägaren

Status: frågelista. Den bygger på `python -m tentaoptimering.booking_quality` (rapport över dagens bokningsuttag) och på de nya uppgifterna om tentavakter. Siffrorna avser det uttag som finns i `data/processed` (8 466 bokningsrader, varav 364 avbokade). Svar läggs in som **verifierade regler** i `config/booking_data_quality.toml` (med `verified = true` och `source`) utan kodändring, eller som nya uppgifter i underlaget.

Tills en fråga är besvarad tolkas ingenting: datakvalitetslagret beskriver bara vad uttaget innehåller, och inget av det styr spärrning, kapacitetsreduktion, operativt godkännande eller optimeringsresultat. Att salnamn saknas antas inte betyda något särskilt.

## A. Bokningsuttaget: sal och adress

Läget i uttaget (aktiva rader, 8 102): sal identifierad i registret på 5 005 rader och bara adress angiven på 3 097.

| # | Fråga | Underlag i uttaget | Därför frågar vi |
|---|---|---|---|
| A1 | Betyder frånvaro av salnamn på **Klostergatan 3** att bokningen avser hela adressen eller en pool av platser, att det är en registreringslucka, eller något annat? | 2 267 av 2 267 rader utan sal; medianen är två bokade platser; 95 % av tentamina med rader där har även en namngiven sal någon annanstans. | Avgör om en `address_level_rule` får skapas. Utan svar antas ingenting. |
| A2 | Samma fråga för **Danmarksgatan 30**. | 237 av 237 rader utan sal. | Som A1. |
| A3 | Vad betyder frånvaro av sal på **Fyrislundsgatan 80**, där ungefär hälften av raderna saknar sal? | 566 av 1 141 rader utan sal, 575 med sal. | Blandningen kan vara två olika fall. |
| A4 | Är de fem raderna utan sal på **Bergsbrunnagatan 15** registreringsluckor? | 5 av 2 532. | Sällsynt avvikelse; bör rättas i källan om det är fel. |
| A5 | Går det att få ett nytt bokningsuttag där varje bokning har sal, eller ett fält som skiljer "ingen sal behövs", "sal ej tilldelad än" och "sal glömd"? | Uttaget har ingen sådan kolumn. | Det skulle göra tolkningarna onödiga. |

## B. Bokningsstatus

| # | Fråga | Underlag | Därför frågar vi |
|---|---|---|---|
| B1 | Betyder **Under behandling** (10 rader) att sal ännu inte tilldelats, att bokningen inte är klar, eller något annat? Ska raden räknas som bokad? | Ingen regel finns; raden är `unclassified`. | Avgör om raden kan behandlas som efterfrågan eller som en reservation. Antas inte. |
| B2 | Vad betyder **Andring begard** (3 rader)? | Som B1. | Som B1. |
| B3 | Bekräfta att **Klar** (8 089 rader) betyder en genomförd eller bekräftad bokning, och att **Avbokad** (364 rader) aldrig ska spärra något. | Tolkas i dag efter statusvärdets klartext. | De två reglerna är markerade som verifierade på klartext, inte på dataägarens bekräftelse. |

## C. Lokaler som inte är en fysisk sal, och fält med fel innehåll

| # | Fråga | Underlag | Därför frågar vi |
|---|---|---|---|
| C1 | Är **Hemma** (124 rader) och **Hemtenta** (115 rader) hemtentamen och alltså aldrig en fysisk sal som ska spärras? | Regeln `candidate-hemma` och `candidate-hemtenta` är overifierade. Hemtenta finns i salsregistret som sal. | Avgör om raderna får klassas som `declared_non_physical`. |
| C2 | Vad är **"Ordinarie sal utan anpassningar"** (13 rader, alla utan sal)? Står den i adressfältet av misstag? | Regeln `candidate-sal-utan-anpassningar` är overifierad. | Avgör om adressfältet är ogiltigt för de raderna. |
| C3 | Finns andra lokaler eller bokningstyper som inte avser en fysisk sal (externa, digitala)? | Okänt. | Så att de inte räknas som upptagna salar. |

## D. Salsregistret

| # | Fråga | Underlag | Därför frågar vi |
|---|---|---|---|
| D1 | Vilken kapacitet har de salar som saknar kapacitetsuppgift (Fyrishov D–F och Hemtenta)? | 293 bokningsrader hänför sig till en sal som finns i registret men saknar kapacitet: 178 på Fyrishov och 115 på Hemtenta. | Utan kapacitet kan inga platsandelar anges. |
| D2 | Är bokningarna med **fler bokade platser än salens kapacitet** fel i bokningen, fel i kapacitetsuppgiften, eller avsiktlig överbokning (t.ex. utökad kapacitet)? | 72 rader; vissa salar når över 100 % samtidigt (bl.a. Sal 2 på Bergsbrunnagatan 15). | Skiljer fel i data från verklig praxis. |
| D3 | Vilka salar får bli **operativt godkända**, och på vilket underlag? | `eligible_for_operational_scheduling` är falskt för alla åtta salar i optimeringsunderlaget. | Tillförlitlig planering är i dag omöjlig för varje sal. |

## E. Koppling till Ladok och täckning

| # | Fråga | Underlag | Därför frågar vi |
|---|---|---|---|
| E1 | Går det att få ett **stabilt aktivitets-ID** i bokningen i stället för koppling via kurskod, datum och starttid? | Kopplingen är provisorisk: 1 873 rader har en entydig kandidat, 303 är tvetydiga, 266 saknar kandidat trots att Ladok täcker datumet. | Gör jämförelsen mellan bokning och körning säker. |
| E2 | Kan Ladok-underlaget utökas utanför **12 januari–31 mars 2026**? | 5 659 aktiva bokningar ligger utanför. De saknar koppling för att Ladok inte täcker perioden, inte för att kopplingen är dålig. | Utan det kan bara en del av bokningsperioden planeras. |
| E3 | Vilka tröskelvärden gäller för **tillförlitlig planering** (andel rader utan identifierad sal, ogiltiga rader, oklara kopplingar)? | Inga tröskelvärden finns. | Policyn för tillförlitligt läge behöver dem. |

## F. Tentavakter (ny uppgift 2026-10-14, `anstallda.xlsx`)

Filen innehåller en rad per anställd med tjänstegrad och avtalsenliga tillgängliga arbetstimmar per månad. **Personuppgifterna (namn) lagras inte i repot**; här redovisas bara aggregat. Filen ligger kvar i `C:\lokalt\tentalokaler\underlag`.

| Uppgift | Värde |
|---|---|
| Antal anställda i listan | 20 |
| Tjänstegrader | 0,25 till 0,85: en på 0,85, två på 0,75, fem på 0,60, två på 0,50, två på 0,40, tre på 0,30 och fem på 0,25 |
| Timmar per månad per anställd | tjänstegrad × 167 (0,85 → 141,95 h; 0,25 → 41,75 h) |
| Summa tillgängliga timmar per månad | 1 553,1 h |
| Arbetspass under hela 2025 | 5 474 pass under 47 veckor: 3 286 förmiddagspass och 2 188 eftermiddagspass |

Härlett (ingen verklighet förrän frågorna är besvarade): cirka 116 pass per vecka; 1 553,1 timmar × 12 månader ≈ 18 600 timmar, vilket om all tid gick åt till pass vore högst cirka 3,4 timmar per pass.

| # | Fråga | Därför frågar vi |
|---|---|---|
| F1 | Är "arbetspass" **personpass** (en vakt, ett pass) eller **tentamenspass** (en tentamen i en sal)? Hur långt är ett pass i timmar, med förberedelse och avslut? | Avgör hur 5 474 relaterar till modellens bemanningstrappa och vaktpool. |
| F2 | Avser **tillgängliga timmar** all arbetstid enligt avtal, eller den tid som är avsatt för tentavakt? Hur stor del används faktiskt? | Förhåller sig kapaciteten 1 553,1 h/månad till faktiskt utförd bemanning? |
| F3 | Varför **47 veckor**? Vilka veckor saknas, och gäller timmarna per månad hela året (12 månader)? | Årsberäkningen av bemanning. |
| F4 | Gäller listan **hela tentavaktstyrkan**, eller finns timanställda, extra eller externa vakter som inte står här? Ändras tjänstegraderna över året? | Poolens storlek är en kostnadsvariabel i modellen. |
| F5 | Hur fördelas passen mellan förmiddag och eftermiddag, och finns kvälls- och helgpass? Skillnad mellan 3 286 och 2 188 beror på? | Mönstret för starttider och för tre pass per dag. |
| F6 | Kan **personers tillgänglighet** (när de kan arbeta) levereras anonymiserat, eller bara totalsiffrorna? | Modellen behöver tillgänglighet per tidsperiod, inte per person; personuppgifter ska inte in i Git. |
| F7 | Vilka avtalsvillkor gäller för vilotid, obekväm arbetstid och raster utöver det som redan är angivet? | Se `docs/ANALYS_KOLLEKTIVAVTAL.md`. |

Modellen har idag poolstorlek och årskostnad per vakt som parametrar (`cost.staff_annual_ore`, bemanningstrappan). Uppgifterna ändrar inget i modellen förrän frågorna är besvarade och beslutet är taget.

## G. Hur svaren används

1. Verifierade uppgifter om bokningsdata läggs in i `config/booking_data_quality.toml` med `verified = true` och en källa (vem, när, vad). Tester prövar att en verifierad regel ändrar klassificeringen utan kodändring.
2. Uppgifter som saknas i uttaget (stabilt aktivitets-ID, kapacitet, salstilldelning) kommer med ett nytt uttag; lagret utnyttjar dem automatiskt.
3. Tröskelvärden och policy för tillförlitlig planering beslutas separat (`docs/ARKITEKTURPRINCIPER_DATAKVALITET.md`, avsnitt 4.3) innan någon klassificering får styra något i motorn.
