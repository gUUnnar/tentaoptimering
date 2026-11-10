# Blockerande datagap

**Dokumenttyp:** aktuell datagapförteckning.
**Status:** gällande tills respektive uppgift är verifierad och statusmatrisen uppdaterad.

> Ordet ”blockerande” avser tillförlitliga eller verifierade slutsatser – inte att den explorativa PoC:n måste stå stilla. Enligt [aktuella krav](KONCEPTUELL_KRAVSPECIFIKATION.md) ska optimeraren kunna köras med dokumenterade, kvalificerade och lätt utbytbara antaganden medan kompletterande uppgifter inväntas. Genomförandestatus och prioritering finns i [kravstatusen](KRAV_OCH_STATUS.md).

Följande behöver lösas innan ett optimeringsresultat kan anses operativt tillförlitligt eller användas för en verifierad besparingsberäkning. De hindrar inte en tydligt märkt explorativ PoC:

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

## Underlagets period

Det förberedda underlaget (`data/processed`) innehåller tentor med ursprungsdatum 2026-01-12 till 2026-03-31 (1 259 klara för modellering, varav 1 172 i Uppsala). Det finns inga tentor efter 31 mars, så april–juni, inklusive sluttentaveckorna, ingår inte i något scenario. Scenariot `joint_underlay_period` heter därför "Alla tentor i underlaget (12 jan–31 mars 2026)" och inte "hela terminen". Orsaken till att underlaget slutar där är inte utredd (urval i källfilerna eller att uttaget inte omfattar senare tentor) och behöver bekräftas mot källan innan en slutsats om lokalbehovet för hela terminen dras.

## Status efter optimeringsförberedelsen

Kandidatrelationer, provisoriska bokningshändelser och observerade rumsnamn är nu materialiserade i separata tabeller. Aktuella publicerade kapaciteter från UU:s webbplats har lagts till som ett versionsmärkt referenslager, men de är inte verifierade för den historiska bokningsperioden och sidans totalsumma kan inte stämmas av mot de individuellt angivna kapaciteterna.

För PoC:n tillåts de individuellt publicerade kapaciteterna som ett uttryckligt scenarioantagande. Datagap 1–5 kvarstår ändå för operativ användning: i synnerhet saknas fortfarande verifierad aktivitet–beställningsnyckel, historisk kapacitet och kalendertillgänglighet.

## Kompletterande verksamhetsuppgifter 2026-10-02

Presentationens [verksamhetsuppgifter](VERKSAMHETSUNDERLAG_2026-10-02.md) tillför indikationer på **7 ordinarie salar/1 109 platser + RPS 41**, en annan **bemanningstrappa med minst 2 vakter per arbetspass**, efterfrågetoppar till och med **juni 2026**, planerade platsvolymer och historisk bom-/övertid. Detta är **nya källuppgifter men inte verifierad modellindata**; datagapen ovan kan inte markeras som lösta av presentationen.

För verifiering behöver vi särskilt salslista och giltighetsperioder (gap 4–5), entydiga deltagar-/närvaromått (gap 2), överenskommen bemanningstrappa inklusive gränsen 250 och >300 tentander samt passdefinition (gap 8 och 10), Retendo-/lönekälla för bomtid/mertid (gap 7), och avstämning av presentationens två olika belopp för ”pengar i sjön”. Ett föreslaget **tredje skrivpass per sal och dag** är en möjlig justerbar förutsättning, inte en beslutad regel.

## Simulerade resursuppgifter (2026-10-15)

Punkterna 5–7 ovan (översättning mellan bokningsnamn och avtalsobjekt, avvecklingsbara avtalsenheter och externa hyror/bemanningskostnader) har ännu inga verkliga uppgifter. För utveckling finns ett **simulerat** resurspaket (`config/resource_data/simulated_dev_2026.toml`) med påhittade men realistiska värden, alla märkta `simulated`. Det löser inget av gapen: det visar att kedjan från avtal och betald personaltid till förklarad besparing fungerar och kan ersättas av verkliga uppgifter utan kodändring. En besparing som bygger på paketet är aldrig verifierad. Bokningar som saknar identifierad sal kan inte spärra något och redovisas som oidentifierade.

## Nytt underlag 2026-11 (avstämning, ingen ny efterfrågan)

- **Ladok, alla aktivitetstillfällen** (`Ladok ALLA aktivitetstillfällen 1 jan 31 jul.xlsx`, 3 567 publicerade eller utkast, 2025-12-16–2026-06-11) är en annan datakorn än uttaget som efterfrågan vilar på (1 525 rader, bara januari–mars). Listan når april–juni men kan **inte** göras till efterfrågan utan beslut: `Antal anmälda` saknas för 247 tillfällen, platsantal saknas för 1 057, prefix för 261, och kurskoden i listan stämmer bara på 285 av 1 525 rader mot uttagets kurskod (anmälda är lika med uttagets anmälda på 199 av 269 jämförbara rader). Kopplingen mot bokningar fungerar på prefix och datum (januari–juni 84–87 % av bokningsdagarna). Mätningen görs av `python -m tentaoptimering.ladok_occasions`; den skriver ingen efterfrågan.
- **Beslut som behövs för att utöka perioden till juni:** godkänner verksamheten `Antal anmälda` i tillfällelistan som dimensionerande mått (jämfört med uttagets anmälda), hur tillfällen utan prefix eller antal hanteras, och att koppla tillfälle till bokning på prefix och datum. Tills dess ingår inga tentor efter 31 mars i någon körning, inklusive Fyrishovveckan 1–5 juni; förhyrningsfönstret för juni är modellerat men kan inte provas på riktig efterfrågan.
- **Närvarouppföljningen** (12 januari–18 juni) importeras som observerad användning i ett eget datakorn och påverkar inte efterfrågan (se [närvaro och planeringsandel](NARVARO_OCH_PLANERINGSANDEL.md)).
- **Anställda och flex** (20 personalrader, 9,3 heltidsekvivalenter, 1 553,1 avtalade timmar/månad; flex huvudsakligen 2025) är inte importerade: de ger avtalad personalvolym men ingen individuell tillgänglighet, och flexfilens två bomtidssummeringar för 2025 (1 228,5 och 1 311 timmar) behöver stämmas av.
- **PM om schemaläggning** (2 juni 2026, förslag till beslut, giltighet från VT2027) ska jämföras med slutligt beslut innan regler läggs in som parametrar.
- **Fyrishov**: uppgiften (cirka 2,4 mnkr 2026, varav cirka 1,2 mnkr lön) saknar uppdelning per tillfälle; beloppet i det simulerade paketet är påhittat.
