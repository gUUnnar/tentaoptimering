# Datamodell

**Dokumenttyp:** teknisk referens.
**Status:** gällande datakorn och separationsprinciper; provisoriska nycklar är
fortfarande provisoriska.

Modellen skiljer tre korn som inte får blandas:

1. `exam_order_id` – provisoriskt beställnings-ID baserat på bokningsexportens prefix.
2. `placement_id` – en fysisk eller administrativ placeringsrad i bokningsexporten.
3. `activity_id` – en rad i Ladokuttaget.

För optimeringsförberedelsen tillkommer `exam_event_id`, en provisorisk bokningshändelse på `exam_order_id`, bokningsdatum och bokningstid. Den är uttryckligen inte en verksamhetsverifierad tentamensidentifierare, men håller samman dess fysiska placeringsrader utan att blanda ihop dem med Ladokaktiviteten.

Kopplingen mellan beställning och Ladokaktivitet är ännu inte verifierad. Kurskod, datum, tid och normaliserad lokal är kandidatfält, inte en permanent primärnyckel.

`candidate_linkage.csv` visar den reproducerbara kandidatjämförelsen på kurskod, datum och starttid. En rad märks som `single_candidate`, `ambiguous_candidates` eller `no_candidate`; ingen av dessa etiketter är en verifierad relation. Kandidatfilen har därför eget diagnostiskt korn och får inte användas som efterfrågetabell eller grund för summering av deltagarantal.

Lokal- och kostnadskällan modelleras på `lease_row_id`. En rad kan vara sal, delrum, förråd, korridor eller parkering. Den ska därför inte användas som ett salregister utan klassning och en verifierad koppling till stabilt sal-ID.

## Normaliserade tabeller

- `bookings.csv`: placeringsrader med provisoriskt beställnings-ID och normaliserade platsnycklar.
- `ladok_activities.csv`: Ladokaktiviteter med normaliserad kurskod, datum, tid och lokalnyckel.
- `lease_rows.csv`: lokal-/kostnadsrader med normaliserade avtals-, byggnads- och rumsnycklar.
- `candidate_linkage.csv`: kandidatpar och uteblivna kandidater mellan bokningsplaceringar och Ladok; en separat diagnostiktabell, inte en faktatabell.
- `exam_events.csv`: provisoriska bokningshändelser med antal observerade placeringar.
- `activity_booking_candidates.csv`: fullständig kandidatrelation mellan Ladok och bokningshändelser, inklusive tvetydigheter och omatchade rader.
- `room_inventory.csv`: observerade bokningsplatser med härlett rums-ID när adress och rum är kända; saknad kapacitet bevaras som saknad.
- `optimization_rooms.csv`: individuella rum med publicerad kapacitet, valda genom den uttryckliga PoC-regeln och spärrade för operativ schemaläggning.
- `optimization_demands.csv`: entydiga kandidatrelationer med det konfigurerade provisoriska efterfrågemåttet.
- `optimization_placements.csv`: efterfrågeposternas historiska fysiska placeringsrader och deras rumsidentifieringsstatus.

Normaliseringen bevarar källfälten men standardiserar rubriker, blanktecken, datum, heltal och tekniska nycklar. Den försöker inte lösa tvetydiga verksamhetsdefinitioner automatiskt.

Gränserna för hur tabellerna får användas följer av denna datamodell,
[arkitekturprinciperna för datakvalitet](ARKITEKTURPRINCIPER_DATAKVALITET.md)
och [den aktuella kravstatusen](KRAV_OCH_STATUS.md). En diagnostisk
kandidatrelation får aldrig uppgraderas till verifierad verksamhetsrelation av
optimeringsmotorn.


## Verksamhetens önskemål (`exam_wishes.csv`)

Bokningsexporten bär verksamhetens ursprungliga önskemål per beställning: `requested_date`, `reserve_date_1`, `reserve_date_2` och `no_reserve_date_reason`. De är *önskemål*, inte bokning: bokningen är `scheduled_date`, sal och tid. `exam_wishes.csv` har en rad per tentamenstillfälle (`exam_event_id`, samma korn som optimeringsbehovet) med de tre datumen, motiveringen som den skrevs, `wish_status` (`reserves_given`, `reason_only`, `neither`, `no_request`), `booked_date_rank` (var det bokade datumet ligger bland önskemålen: `first`, `reserve_1`, `reserve_2`, `other`, `not_booked`), antal tentamenstillfällen per beställning och om beställningens rader har motstridiga önskemål. Önskemålen har datum men aldrig klockslag. Motiveringarna tolkas inte. Se [ABC_SCENARIOMODELL.md](ABC_SCENARIOMODELL.md).

## Tidsavgränsning, verklig beläggning och läsvyer

Den nya dataleveransen avses omfatta **1 januari–30 september inklusive verklig beläggning**. Årtal, filformat, definition av faktisk beläggning och kopplingsnyckel till bokning/sal är ännu inte fastställda i detta dokument; materialet har **inte** importerats. Den data som finns tillgänglig när användaren kör ska avgöra möjliga planeringsperioder, inte fasta terminsdatum i koden.

Behåll en deklarerad **periodtäckning per datatyp** (bokningar, Ladokefterfrågan, salregister/tillgänglighet, faktisk beläggning) med första/sista datum och kända luckor. En saknad beläggningspost betyder **okänd**, inte noll. Där källan tillåter det måste faktiskt nyttjande kunna knytas till **sal-ID + tidsintervall** och, när säkert möjligt, `exam_event_id` och en eller flera `placement_id`. Annars är uppgifterna separata observationsvärden med redovisad osäkerhet.

Den normaliserade bokningsplaceringen och motsvarande tentahändelse ska kunna hämtas för **läsning utan att starta optimering**. Ett uppslag på tentamen kan ge flera fysiska salplaceringar, och ett saluppslag kan visa flera tentamina på samma dag med olika tidintervall. Källa, ursprunglig bokning och simulerad placering är olika informationsmängder och får inte uppdatera varandra.

För analys av utnyttjande redovisas mått explicit: **bokade salstimmar**, **dokumenterade tillgängliga salstimmar**, **bokade platser**, **anmälda tentander**, **faktiskt närvarande** eller **verklig lokalbeläggning** beroende på källans definition. Gör aldrig en kvot mellan olika korn utan att förklara relationen, nämnaren och täckningsgraden. Specifika nya tabeller/kolumner fastställs först när leveransens schema granskats.

## Resursdata: namngivna lokaler, avtalsobjekt, externhyra och personalregler

Kostnader och avtalsvillkor ligger i ett **resurspaket**: en TOML-fil i `config/resource_data/` med schemat `resource-data-v1` (`resource_data.py`). Ett paket väljs med parametern `resources.pack`; ett nytt paket med verkliga uppgifter läggs som en ny fil och en ny rad bland valen i katalogen, utan kodändring. Samma kontrakt bär verkliga och simulerade uppgifter. Den medföljande `simulated_dev_2026.toml` är **simulerad** och används tills verkliga uppgifter finns.

| Post | Innehåll |
|---|---|
| `[pack]` | id, namn, ursprung, giltighetsperiod, beskrivning och vad den ska ersättas av |
| `[[cost_object]]` | hyres- eller avtalsobjekt: art (`internal_rent`, `external_lease`, `owned`, `external_hire`), årskostnad, `avoidable` (`yes`/`no`/`unknown`), uppsägningstid, tidigaste frigörande, engångskostnad |
| `[[room]]` | namngiven sal: stabilt sal-id, namn, `internal` eller `external`, kostnad (egen fördelning eller en jämn andel av avtalsobjektet), kopplat avtalsobjekt, betald restid, tillgänglighet; för en extern sal dessutom kapacitet, planeringsområde, byggnad och debitering (`per_session` eller `per_hour` med minsta debiterade och antagen debiterad tid) |
| `[staff]` | kostnad per betald minut, kortaste betalda pass, kostnad per pool-resurs, regelgrund |
| `[[actual_staffing]]` | valfri faktisk bemanning (datum, sal, antal, betalda minuter) |

Varje post bär `origin` (`observed`, `model_calculated`, `simulated`, `assumption`), källa och giltighetsperiod. **En simulerad uppgift presenteras aldrig som en observation**, och bemanning som modellen räknat för A (faktisk bokning) är `model_calculated`, aldrig observerad. Registrerad bemanning ur `[[actual_staffing]]` visas skild från den beräknade och med sitt eget ursprung.

Hur ett paket används i en körning (`joint_resources.py`): en sal som paketet listar får namn, kostnad, avtalsobjekt och restid därifrån (en registersals kapacitet behålls); en sal som paketet inte listar behåller kostnaden per plats och märks `parameter_proxy`; externa salar läggs till och debiteras per salstillfälle utan fast årskostnad. En kostnadsparameter som användaren ändrat gäller före paketet. Körningen fryser paketet som `resource_pack.json` (hash i manifestet) och anger i `joint_input.json` (`resource_basis`) vilket paket, vilka ursprung och vilka salar som saknade kostnad.

**En sal som slutar användas frigör inte automatiskt sin hyra.** Kopplingen salen → avtalsobjekt avgör: se `cost_realization.py` och [kostnadsmodellen](KOSTNADSMODELL.md).

## Fasta bokningar (reservationer)

Bokningar som inte hör till de optimerade tentorna är inte motorns att flytta men tar salen. `joint_reservations.py` bygger dem ur bokningsunderlaget: en icke avbokad bokning med datum och klockslag, i en sal som identifieras (`room_matched` eller en namngiven sal modellen har) och på ett datum som finns i planeringskalendern, blir en reservation (`Reservation` i kontraktet). Bokningar som bara anger adress, saknar adress eller inte avser en fysisk sal spärrar ingenting och redovisas som *oidentifierade* (antal bokningar och platser). Hela salen spärras under bokningens tid plus ställtid och salen räknas som använd (den kostar) även om ingen optimerad tentamen ligger där. Parametern `reservations.policy = none` ignorerar bokningarna; körningen märks då explorativ.
