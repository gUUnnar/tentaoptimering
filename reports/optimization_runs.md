# Första optimeringskörningarna

Rapporten sammanfattar de första eftervaliderade PoC-körningarna. Resultaten beskriver teoretiskt kapacitetsutnyttjande under scenarioantaganden, inte ett operativt schema eller en ekonomisk besparing.

## Körningar

| Scenario | Run-ID | Solverstatus | Körtid | Placerade tentamina | Oplacerade tentamina | Oplacerade deltagare | Använda Uppsalarum |
|---|---|---|---:|---:|---:|---:|---:|
| Fasta historiska tider | `20261008T102704980911Z-reference_fixed_time` | feasible | 46,3 s | 1 246 | 12 | 1 707 | 7 |
| Starttid ±60 minuter | `20261008T102858593029Z-flexible_start_60m` | feasible | 104,4 s | 1 246 | 12 | 1 574 | 7 |

Båda körningarna passerade den oberoende eftervalideringen av kapacitet, överlappning, delning, geografi, tid och fullständig uppdelning mellan placerad och oplacerad efterfrågan.

## Resultat

Referensens historiska samtidiga efterfrågan når 1 604 deltagare den 16 januari 2026 klockan 08:00–10:00. De sju scenariorummen i Uppsala har tillsammans 1 119 publicerade platser. Underskottet är alltså minst 485 platser i detta tidssegment. Fullständig placering vid oförändrade tider är därmed bevisat omöjlig under scenariots kapaciteter, oberoende av solversökningen.

Scenariot med ±60 minuters startförskjutning:

- minskar oplacerade deltagare med 133, från 1 707 till 1 574;
- lämnar antalet oplacerade tentamina oförändrat på 12;
- flyttar 33 tentamina i tid;
- minskar outnyttjade platsminuter med 63 960;
- ökar öppna salminuter med 300;
- använder fortfarande samtliga sju Uppsalarum.

Körningarna är tidsbegränsade och dagligt dekomponerade. De har giltiga lösningar men inget globalt optimalitetsbevis. För det flexibla scenariot är det därför inte avgjort om fullständig placering är möjlig med mer söktid eller andra uttryckliga tidsregler.

Maskinläsbar jämförelse: `runs/comparisons/20261008T102902325211Z.json`.

## Tolkning

Den första jämförelsen visar ingen minskning av antalet scenariorum. Begränsad starttidsflexibilitet förbättrar däremot vilka deltagarvolymer som kan placeras. Det är ett resultat om teoretisk kapacitet under PoC-antaganden, inte evidens för att lokaler kan avvecklas.

Ekonomisk potential har inte beräknats. Kostnadsunderlaget saknar fortfarande verifierad koppling mellan rum, avtalsenhet och undvikbar kostnad.

