# Datamodell för första checkpointen

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

Se `docs/OPTIMERINGSUNDERLAG.md` för gränserna för vad tabellerna får användas till före motorbygge.


## Tidsavgränsning, verklig beläggning och läsvyer

Den nya dataleveransen avses omfatta **1 januari–30 september inklusive verklig beläggning**. Årtal, filformat, definition av faktisk beläggning och kopplingsnyckel till bokning/sal är ännu inte fastställda i detta dokument; materialet har **inte** importerats. Den data som finns tillgänglig när användaren kör ska avgöra möjliga planeringsperioder, inte fasta terminsdatum i koden.

Behåll en deklarerad **periodtäckning per datatyp** (bokningar, Ladokefterfrågan, salregister/tillgänglighet, faktisk beläggning) med första/sista datum och kända luckor. En saknad beläggningspost betyder **okänd**, inte noll. Där källan tillåter det måste faktiskt nyttjande kunna knytas till **sal-ID + tidsintervall** och, när säkert möjligt, `exam_event_id` och en eller flera `placement_id`. Annars är uppgifterna separata observationsvärden med redovisad osäkerhet.

Den normaliserade bokningsplaceringen och motsvarande tentahändelse ska kunna hämtas för **läsning utan att starta optimering**. Ett uppslag på tentamen kan ge flera fysiska salplaceringar, och ett saluppslag kan visa flera tentamina på samma dag med olika tidintervall. Källa, ursprunglig bokning och simulerad placering är olika informationsmängder och får inte uppdatera varandra.

För analys av utnyttjande redovisas mått explicit: **bokade salstimmar**, **dokumenterade tillgängliga salstimmar**, **bokade platser**, **anmälda tentander**, **faktiskt närvarande** eller **verklig lokalbeläggning** beroende på källans definition. Gör aldrig en kvot mellan olika korn utan att förklara relationen, nämnaren och täckningsgraden. Specifika nya tabeller/kolumner fastställs först när leveransens schema granskats.
