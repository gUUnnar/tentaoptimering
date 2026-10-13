// Svar från /api/bookings/*: historiska bokningar, direkt ur underlaget (ingen optimeringskörning behövs).

/** En bokningsrad: en tentamensbokning i en lokal vid en tid, med bokat antal platser. Varken efterfrågan eller verklig närvaro. */
export type BookingItem = {
  placement_id: string; exam_order_id: string; course_codes: string; course_name: string; exam_type: string
  date: string | null; start: string | null; end: string | null
  address: string | null; room: string | null; location_key: string | null
  booked_places: number; capacity: number | null; seat_share: number | null
  status: string; cancelled: boolean; digital: string | null
  ladok_link: string; ladok_link_text: string
}

export type BookingCoverage = {
  first: string; last: string; rows: number; without_date: number; cancelled: number; source: string
  measures: Record<string, string>
  attendance: { available: boolean; note: string }
}

export type BookingLocation = {
  location_key: string; address: string; room: string | null; label: string; capacity: number | null
  bookings: number; first: string; last: string
}

export type LocationsResponse = { locations: BookingLocation[]; addresses: AddressEntry[]; coverage: BookingCoverage }

export type DaySummary = { bookings: number; booked_minutes: number; booked_places: number; peak_places: number }

export type LocationSummary = {
  bookings: number; cancelled_bookings: number; exam_orders: number; days_with_bookings: number; booked_minutes: number
  booked_places: number; capacity: number | null; peak_places: number; peak_share_of_capacity: number | null; untimed_bookings: number
}

export type LocationResponse = {
  location: { location_key: string; address: string | null; room: string | null }
  date_from: string; date_to: string; bookings: BookingItem[]; days: Record<string, DaySummary>
  summary: LocationSummary; attendance: { available: boolean; note: string }; measures: Record<string, string>
  coverage: BookingCoverage; notes: string[]
}

export type ExamHit = {
  exam_order_id: string; course_codes: string; course_name: string; first_date: string; last_date: string
  placements: number; rooms: number; booked_places: number; all_cancelled: boolean
}

export type ExamSearchResponse = { query: string; total: number; truncated: boolean; exams: ExamHit[] }

export type ExamResponse = {
  exam_order_id: string; course_codes: string; course_name: string; exam_type: string; placements: BookingItem[]
  booked_places: number; rooms: number; ladok_links: string[]; ladok_link_unclear: boolean
  attendance: { available: boolean; note: string }
}

// ---- Översikt per period och adress ---------------------------------------------------------------------------------

export type PlaceMeasures = {
  placements: number; cancelled_placements: number; exam_orders: number; booked_places: number; booked_minutes: number
  peak_places: number; untimed_placements: number
}

/** En sal under en adress. `room` null = bokningar som bara anger adress ("sal ej angiven"); de hänförs aldrig till en sal. */
export type RoomRow = PlaceMeasures & { room: string | null; label: string; location_key: string | null; capacity: number | null; peak_share_of_capacity: number | null }

export type AddressOverview = PlaceMeasures & {
  address: string; label: string; named_rooms: number; unspecified_room_placements: number; rooms: RoomRow[]
}

export type OverviewExam = {
  exam_order_id: string; course_codes: string; course_name: string; exam_type: string; first_date: string; last_date: string
  booked_places: number; place_count: number; places: { label: string; address: string | null; room: string | null; booked_places: number }[]
}

export type OverviewResponse = {
  date_from: string; date_to: string; address: string | null
  totals: {
    placements: number; cancelled_placements: number; exam_orders: number; booked_places: number; addresses: number
    without_address_placements: number; unspecified_room_placements: number; exam_orders_in_several_places: number
  }
  addresses: AddressOverview[]; exams: OverviewExam[]; exams_total: number; exams_truncated: boolean
  bookings: BookingItem[] | null
  attendance: { available: boolean; note: string }; measures: Record<string, string>; coverage: BookingCoverage; notes: string[]
}

export type AddressEntry = { address: string; label: string; bookings: number; exam_orders: number; named_rooms: number; unspecified_room_bookings: number; first: string; last: string }

// ---- Jämförelse mot en körning ---------------------------------------------------------------------------------------

export type SlotInfo = { date: string; start: string; slot_id: string }

export type CompareDemand = {
  exam_demand_id: string; course_code: string | null; participants: number; duration_minutes: number | null; movable: boolean
  original: SlotInfo | null; simulated: SlotInfo | null; moved: boolean; date_shift_days: number | null; start_changed: boolean
  simulated_rooms: { room_id: string; label: string; address: string | null; room: string | null; participants: number }[]
  rooms_compared: boolean; same_rooms: boolean | null; booked_rooms_without_name: number
  booked_addresses: string[]; simulated_addresses: string[]; same_addresses: boolean
}

export type CompareResponse = {
  exam_order_id: string; course_codes: string; course_name: string; run_id: string; problem_id: string | null
  status: "compared" | "no_link" | "not_in_run"; reason: string | null
  booking: { date: string | null; start: string | null; end: string | null; label: string; booked_places: number; status: string }[]
  booked_places: number
  link: { statuses: string[]; texts: string[]; activity_ids: string[]; unclear: boolean; provisional: boolean }
  run: { outcome: string | null; technical_placement_complete: boolean | null }
  demands: CompareDemand[]; notes: string[]
}
