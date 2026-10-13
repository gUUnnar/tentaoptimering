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

export type LocationsResponse = { locations: BookingLocation[]; coverage: BookingCoverage }

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
  attendance: { available: boolean; note: string }; simulated: null; simulated_note: string
}
