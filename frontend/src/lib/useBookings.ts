import { useEffect, useState } from "react"
import { bookingApi } from "./bookingApi"
import type { CompareResponse, ExamResponse, ExamSearchResponse, LocationResponse, LocationsResponse, OverviewResponse } from "./bookingTypes"
import { rangeError, type Range } from "./bookingView"

export type Load<T> = { status: "idle" | "loading" | "ready" | "error"; data: T | null; error: string }

const IDLE = { status: "idle", data: null, error: "" } as const

/** Läser ett svar när `key` ändras; ett föråldrat svar kastas bort om valet hunnit ändras. `key` null = inget att läsa. */
function useLoad<T>(key: string | null, read: () => Promise<T>, keepOld = false): Load<T> {
  const [state, setState] = useState<Load<T>>(IDLE)
  useEffect(() => {
    if (key === null) { setState(IDLE); return }
    let cancelled = false
    setState(current => ({ status: "loading", data: keepOld ? current.data : null, error: "" }))
    read()
      .then(data => { if (!cancelled) setState({ status: "ready", data, error: "" }) })
      .catch(error => { if (!cancelled) setState({ status: "error", data: null, error: (error as Error).message }) })
    return () => { cancelled = true }
  }, [key])  // eslint-disable-line react-hooks/exhaustive-deps
  return state
}

export const useLocations = (refreshKey?: unknown): Load<LocationsResponse> => useLoad(`locations|${String(refreshKey)}`, () => bookingApi.locations())

export const useLocation = (locationKey: string, range: Range): Load<LocationResponse> =>
  useLoad(locationKey && !rangeError(range) ? `${locationKey}|${range.from}|${range.to}` : null, () => bookingApi.location(locationKey, range.from, range.to), true)

export const useExamSearch = (query: string, range: Range | null): Load<ExamSearchResponse> =>
  useLoad(query.trim() || range ? `${query.trim()}|${range?.from ?? ""}|${range?.to ?? ""}` : null, () => bookingApi.searchExams(query.trim(), range?.from, range?.to))

export const useExam = (orderId: string): Load<ExamResponse> => useLoad(orderId || null, () => bookingApi.exam(orderId))

export const useOverview = (range: Range, address: string | null): Load<OverviewResponse> =>
  useLoad(rangeError(range) ? null : `${range.from}|${range.to}|${address ?? "*"}`, () => bookingApi.overview(range.from, range.to, address), true)

export const useCompare = (orderId: string, runId: string): Load<CompareResponse> =>
  useLoad(orderId && runId ? `${orderId}|${runId}` : null, () => bookingApi.compare(orderId, runId))
