# Närvaro och planeringsandel

**Status:** underlag och parameterbeskrivning för `demand.planning_share_ordinary_pct` och
`demand.planning_share_retake_pct`. Siffrorna är beräknade ur filen *Alla tentor vt2026
närvarouppföljning* (12 januari–18 juni 2026, tre identiska dubbletter borttagna) och är
**historisk rapporterad närvaro**, inte dimensionerande efterfrågan.

## Vad parametrarna gör

Planerat deltagarantal per delgrupp är `anmälda × (100 + efterfrågevariation) × planeringsandel`,
avrundat en gång enligt `demand.rounding` och aldrig under 1. Andelen för omtentor gäller bara
tentor som uteslutande består av omtentor; blandade tentor och alla andra typer (dugga, hybrid)
använder andelen för ordinarie tentor, som är det försiktigare valet. Båda är 100 som förval, så en
körning utan uttryckligt val planerar för alla anmälda. En lägre andel är ett **antagande om risk**:
den sparas i `joint_run.json` och gör körningen till en C-körning med efterfrågegrunden markerad som
ej verksamhetsverifierad.

## Historisk närvaro (närvaro / justerade skrivplatser)

| Period | Ordinarie tenta | Omtenta |
|---|---|---|
| Januari | 73 % | 47 % |
| Februari–maj | 67–74 % | 42–48 % |
| Juni | 83 % | 54 % |

Totalt 72 842 närvarande av 108 751 justerade platser (67 %). Fyrishovveckorna (12–16 januari och
1–5 juni) består nästan bara av ordinarie tentor och hade 73 % respektive 83 % närvaro.

## Varför en lägre andel inte räcker som slutsats

- Närvaron varierar mellan tentor. Med 90 % planering på tentanivå översteg närvaron planen på
  cirka 8 % av januaritentorna och 16 % av junitentorna; med 80 % på 23 % respektive 32 %.
  På pass-nivå (flera tentor delar platser) var närvaron högst 92 % av bokade platser.
- Underlaget är en termin. Ingen spridning mellan år är känd.
- 62 rader har närvaro över justerade platser och förklaras inte i filen.
- Närvaro är inte kopplad till exakt sal och tenta (filen saknar prefix och anger delvis adress
  eller "Fyrishov" som lokal).
- Stödstudenter, e-tentor och salarnas format är inte prövade mot en lägre andel.

Körningen sparar planerat och anmält antal (`demand_planning` i underlagsbasen och i sammanfattningen) och förklaringen flaggar när det planerade antalet är lägre än det anmälda: en fullständig placering av det planerade antalet ger inte en plats åt varje anmäld student.

Slutsats: närvaron motiverar att *undersöka* en lägre planeringsandel i C-körningar, men ger inget
verifierat behov och ingen verifierad besparing.
