# Datamodell för första checkpointen

Modellen skiljer tre korn som inte får blandas:

1. `exam_order_id` – provisoriskt beställnings-ID baserat på bokningsexportens prefix.
2. `placement_id` – en fysisk eller administrativ placeringsrad i bokningsexporten.
3. `activity_id` – en rad i Ladokuttaget.

Kopplingen mellan beställning och Ladokaktivitet är ännu inte verifierad. Kurskod, datum, tid och normaliserad lokal är kandidatfält, inte en permanent primärnyckel.

Lokal- och kostnadskällan modelleras på `lease_row_id`. En rad kan vara sal, delrum, förråd, korridor eller parkering. Den ska därför inte användas som ett salregister utan klassning och en verifierad koppling till stabilt sal-ID.

## Normaliserade tabeller

- `bookings.csv`: placeringsrader med provisoriskt beställnings-ID och normaliserade platsnycklar.
- `ladok_activities.csv`: Ladokaktiviteter med normaliserad kurskod, datum, tid och lokalnyckel.
- `lease_rows.csv`: lokal-/kostnadsrader med normaliserade avtals-, byggnads- och rumsnycklar.

Normaliseringen bevarar källfälten men standardiserar rubriker, blanktecken, datum, heltal och tekniska nycklar. Den försöker inte lösa tvetydiga verksamhetsdefinitioner automatiskt.
