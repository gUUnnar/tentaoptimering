# Tentalokaler – slutsatser från krav- och datagenomgång

Datum: 2026-10-06. Underlag: `C:\lokalt\tentalokaler` och användarens uppdragsförtydligande i chatten.

## 1. Uppdraget som ska styra PoC:n

**Hur mycket kan lokalbehovet optimeras, och hur stor potentiell besparing i kronor kan åstadkommas?**

PoC:n ska göra verksamhetskraven justerbara och visa hur ändringar påverkar lokalbehov, kostnad och genomförbarhet. Parametrarna ska definieras först; värden och tillåtna intervall sätts successivt tillsammans med verksamheten. Inga förutbestämda scenarier eller godtyckliga gränser, exempelvis 0–3 dagars förskjutning, ska byggas in som fasta förutsättningar.

Nuvarande regler beskriver utgångsläget. Verksamhetsregler ska kunna ändras i analysen. Juridiska och avtalsmässiga förutsättningar måste redovisas separat: ett hypotetiskt resultat som kräver regel- eller avtalsändring ska märkas med detta beroende.

## 2. Samlad bedömning

Underlaget räcker för att börja strukturera en retrospektiv optimeringsmodell. Det räcker ännu inte för att redovisa en verifierad besparing i kronor eller en säker uppskattning baserad på faktisk närvaro.

De viktigaste fynden är:

1. Bokningsfilen är detaljerad och användbar, men en rad är inte automatiskt en tentamen. Uppdelade placeringar, samtentor och särskilt stöd måste hanteras utan dubbelräkning.
2. Ladokfilen har anmälningsuppgifter. Inget av dess fält visar uttryckligen faktisk närvaro. Användarens benämning ”närvaro” behöver därför verifieras med dataägaren.
3. Lokalfilen är en rapport över preliminär internhyra och area, inte ett komplett register över skrivsalar, kapaciteter och undvikbara kostnader.
4. Lokalrapporten avser ett bestånd per 1 december 2026. Bokningarna avser september 2025–augusti 2026. Historisk och framtida lokaltillgång behöver hållas isär.
5. Tidigare underlag låser ibland hårda verksamhetskrav och föreslår bestämda scenarier. Dessa formuleringar ska inte styra PoC:n efter det senaste uppdragsförtydligandet.

Ingen optimering har körts i denna genomgång. Inga besparingsbelopp har beräknats.

## 3. Datafilerna

### Bokningar: Tentaplaceringar_Export_2025-09-01-2026-08-31.xlsx

Arket `Data i systemet` innehåller **8 466 datarader och 35 kolumner**. Datumen för inbokning sträcker sig från **2025-09-01 till 2026-08-29**.

| Status | Antal rader |
|---|---:|
| Klar | 8 089 |
| Avbokad | 364 |
| Under behandling | 10 |
| Andring begard | 3 |

Det finns **5 499 olika prefix**. Av dem förekommer **2 469 på flera rader**. Ett prefix förekommer med flera inbokade datum. Prefix är därmed en lovande kopplingsnyckel inom exporten, men dess betydelse och undantag måste verifieras innan det behandlas som unikt tentamenstillfälle.

Användbara fält omfattar kurskoder, prefix, status, samtentor, inbokat datum och tid, längd, adress och sal, bokade platser, antal tentander, ursprungligt antal tentander, RPS, önskat datum, reservdatum, tentamenstyp och digitalt format.

**Hantering som krävs:**

- Skilj tentamen/beställning från placering i sal och från placering för särskilt stöd.
- Bestäm vilka antal som är gemensamma för beställningen och vilka som gäller den enskilda raden. Summera inte beställningsantal över alla placeringsrader utan denna kontroll.
- Skilj avbokningar från genomförda eller färdigplacerade beställningar. Status ”Klar” bevisar inte i sig att tentamen genomfördes.
- Hemmatentor och poster som inte belastar de aktuella lokalerna ska hanteras separat.
- Normalisera adresser och salnamn. Tomma strängar och enstaka blanksteg förekommer; kontroll enbart av tomma Excel-celler räcker inte.
- Kurskoder kan innehålla flera koder. En enkel koppling till en enda kurskod i Ladok blir otillräcklig.
- Kommentarer innehåller verksamhetsbegränsningar som inte finns i strukturerade fält, exempelvis laborationer och flera tentor på samma kurs. Dessa behöver granskas och omvandlas till explicita krav där de ska påverka modellen.

Önskat datum och reservdatum är användbara uppgifter om dagens flexibilitet. De ska inte automatiskt bli PoC:ns maximalt tillåtna datumalternativ.

### Ladok: Utsökning Ladok tentander från tidigare termin.xlsx

Arket innehåller **1 525 datarader och 12 kolumner**. Fälten är:

`EN_KURSKOD`, `BENAMNING_SV`, `STARTDATUM`, `STARTTID`, `AKTIVITETSTILLFALLESTYP_SV`, `LOKAL`, `ANMALAN`, `ANTAL_TOT`, `VARAV_ANTAL_ANMALDA`, `VARAV_ANTAL_AVANMALDA`, `VARAV_ANTAL_TILLAGDA`, `ANTAL_OMREG_EL_TIDTERMIN`.

**Slutsats:** Inget fält betecknar uttryckligen närvarande eller faktiskt skrivande. Uppgifterna ska tills vidare beskrivas som anmälningsdata. `ANTAL_TOT` får inte antas betyda faktisk närvaro utan en definition från dataägaren.

Vid cellkontrollen saknar 16 rader `ANTAL_TOT`, 38 rader `VARAV_ANTAL_ANMALDA`, fem rader `LOKAL` och en rad `STARTTID`. Många fält för avanmälda och tillagda är tomma. Om tomt betyder noll eller okänd uppgift behöver fastställas.

Filen har inte bokningsfilens prefix. En möjlig koppling bygger på kurskod, datum, starttid och normaliserad lokal, kompletterad med namn och aktivitetstyp. Kopplingen måste hantera samtentor, ordinarie/omtentamen och flera placeringar. Matchningsgrad och tvetydiga kopplingar behöver mätas innan filerna används tillsammans.

CSV-versionen finns också i mappen men har inte jämförts med Excelversionen. Ladokfilens fullständiga tidsmässiga täckning och kopplingsgrad är ännu inte verifierade.

### Lokaler och ekonomi: 2026 Tentamenslokaler.xlsx

Arket `Rapport` har rubriken **”Aktuella lokaler per 261201 för Tentamenslokaler”**. Det redovisar upplåtelse, giltighetsdatum, byggnadsbenämning, plan, rum, area, preliminär internhyra för helår 2026, städmarkering och hyresvärd.

Rapporten omfattar även förråd, korridor, parkeringsyta och många delrum. Den kan därför inte användas som en lista där varje rad är en skrivsal.

**Konkreta problem att lösa:**

- Kapacitet, antal digitala platser, stödplatser och salarnas tillgänglighet saknas i denna rapport.
- Lokalernas ekonomiska benämningar överensstämmer inte direkt med bokningsexportens adresser och salnamn. Exempelvis används ”Boländerna, Tentamentslokaler” i ekonomirapporten och ”Bergsbrunnagatan 15” i bokningarna. En verifierad översättningstabell behövs.
- DH17-posterna börjar gälla 2026-12-01 och tillhör därmed inte bokningsperiodens historiska bestånd.
- Bokningar på Klostergatan och externa Fyrishov-placeringar saknar tydligt motsvarande kostnadsposter i rapporten.
- Slutdatum år 9999 är ett systemvärde. Det ska inte tolkas som att uppsägning saknar begränsningar eller att kostnaden kan tas bort direkt.
- ”Internhyra helår (prel 2026)” visar inte vilken faktisk universitetskostnad som försvinner om en viss sal slutar användas.

## 4. Krav och styrande material

Mötesanteckningarna från 11 september och 2 oktober samt mötespresentationen stöder inriktningen att undersöka ekonomisk potential innan ett permanent verktyg eller en organisationsmodell beslutas.

Presentationen från 2 oktober anger retrospektiv optimering av 2024–2025 och att hårda verksamhetskrav låses. Det aktuella datasetet täcker en annan period och det senaste uppdraget innebär att verksamhetskrav ska kunna justeras. Uppdraget och dataperioden behöver därför uppdateras i en kommande PoC-specifikation.

Mötesanteckningarna från 2 oktober innehåller en action om att testa vissa bestämda scenarier. Det är ett tidigare förslag, inte en fast kravlista. PoC:n ska i stället ha ett parameterregister och kunna jämföra valfria parameterinställningar.

Det läsbara beslutsdokumentet, dnr UFV 2025/2115, anger principer från vårterminen 2027. Dokumentet innehåller samtidigt olika datum och kvarvarande platshållare, bland annat ”Namn” och ”och/eller”. Slutlig beslutad version och bilagornas status behöver därför bekräftas. Filnamnet ensamt bevisar inte dokumentets beslutsstatus.

UU:s aktuella webbsida om studenternas arbetsvillkor anger normalt vardagar kl. 08–17 och examination i tentamenslokal kl. 08–19, med möjlighet till annan tid vid särskilda skäl. Den reglerar också schemapublicering och schemaändringar. Retrospektiv omplanering ska därför förstås som alternativ ursprunglig planering, inte som förslag att flytta redan publicerade tentor utan hänsyn till dessa regler.

Mötesanteckningarna återger andra tidsramar, bland annat kl. 08–20, från PM och tillämpningsbilaga. Den skillnaden ska vara en öppen verifieringsfråga, inte döljas genom att välja en av tiderna som permanent modellgräns.

**Läsbegränsning:** PM, tillämpningsbilaga och kollektivavtal finns i mappen men gav ingen användbar text vid extraktion. De är skannade. Visuell läsning kunde inte slutföras eftersom anslutningen till den lokala exekveringsmiljön bröts. Deras exakta bestämmelser är alltså inte verifierade i denna genomgång. Uppgifter om dem i mötesanteckningarna är sekundära uppgifter.

## 5. Parametrar att definiera – värden bestäms senare

Följande är ett förslag till parameterregister, inte fastställda krav eller intervall.

| Område | Parametrar | Underlag/komplettering |
|---|---|---|
| Datumflexibilitet | Tillåten tidigare/senare placering, individuella datumfönster, tentamensperiodens början och slut | Önskat datum och reservdatum finns; tillåtna förändringar beslutas successivt |
| Kalender och tider | Tillåtna veckodagar och helgdagar, tidigaste start, senaste slut, tillåtna starttider | Kravdokument och verksamhetsval |
| Pass och omlopp | Skrivtid, ställtid, förberedelse och återställning, extra skrivtid | Skrivtid finns; övriga tider behöver kompletteras |
| Efterfrågan | Vilket deltagarantal som dimensionerar, närvaroprognos, säkerhetsmarginal och acceptabel risk för platsbrist | Anmälningsdata finns; faktisk närvaro och definitioner saknas |
| Lokalbestånd | Vilka salar/byggnader som får användas, kapacitet, tillgänglighet över tid, vilka objekt som kan avvecklas | Fullständigt salregister och avtalskoppling behövs |
| Digitalt format | Kompatibilitet mellan tenta och sal, antal digitala platser, antagen förändring av tentamensformat | Digitalmarkering finns; salarnas teknik och möjliga formatändringar måste definieras |
| Samlokalisering | Vilka tentor som får dela sal, delas mellan salar eller måste hållas samman | Samtentafält finns; separationsregler behöver kompletteras |
| Särskilt stöd | Antal stödplatser, extra tid, avskildhet och tillåtna placeringar | RPS-fält finns; stödbehovens innebörd och resurser behöver klargöras |
| Studenternas planering | Krockar, mellanrum mellan tentor, belastning per period och samband med kursmoment | Studentgrupps-/programrelationer och övriga schemaförutsättningar saknas |
| Geografi | Tillåtna placeringar, avstånd/restider, transport- och förflyttningsmarginaler | Adresser finns; verifierade restider och tillåtna gränser behövs |
| Bemanning | Minsta bemanning per sal och deltagarantal, kompetens, tillgång per tid, arbetstidsregler | Avtal finns men måste läsas; strukturerad bemanningsdata saknas |
| Ekonomi | Fasta och rörliga kostnader, externa hyror, avvecklingsbara avtalsobjekt, uppsägningstid, bemanning och transporter | Internhyror finns; undvikbara kostnader behöver kompletteras |

Varje parameter bör ha namn, definition, enhet, källa, nuvarande värde, justerbarhet och regelstatus. De gränser som används i en viss körning ska sparas med resultatet och kunna ändras utan kodändring.

## 6. Hur kronor ska redovisas

PoC:n behöver skilja mellan:

- **Minskat resursbehov:** färre samtidigt använda salar, mindre nödvändig kapacitet eller färre externa bokningar.
- **Ändrad intern kostnadsfördelning:** lägre debitering till institutioner, vilket inte automatiskt minskar UU:s totala kostnad.
- **Potentiellt realiserbar besparing:** externa kostnader som kan undvikas och avtals-/lokalobjekt som faktiskt kan avvecklas, minus ökade kostnader för exempelvis bemanning och transport.

En borttagen skrivsal medför inte alltid att en proportionell del av byggnadens hyra försvinner. Besparingen måste beräknas på den avtalsenhet som går att minska eller säga upp. Årlig potential, tidpunkt då den kan realiseras och eventuella engångskostnader bör redovisas separat.

Faktisk historisk närvaro, om den senare erhålls, kan användas för en retrospektiv analys med perfekt efterhandsinformation. Den analysen ska skiljas från planering med prognoser och osäkerhet; annars överskattas den besparing som är möjlig i praktiken.

## 7. Vad som behöver kompletteras först

| Prioritet | Komplettering | Varför den behövs |
|---|---|---|
| 1 | Definition av alla deltagarantal och verifierat uttag av faktisk närvaro | Avgör efterfrågan och möjligheten att bedöma överdimensionering |
| 1 | Salregister med stabila ID, adresser, kapaciteter, teknik, stödplatser och giltighetsperioder | Gör historiska placeringar och alternativ jämförbara |
| 1 | Koppling från salar till upplåtelser/avtal och faktiskt undvikbara kostnader, inklusive externa hyror | Gör det möjligt att översätta minskat lokalbehov till kronor |
| 1 | Bekräftad slutversion av principbeslut och läsning av skannade bilagor/kollektivavtal | Hindrar felaktiga hårda regler i modellen |
| 2 | Definition av prefix och radnivå, inklusive samtentor och RPS | Förhindrar dubbelräkning och felaktig uppdelning |
| 2 | Relationer mellan studentgrupper, kurser och andra obligatoriska moment | Gör större datumförskjutningar bedömbara |
| 2 | Bemanningskapacitet, kostnader och förflyttningstider | Kontrollerar att lokalbesparingen inte kräver ogenomförbar eller dyrare bemanning |

## 8. Rekommenderat nästa steg

Fastställ parameterregistret utan förhandslåsta intervall. Bygg därefter en verifierad baslinje för den faktiska bokningsperioden: vilka tentamenstillfällen och placeringar som ingår, vilka salar som fanns då och hur kostnaderna beräknas.

Första modellresultatet bör visa vilka ändringar som möjliggör minskat lokalbehov och vilka krav som begränsar det. Varje körning ska redovisa parameterinställningar, förändringar jämfört med baslinjen, konsekvenser och kvarstående osäkerhet. Om optimeraren inte har bevisat ett optimum ska resultatet beskrivas som bästa funna lösning, inte maximal möjlig besparing.

## 9. Källor och omfattning

- Användarens uppdragsförtydligande i chatten 2026-10-06 är styrande för PoC:ns inriktning.
- De tre Excel-filerna i `C:\lokalt\tentalokaler\underlag` har lästs programmässigt utan att ändras.
- `Motesanteckningar_AI_schemalaggning_lokaler_2026-09-11.md`.
- `Motesanteckningar_Undersokande_initiativ_tentamenslokaler_2026-10-02.md`.
- `AI_optimering_tentalokaler_moete_2026-10-02.pptx`: textinnehåll granskat.
- `Utvecklingsarbete 2-10-26.pptx`: textinnehåll granskat; bildbaserade diagram har inte verifierats.
- `RS-beslut Principer för tentamensverksamheten 260527.pdf`: extraherad text granskad, inklusive versionstecken och platshållare.
- PM, tillämpningsbilaga och lokalt kollektivavtal: identifierade men inte fullständigt lästa, se läsbegränsning ovan.
- [Studenternas arbetsvillkor, Uppsala universitet](https://www.uu.se/student/regler-och-rattigheter/studenternas-arbetsvillkor), läst 2026-10-06.
- Inspelningen från 2 oktober har inte transkriberats på nytt. Delningslänken till tidigare chatt kunde inte öppnas; uppdragsförtydligandet ovan användes i stället.

Detta är en inledande krav- och datagenomgång. Kopplingarna mellan filer, fullständig datakvalitet och den skannade kravtexten återstår att verifiera före beräkning av besparingspotential.
