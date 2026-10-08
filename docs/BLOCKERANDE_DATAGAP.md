# Blockerande datagap

Följande behöver lösas innan ett optimeringsresultat kan anses operativt tillförlitligt eller användas för en besparingsberäkning. De hindrar inte en tydligt märkt explorativ PoC:

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

## Status efter optimeringsförberedelsen

Kandidatrelationer, provisoriska bokningshändelser och observerade rumsnamn är nu materialiserade i separata tabeller. Aktuella publicerade kapaciteter från UU:s webbplats har lagts till som ett versionsmärkt referenslager, men de är inte verifierade för den historiska bokningsperioden och sidans totalsumma kan inte stämmas av mot de individuellt angivna kapaciteterna.

För PoC:n tillåts de individuellt publicerade kapaciteterna som ett uttryckligt scenarioantagande. Datagap 1–5 kvarstår ändå för operativ användning: i synnerhet saknas fortfarande verifierad aktivitet–beställningsnyckel, historisk kapacitet och kalendertillgänglighet.
