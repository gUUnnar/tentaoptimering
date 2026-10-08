# Kandidatkoppling bokningar–Ladok

Detta är en kopplingsdiagnostik, inte en verifierad sammanslagning av källorna.
En kandidat kräver samma kurskod, bokningsdatum och bokningens starttid.
Samma kandidatnyckel kan fortfarande beskriva olika aktiviteter, en samtenta eller flera salplaceringar.

## Mätvärden

| Mått | Värde |
|---|---:|
| `method` | candidate_key_course_code_scheduled_date_booking_start_time |
| `booking_placement_rows_total` | 8466 |
| `booking_placement_rows_with_extractable_course_code` | 8023 |
| `booking_placement_rows_without_extractable_course_code` | 443 |
| `booking_course_placement_rows_eligible` | 10078 |
| `booking_candidate_contexts` | 6132 |
| `booking_candidate_contexts_with_ladok_candidate` | 1368 |
| `booking_course_placement_rows_no_candidate` | 7694 |
| `booking_course_placement_rows_single_candidate` | 2228 |
| `booking_course_placement_rows_ambiguous_candidates` | 156 |
| `candidate_pairs` | 2556 |
| `candidate_pairs_with_identical_location_key` | 94 |
| `ladok_activities_eligible` | 1524 |
| `ladok_activities_ineligible` | 1 |
| `ladok_activities_with_booking_candidate` | 1453 |

## Tolkning och avgränsning

- `single_candidate` betyder endast att exakt en Ladok-rad delar kandidatnyckeln; det är inte en godkänd verksamhetsmatchning.
- `ambiguous_candidates` ska utredas med stabilt aktivitets-ID eller dokumenterad kopplingsregel. De ska inte väljas automatiskt.
- `location_key_equal` är endast ett transparent kontrollmått. Boknings- och Ladoklokaler har olika namnsättning och saknar verifierad översättningstabell.
- Deltagarantal från Ladok används inte i denna artefakt och tolkas inte som faktisk närvaro.
- Fullständig radnivå finns i `data/processed/candidate_linkage.csv` för manuell granskning och återskapas från originalkällorna.
