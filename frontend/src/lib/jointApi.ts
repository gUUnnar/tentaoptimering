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

/** Sammanfattningen som backend skickar (joint_api.run_summary). */
export type BackendSummary = {
  cost_ore: number | null; lower_bound_ore: number | null; gap_relative: number | null; changed_exams: number | null
  wall_time_seconds: number | null; first_solution_seconds: number | null; solver_outcome: string | null
  has_verified_solution: boolean; cancelled: boolean
  verdicts: { technical_validation: string; business_verification: string; provenance: string }
}

/** Översätter backendens fältnamn till vyernas. Saknade domar blir not_evaluated, aldrig godkända. */
export function toJointSummary(raw: BackendSummary): JointSummary {
  const verdicts = raw.verdicts ?? ({} as BackendSummary["verdicts"])
  return {
    cost_ore: raw.cost_ore ?? null, bound_ore: raw.lower_bound_ore ?? null, gap: raw.gap_relative ?? null,
    changed_exams: raw.changed_exams ?? null, first_solution_seconds: raw.first_solution_seconds ?? null,
    wall_seconds: raw.wall_time_seconds ?? null, outcome: raw.solver_outcome ?? "unknown",
    has_verified_solution: raw.has_verified_solution === true, cancelled: raw.cancelled === true,
    technical_validation: verdicts.technical_validation ?? "not_evaluated",
    business_verification: verdicts.business_verification ?? "not_evaluated",
    provenance: verdicts.provenance ?? "not_evaluated",
  }
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
  // Backendens "name" är scenariots problem-id; "id" är filnamnet.
  listScenarios: async () => (await request<{ scenarios: JointScenario[] }>("/api/joint-runs/scenarios")).scenarios
    .map(item => ({ ...item, problem_id: item.problem_id ?? item.name })),
  listCandidates: async problemId => (await request<{ candidates: WarmStartCandidate[] }>(
    `/api/joint-runs/warm-start-candidates?problem_id=${encodeURIComponent(problemId)}`)).candidates,
  startRun: body => request("/api/joint-runs", { method: "POST", body: JSON.stringify(body) }),
  events: (jobId, after) => request(`/api/joint-runs/${encodeURIComponent(jobId)}/events?after=${after}`),
  cancel: async jobId => { await request(`/api/joint-runs/${encodeURIComponent(jobId)}/cancel`, { method: "POST" }) },
  runEvents: async runId => (await request<{ events: JointEvent[] }>(`/api/runs/${encodeURIComponent(runId)}/events`)).events,
  warmStart: async runId => {
    try {
      const record = await request<WarmStartRecord>(`/api/runs/${encodeURIComponent(runId)}/warm-start`)
      return record.decision === "not_recorded" ? null : record // backend svarar 200 med not_recorded när beslutsfilen saknas
    } catch (error) { if (error instanceof ApiError && error.status === 404) return null; throw error }
  },
  summary: async runId => toJointSummary(await request<BackendSummary>(`/api/joint-runs/${encodeURIComponent(runId)}/summary`)),
  // Gemensamma körningar listas ur sparade artefakter; /api/runs gäller den äldre termmotorn.
  listRuns: async () => (await request<{ candidates: WarmStartCandidate[] }>("/api/joint-runs/warm-start-candidates")).candidates
    .map(item => ({ run_id: item.run_id, scenario_id: item.problem_id, status: item.solver_outcome, engine: "joint" })),
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
