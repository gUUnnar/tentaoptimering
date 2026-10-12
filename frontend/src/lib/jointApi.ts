import type {
  EventsResponse, JointEvent, JointScenario, JointSummary, SavedRun, StartJointRunBody, WarmStartCandidate, WarmStartRecord,
} from "./jointTypes.ts"

/** Samma yta för skarp backend och mockad datakälla, så att vyerna inte vet vilken som används. */
export interface JointApi {
  readonly mock: boolean
  listScenarios(): Promise<JointScenario[]>
  listCandidates(problemId: string): Promise<WarmStartCandidate[]>
  startRun(body: StartJointRunBody): Promise<{ job_id: string }>
  events(jobId: string, after: number): Promise<EventsResponse>
  cancel(jobId: string): Promise<void>
  runEvents(runId: string): Promise<JointEvent[]>
  /** null när körningen saknar beslutsfil (HTTP 404). */
  warmStart(runId: string): Promise<WarmStartRecord | null>
  summary(runId: string): Promise<JointSummary>
  listRuns(): Promise<SavedRun[]>
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) { super(message); this.status = status }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options })
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: unknown }
    throw new ApiError(typeof body.detail === "string" ? body.detail : `Anropet misslyckades (HTTP ${response.status}).`, response.status)
  }
  return response.json() as Promise<T>
}

export const httpJointApi: JointApi = {
  mock: false,
  listScenarios: async () => (await request<{ scenarios: JointScenario[] }>("/api/joint-runs/scenarios")).scenarios,
  listCandidates: async problemId => (await request<{ candidates: WarmStartCandidate[] }>(
    `/api/joint-runs/warm-start-candidates?problem_id=${encodeURIComponent(problemId)}`)).candidates,
  startRun: body => request("/api/joint-runs", { method: "POST", body: JSON.stringify(body) }),
  events: (jobId, after) => request(`/api/joint-runs/${encodeURIComponent(jobId)}/events?after=${after}`),
  cancel: async jobId => { await request(`/api/joint-runs/${encodeURIComponent(jobId)}/cancel`, { method: "POST" }) },
  runEvents: async runId => (await request<{ events: JointEvent[] }>(`/api/runs/${encodeURIComponent(runId)}/events`)).events,
  warmStart: async runId => {
    try { return await request<WarmStartRecord>(`/api/runs/${encodeURIComponent(runId)}/warm-start`) }
    catch (error) { if (error instanceof ApiError && error.status === 404) return null; throw error }
  },
  summary: runId => request(`/api/joint-runs/${encodeURIComponent(runId)}/summary`),
  listRuns: async () => (await request<{ runs: SavedRun[] }>("/api/runs")).runs,
}

/** Mockläge: lägg till ?mock=1 i adressen. Ingen backend behövs. */
export function isMockRequested(search: string = typeof window === "undefined" ? "" : window.location.search): boolean {
  const value = new URLSearchParams(search).get("mock")
  return value === "1" || value === "true"
}

export async function loadJointApi(): Promise<JointApi> {
  if (!isMockRequested()) return httpJointApi
  const { mockJointApi } = await import("./jointMock.ts")
  return mockJointApi
}
