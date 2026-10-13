import { request } from "./jointApi.ts"
import type { CompareResponse, ExamResponse, ExamSearchResponse, LocationResponse, LocationsResponse, OverviewResponse } from "./bookingTypes.ts"

const enc = encodeURIComponent

export const bookingApi = {
  locations: (): Promise<LocationsResponse> => request("/api/bookings/locations"),
  location: (key: string, from: string, to: string): Promise<LocationResponse> =>
    request(`/api/bookings/location?location=${enc(key)}&date_from=${enc(from)}&date_to=${enc(to)}`),
  searchExams: (query: string, from?: string, to?: string): Promise<ExamSearchResponse> =>
    request(`/api/bookings/exams?q=${enc(query)}${from ? `&date_from=${enc(from)}` : ""}${to ? `&date_to=${enc(to)}` : ""}`),
  exam: (orderId: string): Promise<ExamResponse> => request(`/api/bookings/exams/${enc(orderId)}`),
  /** `address` null = alla adresser; "" = bokningar utan adress. */
  overview: (from: string, to: string, address: string | null): Promise<OverviewResponse> =>
    request(`/api/bookings/overview?date_from=${enc(from)}&date_to=${enc(to)}${address === null ? "" : `&address=${enc(address)}`}`),
  compare: (orderId: string, runId: string): Promise<CompareResponse> => request(`/api/bookings/exams/${enc(orderId)}/compare?run=${enc(runId)}`),
}
