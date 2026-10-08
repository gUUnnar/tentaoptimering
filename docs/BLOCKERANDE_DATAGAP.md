# Blockerande datagap

> **Historisk datakvalitetsinventering (första checkpointen).** Ordet ”blockerande” avser tillförlitliga/verifierade slutsatser – inte att den explorativa PoC:n måste stå stilla. Enligt [aktuella krav](KONCEPTUELL_KRAVSPECIFIKATION.md) ska optimeraren kunna köras med dokumenterade, kvalificerade och lätt utbytbara antaganden medan kompletterande uppgifter inväntas. Aktuell arbetsordning framgår av [Codex-uppdraget](KODGRANSKNING_OCH_CODEX_UPPDRAG_2026-10-08.md).


Följande behöver lösas innan en solver eller besparingsberäkning kan anses tillförlitlig:

1. definition av bokningsexportens prefix, radkorn, samtentor och RPS-placeringar
2. verifierat uttag av faktisk närvaro och definition av Ladoks deltagarfält
3. stabilt aktivitets-ID eller en dokumenterad kopplingsregel mellan Ladok och bokningar
4. tidsversionerat salregister med stabila ID, adresser, kapacitet, teknik och stödplatser
5. verifierad översättning mellan bokningsnamn och lokal-/avtalsobjekt
6. avvecklingsbara avtalsenheter, undvikbara kostnader, uppsägningstid och engångskostnader
7. externa hyror, bemanningskostnader och transportkostnader
8. bekräftad slutversion av principbeslut, tillämpningsregler och kollektivavtal
9. studentgrupper och andra obligatoriska moment som krävs för krockkontroll
10. verksamhetsbeslut om tillåtna parametervärden och intervall per körning

Baslinjerapporten kvantifierar de datagap som går att belägga direkt i de tre källfilerna.
