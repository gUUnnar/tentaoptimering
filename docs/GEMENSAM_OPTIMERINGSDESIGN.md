# Teknisk specifikation – gemensam optimeringsmotor

**Dokumenttyp:** styrande teknisk specifikation.
**Status:** gällande för `joint_*`-motorn.

Dokumentet anger motorns kontrakt och godkännandekriterier. Det ersätter inte datagap eller verksamhetsbeslut med hårdkodade värden. Alla körningsunderlag ska beskriva sina antaganden i maskinläsbar form.

## Syfte och godkännandekriterium

Motorn ska gemensamt välja tentamensdatum/pass, salstillfällen, lokalportfölj och bemanning för användarens valda sammanhängande planeringsperiod. Perioden får vara en dag, en vecka, en termin eller längre inom dokumenterad datatäckning. En godkänd lösning täcker exakt hela den inkluderade efterfrågan. Om den inte kan göra det ska huvudmodellen rapportera ogenomförbarhet; en separat diagnostikmodell kan peka ut resursbrist men är inte en lösning.

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

Modellen löser hela den valda perioden med en gemensam lokalportfölj och
personalvolym. En dekomponerad strategi får kontrollera dagar eller dagblock
separat endast om den bevarar det gemensamma portfölj- och poolbeslutet,
producerar en giltig gemensam kostnadsgräns och eftervaliderar den fullständiga
lösningen. Oberoende dagoptimeringar utan dessa kopplingar är inte giltiga för
den gemensamma kostnadsfunktionen.

För små och medelstora instanser förgenereras endast giltiga pass- och rumskandidater, dominerade alternativ tas bort, symmetriska resurser bryts och CP-SAT/LNS körs med tidsgräns och dokumenterad optimalitetslucka. Regioner får delas endast när kalender, lokaler och personal bevisligen är oberoende.

För första terminskörningen i verklig datastorlek används dessutom en uttryckligen konstruktiv skalkörning: lokalportföljer prövas, varje portfölj placeras deterministiskt och kostnaden för lokalportfölj samt anonym samtidig bemanning jämförs gemensamt. Den får rapportera `constructive_feasible`, men aldrig `optimal`, och rapporterar därför inget numeriskt optimalitetsgap. Resultatet är en genomförbarhets- och arkitektursignal tills kandidatgenerering/CP-SAT kan skalas med samma fullständiga regelmängd.

## Implementationssteg

1. Kanoniskt scope- och efterfrågelager med full aktivitetsspårbarhet.
2. Syntetiskt integrerat fall med salstillfällen, hård full täckning och rum–personal-avvägning.
3. Konfigurerbara kalender- och antagandeobjekt.
4. Terminsmotor med rum, salstillfällen och kostnadskomponenter.
5. Bemanningsuppgifter, därefter individuella arbetstids- och resevillkor när de aktiveras.
6. Terminskörning med verkliga data och tydligt vald omfattning, med separat täckningsmått för inkluderade behov respektive hela källpopulationen.

## Betald personaltid, externa salar och fasta bokningar i motorn

**Betald personaltid.** För varje sal och pass finns en produkt `vakter × betald längd` (`joint_paid_time.py`): betald längd är salstillfällets längsta tentamen plus förberedelse och avslut, lägst kortaste betalda pass, plus salens betalda restid, och noll om salen inte har något tillfälle. Kostnaden är kostnaden per betald minut gånger summan. Samma termer byggs för den monolitiska modellen och för varje dagkontroll i den dekomponerade strategin; relaxationen får en giltig undre gräns (varje vaktposition betalas minst den kortaste kandidattentamen i passet). Eftersom gränsen är svagare än den exakta kostnaden kan gapet vara större med betald tid, men resultatet kontrolleras alltid exakt dag för dag.

**Externa salar** är salar utan fast årskostnad med en kostnad per salstillfälle (`Room.external_session_cost_ore`); kontraktet hade redan stödet och resursdata är nu dataadaptern som skapar dem.

**Fasta bokningar** (`Reservation`) spärrar en sal för en tid: ett salstillfälle måste sluta minst ställtiden före bokningens start eller börja minst ställtiden efter dess slut, och en sal med en fast bokning är alltid använd (`owned = 1`). Relaxationen fixerar bara att salen är använd; själva spärren prövas i dagkontrollerna. `joint_blocking.py`.

**Kontrakt.** `joint-optimization-input-v3` lägger till `reservations`, `resource_basis`, `Room.name/cost_object_id/cost_origin/kind/travel_paid_minutes` och `StaffingCostPolicy.paid_minute_cost_ore/min_paid_minutes`; resultatet `staffing_summary` och `costs.staff_paid_time_cost_ore`. Äldre filer läses med standardvärden.

**Prissättning av en given plan.** `joint_pricing.py` prissätter vilken plan som helst (en körning eller den faktiska bokningen) med en sparad körnings regler; den används av jämförelsen (`abc_ledger.py`, `abc_explain.py`) och testas mot optimeraren och valideraren i `tests/test_joint_paid_time_differential.py`.
