import { request } from "./jointApi"
import type { StartJointRunBody } from "./jointTypes"

export type PrecheckVerdict = "impossible" | "blocked" | "possible" | "unclear"
export type PrecheckResult = {
  verdict: PrecheckVerdict; exams_total: number; blocked_exams: number; must_move_exams: number
  solver_outcome: string; seconds: number; reasons: string[]
  fixed_bookings?: FixedBookings | null
}
export type FixedBookingGroup = { group: string; label: string; why: string; action: string; action_parameter: string; bookings: number; booked_places: number; rooms: string[] }
export type FixedBooking = { reservation_id: string; group: string; action: string; date: string; start_minute: number; end_minute: number; room_id: string; room: string; booked_places: number; course: string; exam_event_id: string | null }
/** Övriga redan lagda bokningar i perioden. `status` är något annat än "read" när bokningarna inte kunde läsas eller ignorerades. */
export type FixedBookings = {
  status: string | null; blocking: number; removed: number; unidentified_bookings: number; unidentified_booked_places: number
  groups: FixedBookingGroup[]; bookings: FixedBooking[]; truncated: boolean; note: string | null
}
export type PrecheckJob = { job_id: string; status: string; result: PrecheckResult | null; error: { message?: string } | string | null }

const enc = encodeURIComponent

/** Förkontroll av en körning: går tentorna överhuvudtaget att placera med de här inställningarna? Samma underlag som en körning, inget sparas. */
export const precheckApi = {
  start: (body: StartJointRunBody) => request<{ job_id: string }>("/api/joint-runs/precheck", { method: "POST", body: JSON.stringify(body) }),
  job: (jobId: string) => request<PrecheckJob>(`/api/jobs/${enc(jobId)}`),
}
