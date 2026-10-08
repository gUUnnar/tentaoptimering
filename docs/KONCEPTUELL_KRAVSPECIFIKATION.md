TENTALOKALER – KONCEPTUELL KRAVSPECIFIKATION
Verksamhetsmässig målbild efter intervju, 2026-10-08
Status: arbetsdokument för PoC, inte fastställd produktionsspecifikation.

1. UPPDRAG OCH EKONOMISKT MÅL
Undersök den långsiktiga besparingspotentialen i Uppsala universitets tentamensverksamhet genom GEMENSAM optimering av tre kopplade beslut: när tentamina skrivs, i vilka lokaler och med vilken bemanning. Minimera verksamhetens totala kostnad, inte respektive delkostnad. Fler vakter, längre transport eller mer betald väntetid (bomtid) får vara ekonomiskt motiverat om större lokalbesparing uppstår; omvänt kan dyrare lokaler vara värda att behålla för att minska personal- och transportkostnader.

Budget och utfall redovisas PER ÅR. En termin är minsta planeringsenhet; flera terminer kan ingå i samma optimering. Skilj alltid mellan (a) modellerad långsiktig teoretisk årskostnad och besparingspotential, (b) verifierad och faktiskt realiserbar besparing, och (c) eventuella övergångskostnader/avtalsvillkor. Initial PoC fokuserar på (a); det betyder inte att (b) redan uppstår. Planeringen måste beakta perioder med extrem beläggning, inte bara medelutnyttjande.

2. HÅRDA KRAV OCH GENOMFÖRBARHET
• Alla INOM PoC:ns deklarerade omfattning ingående tentamina och deras dimensionerande tentander ska kunna genomföras. Det är inte en lyckad optimering att lämna tentamina eller studenter oplacerade. Vid konflikt ska körningen ange att fullständig lösning inte hittades/är omöjlig under givna förutsättningar och redovisa orsaker och nödvändiga förändringar; partiella scheman är enbart diagnostik.
• Publicerad fysisk kapacitet per sal och tentamensformat är ett ABSOLUT TAK. Ingen experimentell beläggningsgrad får höja den.
• Uppsala och Visby behandlas som separata planeringsområden. Tentander, lokaler och vakter flyttas inte mellan orterna.
• Digital examination kräver tekniskt kompatibel lokal. Optimeraren får inte konvertera digital tentamen till papper (eller tvärtom) utan ett uttryckligt hypotetiskt scenario.
• Tvingande lagar, kollektivavtal, arbetstidsregler, raster, dygnsvila och kompetenskrav måste följas för alla personaltyper.
• Förhindra samtidiga tentamina på samma kurs och samma utbildningsprogram. Krockar mellan orelaterade parallella studier på individnivå ingår inte. Om programkoppling saknas ska begränsad säkerhet anges, inte döljas.
• PoC:n exkluderar tills vidare särskild stöd-sal och särskilda stödbehov. Exkludera då konsekvent både motsvarande efterfrågan och kapacitet och redovisa tydligt vad som faller utanför, så att resultat inte felaktigt påstår full täckning av universitetets samtliga tentander.

3. PARAMETERSTYRD TENTAMENSSCHEMALÄGGNING (NÄR)
Historiskt önskat datum, starttid och ursprunglig lokal kan per scenario vara hårt fasta, mjuka preferenser eller flexibla inom tillåtna ramar. I normalfallet ska oförändrat schema föredras när det inte finns skäl att ändra det. Använd antingen verifierbara ändringskostnader eller en separat justerbar preferens/sekundärmålfunktion; blanda inte ihop dessa med faktiska kronor.

Definiera vilka parametrar användaren kan justera, utan godtyckliga snäva värdegränser:
• Planeringstermin(er) och tillåtna kalenderdatum, inklusive särskilda tilläggsdagar utanför tentamenstoppar och möjlighet till helgskrivningar.
• Möjliga skrivpass per dag, startfönster, tentamenslängd och antal möjliga pass, med hänsyn till hur länge salarna faktiskt kan användas.
• Ställtid/omställning mellan två SEPARATA skrivtillfällen i samma sal, som en justerbar parameter, exempelvis turnaround_minutes. Historiska intervall är inte automatiskt en beslutad regel.
• Tentamenslängd är normalt en given egenskap. Eventuell parameter max_exam_duration_hours avser en uttrycklig hypotetisk ändring av examinationens upplägg och får aldrig tyst korta en faktisk 5-timmarstentamen.
• Samma tentamen kan delas upp mellan flera rum vid samma tillfälle; antalet tentander får inte dubbleras.
• Olika tentamina och olika skrivtider FÅR finnas i samma salstillfälle, med gemensam start men olika sluttider. Nytillkomna tentander släpps INTE in löpande medan prov pågår. Salen kan användas på nytt först efter sista skrivande och ställtid.
• Om en och samma tentamen får erbjudas vid flera helt olika starttillfällen är en öppen verksamhetsfråga; grundantagande i första PoC är ett gemensamt tillfälle.

4. EFTERFRÅGAN OCH DIGITALISERING
• Historiskt antal registrerade/anmälda tentander kan användas som dimensionering när bättre uppgift saknas; skilj noga på Ladokregistrering, institutionsönskemål och FAKTISK närvaro. Fält i Ladokutdraget är inte verifierad närvaro per automatik.
• Parametern demand_variation_pct ändrar antalet tentander PER tentamen, inte antalet tentamenstillfällen. Startvärde 0 %. Samma procent för alla tentamina i version ett; avrundning till heltal definieras och redovisas.
• Andelen digitala tentamina väntas öka. Tillåt scenario för framtida digital andel, exempelvis digital_exam_share_pct, med tydlig regel för vilka tentamina som växlar format, och märk detta som prognos/hypotes i stället för ett historiskt faktum.
• Externa lokaler som saknar digital teknik, exempelvis Fyrishov i nuvarande beskrivning, kan inte användas för digitala tentamina utan annan teknisk åtgärd. Investering i korttidslokaler ska inte ingå som generellt alternativ.

5. LOKALER OCH KOSTNADER (VAR)
Lokaler ska ha identifiering, ort, byggnad/geografisk position, fysisk kapacitet, formatkompatibilitet, tillgängliga tider, kostnadstyp och användningsvillkor. Lokaler inom samma ort kan användas flexibelt för kompatibla tentor; avstånd påverkar framför allt vakters tidsåtgång och därmed kostnaden.

Skilj på:
A. Långtidshyrda lokaler: fasta kostnader, normalt inte sparade bara för att salen står tom en timme. Optimeringen ska kunna analysera ett kontrafaktiskt MINDRE lokalbestånd, exempelvis att tre långtidshyrda salar ersätts av två, även om den nuvarande hyran eller lokalen inte kan delas upp. Ett proportionellt reducerat hyrespris är då ett explicit hypotetiskt antagande, inte en verifierad avtalsmöjlighet.
B. Korttids-/externhyra: kostnad enligt verkligt debiterbar dag eller sammanhängande hyrperiod och praktiska villkor. Föredra inte automatiskt externa lokaler; digitalt krav kan göra dem oanvändbara.
C. Tekniska anpassningar: investering endast tänkbar i långsiktigt disponerade lokaler, ej exempelvis tillfälligt hyrt Fyrishov. Investeringsmodul prioriteras inte i första PoC.

6. PERSONAL OCH ARBETSTID
Modellera anonymiserade personalresurser med kostnader, arbetstidsvillkor och tillgänglighet; inga personuppgifter behövs. Uppgift om dagens 86 aktiva vakter, varav cirka 20 anställda, är nulägesreferens och INTE en maximigräns. Antal vakter, arbetsvolym och eventuell sammansättning av anställningsformer påverkar totalkostnaden och får optimeras över den långsiktiga horisonten.

Bemanningsbehov varierar med antal samtidigt skrivande i respektive sal och tillämpliga bemanningsregler. Presentationsmaterialets preliminära intervallregel (1–65: 2; 66–135: 3; 136–220: 4; 221–250: 5; 250–300: 6) ska dubbelkontrolleras för gränsvärden och högre kapaciteter; utforma den som lätt ersättbar konfigurationsdata, inte kod. Att minska bemanning när vissa grupper slutar ska kunna vara en separat verksamhetsparameter om säkerhetsregler medger det.

En vakt kan bemanna flera tentor under en dag och arbeta i flera byggnader INOM samma ort. Förflyttning, förberedelse, avslut, raster, vila och bomtid måste tidsmodelleras utan dubbelräkning. Restid och iordningställande kan inte ske samtidigt. Lön, tillägg, övertid, betalda förflyttningar, eventuell bomtid samt relevanta kollektiva villkor ingår i EN sammanhängande kostnadsmodell.

7. GEMENSAM MÅLFUNKTION OCH RESULTAT
Minimera långsiktig årlig total kostnad = strukturella lokalkostnader + externa lokalkostnader + personalkostnader + relevanta ytterligare kostnader (transport eller andra poster utan dubbelräkning). Ett schema med färre salstimmar eller färre vakter är inte per automatik bättre; det är total kostnad som avgör.

Rapportera separat:
• Giltighet/full efterfrågetäckning och solverstatus: optimal, genomförbar utan optimalitetsbevis, ej fullständigt genomförbar, tidsgräns.
• Den hypotetiska årskostnaden och skillnaden mot tydligt definierat nulägesscenario.
• Lokalbestånd, externhyrda dagar/perioder, digital kompatibilitet, terminsvisa toppar och antal skrivtillfällen.
• Personalvolym, bemanning över tid, betald tid, bomtid och flyttningar.
• Flyttade tentor jämfört med ursprungligt datum/tid/lokal; förändringspreferenser/-kostnader.
• Antaganden, vilken data som är verifierad, vilka delar som är uppskattningar, solverns optimalitetsgap och känslighet.
• Tydlig etikett för TEORETISK kontra faktiskt REALISERBAR besparing.

8. KÖRBAR PoC OCH SNART ANKOMMANDE DATA
PoC:n MÅSTE fungera med befintligt material redan i dag. Använd kvalificerade, synligt dokumenterade, versionshanterade antaganden där data saknas. Alla antaganden ska kunna bytas mot bättre data om några dagar UTAN större ombyggnad. Separera importerade rådata, normaliserad datamodell, antaganderegister, scenarioparametrar, optimeringsmotor och rapportering. CLI och maskinläsbart resultat är tillräckligt; grafisk kalender kan användas som scenariointerface senare, men bygg inte en egen webbapp nu.

Befintliga datakällor:
• Tentaplaceringar_Export_2025-09-01-2026-08-31.xlsx: historiska placeringar/bokningar.
• Utsökning Ladok tentander från tidigare termin.xlsx: Ladokbaserat deltagarunderlag, inte säkerställd faktisk närvaro.
• 2026 Tentamenslokaler.xlsx: lokaler och kostnader.
• PM och tillämpning av schemaläggning, rektorsbeslut om principer, lokalt kollektivavtal, mötesanteckningar och presentation Utvecklingsarbete 2-10-26.

9. EXPLICIT ÖPPNA FRÅGOR / VERIFIERINGSBEHOV
Faktisk närvaro, examen–programrelationer, exakta bemanningsgränser och arbetstidsvillkor, anställningskostnader, transport-/förberedelsetider, fullständiga digitala salförutsättningar, externa lokalers exakta hyrvillkor, kostnader vid långsiktig lokalminskning och eventuella tillfällen där en tenta får ges vid olika starttider. Dessa punkter får inte döljas eller felaktigt presenteras som verifierade fakta, men behöver inte blockera kvalificerade explorativa körningar.

10. ARKITEKTURPRINCIP
Utforma den minsta korrekta GEMENSAMMA modellen, kontrollera beslutsvariablerna och hårda kraven med syntetiska testfall och därefter historisk data. Återanvänd befintlig kod där den passar, men skydda inte en missvisande modell med fler specialfall. Projektets nästa steg är kodnära gap-granskning före större omarbetning.

