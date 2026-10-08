# Uppdrag: första leveransen för Tentalokaler-PoC

> **HISTORISKT UPPDRAG – ERSATT 2026-10-08.** Detta beskriver endast projektets första datacheckpoint. Aktuella styrande instruktioner finns i [AGENTS.md](AGENTS.md), [konceptuell kravspecifikation](docs/KONCEPTUELL_KRAVSPECIFIKATION.md) och [nuvarande Codex-uppdrag](docs/KODGRANSKNING_OCH_CODEX_UPPDRAG_2026-10-08.md). Formuleringen «Bygg ingen solver ännu» nedan hör till den gamla leveransen, inte ett permanent förbud. För närvarande ska Codex inventera och analysera lokal solver, men avvakta godkännande före ändring. **Alla inom scope ingående tentander måste placeras; schemaläggning ska kunna ändras över hela terminen och inte bara några minuter.**


PoC:n ska på sikt besvara:

> Hur mycket kan lokalbehovet optimeras, och hur stor potentiell besparing i kronor kan åstadkommas?

Verksamhetskraven ska vara justerbara. Modellen ska definiera vilka parametrar som finns, men inte låsa värden eller intervall i förväg. Ett intervall som exempelvis 0–3 dagars datumförskjutning får därför inte byggas in som en permanent förutsättning.

## Den första, snäva leveransen

Arbeta endast med:

1. projektstruktur
2. datainläsning
3. datavalidering
4. normaliserade tabeller
5. parameterregister i maskinläsbar form
6. baslinjerapport
7. kostnadsmodellens struktur
8. lista över blockerande datagap

Bygg ingen solver ännu.

Originaldata finns utanför repot i `C:\lokalt\tentalokaler\underlag` och ska behandlas som read-only. Inga beräknade besparingsbelopp får beskrivas som verifierade innan salar har kopplats till kapacitet, avtal och faktiskt undvikbara kostnader.
