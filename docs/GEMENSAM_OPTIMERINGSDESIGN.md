# Teknisk specifikation – gemensam optimeringsmotor

Detta dokument specificerar nästa motor innan den byggs för verkliga terminsdata. Den ersätter inte datagap eller verksamhetsbeslut med hårdkodade värden. Alla scenarier ska beskriva sina antaganden i maskinläsbar form.

## Syfte och godkännandekriterium

Motorn ska gemensamt välja tentamensdatum/pass, salstillfällen, lokalportfölj och bemanning för en minst terminslång planeringsperiod. En godkänd lösning täcker exakt hela den inkluderade efterfrågan. Om den inte kan göra det ska huvudmodellen rapportera ogenomförbarhet; en separat diagnostikmodell kan peka ut resursbrist men är inte en lösning.

Ekonomiskt resultat uttrycks i öre. Först minimeras jämförbar årskostnad. Bland lösningar med samma kostnad minimeras sedan dokumenterade förändringspreferenser, exempelvis avvikelse från historiska datum och rum.

## Kanoniskt tentamensbehov

`source_activity` är en Ladokaktivitet. Den är inte automatiskt ett tentamensbehov och dess deltagarantal får inte summeras direkt med andra aktiviteter.

`demand_scope_decision` innehåller exakt ett beslut för varje `source_activity`:

| Status | Betydelse |
|---|---|
| `included` | Aktiviteten ingår i vald omfattning och måste kopplas till en delgrupp. |
| `excluded` | Aktiviteten ingår inte; orsak och evidens är obligatoriska. |
| `unresolved` | Verksamhetsbedömning saknas; aktiviteten är synlig och blockerar en full populationsslutsats. |

`exam_demand` är det unika examinationsbehov som ska schemaläggas. `demand_subgroup` är en faktisk deltagargrupp för ett behov och äger dess deltagarantal. Relationen `source_activity_subgroup` kopplar en eller flera Ladokaktiviteter till samma delgrupp. Därmed kan flera aktiviteter beskriva samma tenta utan att deras tal räknas flera gånger, och en tenta kan delas mellan flera delgrupper och salar.

En inkluderad aktivitet ska kopplas exakt en gång till en delgrupp. Varje delgrupp ska ha ett uttryckligt deltagarantal och en definition av dess räknemetod. Ett `exam_demand` får sitt antal tentander genom summan av sina delgrupper, aldrig genom en implicit summering av aktiviteter.

Den första scope-rapporten får markera tekniskt entydiga aktiviteter med ett konfigurerat provisoriskt deltagarvärde som `included` i **teknisk PoC-omfattning**. Övriga aktiviteter är `unresolved`, inte exkluderade. Rapporten skiljer denna tekniska grund från ett framtida verksamhetsbeslut och möjliggör utveckling, men inte ett påstående om hel verksamhetstäckning.

## Salstillfälle

Ett salstillfälle är en egen optimeringsentitet, inte bara en rad i en tilldelning:

```text
room_session = rum + gemensam start + ingående exam_demand/subgroup + sessionens tillgänglighetstid
```

Alla deltagare i samma `room_session` börjar samtidigt. Varje ingående tenta kan ha egen sluttid. Sessionens `available_again_at` är den senaste sluttiden bland dess ingående tentamina plus konfigurerad ställtid. En ny grupp får inte starta i rummet före den tidpunkten.

I CP-SAT knyts deltagartilldelningen `seats[e,s,r]` till en gemensam passstart `s`. Kapacitetsvillkoret summerar samtidigt skrivande deltagare i varje salstillfälle. För starttider som inte är gemensamma gäller i stället exklusivitet under hela den tidigare sessionens ockupationstid. Detta hindrar löpande nyinsläppning när en del av deltagarna lämnar tidigt.

## Personal som konsekvens av schema och lokalval

`staffing_task` skapas av varje aktiverat `room_session`, med start, slut, förberedelse, avslut, ort och ett regelstyrt krav på antal/kompetens. Bemanning är alltså inte ett förhandsgivet schema.

Den första fullständiga motorn använder en hybridmodell:

1. En bemanningsregel omvandlar varje salstillfälle till samtidiga behov per personaltyp och tidssegment.
2. Anonyma individer introduceras endast för uppgifter som behöver kedjas över dagen – överlapp, restid, raster och vila.
3. När individuella regler inte aktiverats får den aggregerade samtidiga efterfrågan per personaltyp ett kostnads- och kapacitetssamband utan onödiga individvariabler.

Antalet vaktresurser är en beslutsvariabel. Kontraktstypen anger om kostnaden är årsbaserad, timbaserad eller båda; en kostnadskomponent får inte räknas dubbelt. Den syntetiska första modellen använder ett vaktkrav per aktiverat salstillfälle för att bevisa den ekonomiska kopplingen innan arbetstidslogik byggs ut.

## Kalender, resurser och hårda regler

En scenariofil definierar kalenderperiod, tillåtna datum, veckodagar, skrivpass, ställtid och eventuell historisk preferens. Varje `exam_demand` får en mängd giltiga kandidatpass efter att datum-, längd-, ort-, format- och krockregler har tillämpats.

Huvudmodellen har minst följande hårda regler:

- exakt ett kandidatpass för varje inkluderat behov;
- exakt hela dimensionerande deltagarantalet tilldelat;
- fysisk sal-, digital- och stödkompatibilitet;
- separata planeringsområden för Uppsala och Visby;
- kurs- och programkrockar när relationen täcks av data;
- salstillfällets kapacitet, gemensamma start och ställtid;
- verifierade eller uttryckligen antagna kalendertillgängligheter;
- bemanning och aktiverade arbetstidsregler.

Regeltäckning redovisas i varje resultat. En okänd programrelation får inte beskrivas som en verifierad krockkontroll.

## Årskostnad från terminsplanering

Planeringshorisont och ekonomisk horisont är separata:

- Långsiktiga lokalers årskostnad räknas en gång, oavsett antal modellerade terminer.
- Externhyra, timpersonal, betald restid och andra rörliga komponenter summeras först för den faktiskt simulerade perioden.
- En rapporterad årskostnad för rörliga komponenter kräver ett explicit `annualization_factor` och en dokumenterad efterfrågeprofil för den ej simulerade tiden. Faktorn får aldrig impliceras som två.

Om ett sådant antagande saknas redovisas fast årskostnad och simulerad periodkostnad var för sig. Ingen totalsiffra märks då som årskostnad. Det syntetiska fallet använder uttryckligen redan annualiserade kostnadstal endast för att testa kostnadsavvägningen.

## Beräkningsstrategi

Modellen löser hela terminen där lokalportfölj och personalvolym delas. Datumvis dekomponering är inte giltig för den gemensamma kostnadsfunktionen.

För att hålla sökningen rimlig förgenereras endast giltiga pass- och rumskandidater, dominerade alternativ tas bort, symmetriska resurser bryts och historiska placeringar används som warm start. CP-SAT/LNS körs med tidsgräns och dokumenterad optimalitetslucka. Regioner får delas endast när kalender, lokaler och personal bevisligen är oberoende.

## Implementationssteg

1. Kanoniskt scope- och efterfrågelager med full aktivitetsspårbarhet.
2. Syntetiskt integrerat fall med salstillfällen, hård full täckning och rum–personal-avvägning.
3. Konfigurerbara kalender- och antagandeobjekt.
4. Terminsmotor med rum, salstillfällen och kostnadskomponenter.
5. Bemanningsuppgifter, därefter individuella arbetstids- och resevillkor när de aktiveras.
6. Först därefter terminskörning med verkliga data och tydligt vald omfattning.
