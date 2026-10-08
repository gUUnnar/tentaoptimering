# Optimeringsunderlag för PoC-motorn

Detta dokument beskriver det spårbara datalagret mellan Ladok, provisoriska bokningshändelser och historiska placeringar som PoC-motorn använder. Underlaget är inte ett godkänt operativt salregister eller en kostnadsmodell.

## Korn och relationer

| Tabell | Korn | Användning |
|---|---|---|
| `exam_events.csv` | Provisorisk bokningshändelse: `exam_order_id` + bokningsdatum + bokningstid | Håller ihop flera placeringar för samma observerade bokningshändelse. |
| `activity_booking_candidates.csv` | Kandidatrelation mellan en Ladokaktivitet och en provisorisk bokningshändelse | Visar även omatchade och tvetydiga kandidater; är inte en godkänd verksamhetskoppling. |
| `room_inventory.csv` | Unik observerad bokningsplats | Identifierar ett härlett `room_id` endast när både adress och rum finns. Tom kapacitet betyder okänd, inte noll. |
| `optimization_rooms.csv` | Ett individuellt rum med publicerad kapacitet | Scenariorum för explorativ kapacitets-PoC; okänd kalendertillgänglighet och operativ spärr följer med på varje rad. |
| `optimization_demands.csv` | Entydig kandidatrelation på Ladokaktivitetsnivå | Ger ett konfigurerat, provisoriskt efterfrågemått per aktivitet. |
| `optimization_placements.csv` | Efterfrågepost × historisk placeringsrad | Bevarar flera salar per tentamen och flera aktiviteter i samma bokningshändelse. |

Den tekniska kandidatnyckeln är `course_code + scheduled_date + booking_start_time`. Den används bara för att särskilja tre tillstånd:

- `unambiguous_candidate`: exakt en Ladokaktivitet och en bokningshändelse delar nyckeln.
- `ambiguous_candidates`: minst en sida har fler än en kandidat; ingen godtycklig fördelning görs.
- `no_booking_candidate` eller `no_ladok_candidate`: kandidaten saknas i den andra källan.

## Provisoriskt efterfrågemått

Parameterregistret väljer tills vidare Ladoks `registered_count` (`VARAV_ANTAL_ANMALDA`) som källa till `demand_value`. Valet är uttryckligt och maskinläsbart i `config/parameters.toml`, och kan bytas utan kodändring när dataägaren fastställt ett annat mått.

Det är inte faktisk närvaro. Rader med saknat värde får `missing_configured_demand_value` och är inte klara för en första efterfrågekörning.

## Rum och kapacitet

`room_inventory.csv` kombinerar observerade bokningsuppgifter med ett versionsmärkt utdrag av UU:s officiella sida om tentamenslokaler. Sidan anger bland annat rumskapacitet för Bergsbrunnagatan 15, Fyrislundsgatan 80, Råbyvägen 95 och B40 på Campus Gotland. Den beskriver även Klostergatan 3 som ett specialtentamenscenter med sammanlagd kapacitet, inte kapacitet per enskilt rum, samt Fyrishov som tillfälligt inhyrda hallar utan angiven kapacitet.

Källan är uppdaterad 2026-09-24, efter bokningsperiodens slut. `capacity_seats` bevarar därför publicerade aktuella värden, medan `capacity_usable_for_booking_period` förblir falskt tills giltighetsperioden har verifierats. Fältet `observed_booked_places_max` är fortsatt endast ett historiskt observationsvärde och får inte användas som kapacitet.

På användarens uttryckliga instruktion 2026-10-08 tillåter parameterregistret ändå dessa aktuella, rumsspecifika kapaciteter i en explorativ PoC. Urvalet materialiseras i `optimization_rooms.csv`. Filen skiljer `eligible_for_exploratory_capacity_poc` från `eligible_for_operational_scheduling`; det senare är alltid falskt så länge verifierad kalender och giltighetsperiod saknas. Klostergatans gemensamma anläggningstotal och Fyrishovs salar utan publicerad kapacitet ingår därför inte som optimeringsrum.

Webbsidan anger totalt 1 446 tentamensplatser. De individuellt angivna kapaciteterna i sidtexten summerar till 1 220 inklusive Klostergatans gemensamma total på 41 platser. Skillnaden på 226 platser är ett öppet datakvalitetsproblem och fylls inte med antagna värden.

Lokalrapporten används endast för att visa eventuella namnlikheter på rumsnivå. Den ger inte en verifierad salkoppling, kapacitet eller tillgänglighet och används inte för att fördela internhyra eller beräkna besparing.

Officiell referenskälla: [Tentamenslokaler – Uppsala universitet](https://www.uu.se/medarbetare/stod-och-verktyg/lokaler/boka-tentamensplatser), hämtad 2026-10-08.

## Tillåten användning i PoC:n

Underlaget kan nu användas för att granska matchningsgrad, efterfrågetäckning, samtentor och historiska placeringar utan att dubbelräkna varje salplacering som en egen tenta. Det får också användas för en första explorativ kapacitetskörning som undersöker packning, överkapacitet och ej placerbar efterfrågan.

En sådan körning ska använda `optimization_demands.csv` och `optimization_rooms.csv`, återge scenarioantagandena i resultatet och får inte beskrivas som ett operativt genomförbart schema. Verifierad tillgänglighet, verksamhetsregler och kostnadsundvikbarhet krävs fortfarande innan operativ schemaläggning eller ekonomiska slutsatser.
