import type {
  CompareResult, EventsResponse, FieldError, JointEvent, JointScenario, JointSummary, ParametersResponse, SavedRun, SaveScenarioBody,
  StartJointRunBody, WarmStartCandidate, WarmStartRecord,
} from "./jointTypes.ts"
import { toCompareResult } from "./jointCompare.ts"

export interface JointApi {
  listScenarios(): Promise<JointScenario[]>
  parameters(scenarioId: string): Promise<ParametersResponse>
  saveScenario(body: SaveScenarioBody): Promise<JointScenario>
  listCandidates(problemId: string): Promise<WarmStartCandidate[]>
  startRun(body: StartJointRunBody): Promise<{ job_id: string }>
  events(jobId: string, after: number): Promise<EventsResponse>
  cancel(jobId: string): Promise<void>
  runEvents(runId: string): Promise<JointEvent[]>
  /** null när körningen saknar beslutsfil. */
  warmStart(runId: string): Promise<WarmStartRecord | null>
  summary(runId: string): Promise<JointSummary>
  compare(runId: string, base: string): Promise<CompareResult>
  listRuns(): Promise<SavedRun[]>
}

// ---- Fel -----------------------------------------------------------------------------------------------------------

export class ApiError extends Error {
  status: number
  /** Fel per parameter (HTTP 422 med detail.errors). */
  errors: FieldError[]
  constructor(message: string, status: number, errors: FieldError[] = []) { super(message); this.status = status; this.errors = errors }
}

/** Gör om ett felsvar till ApiError. Hanterar `{detail: "text"}`, `{detail: {errors: [{id, message}]}}` och FastAPI:s standardlista. */
export function errorFromBody(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === "string") return new ApiError(detail, status)
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const list = (detail as { errors?: unknown }).errors
    const errors = Array.isArray(list)
      ? list.filter((item): item is { id?: unknown; message?: unknown } => !!item && typeof item === "object")
        .map(item => ({ id: typeof item.id === "string" ? item.id : "", message: typeof item.message === "string" ? item.message : "Ogiltigt värde." }))
      : []
    if (errors.length) return new ApiError(errors.length === 1 ? errors[0].message : `${errors.length} värden är ogiltiga.`, status, errors)
    const message = (detail as { message?: unknown }).message
    if (typeof message === "string") return new ApiError(message, status)
  }
  if (Array.isArray(detail)) {
    const messages = detail.map(item => (item as { msg?: unknown })?.msg).filter((msg): msg is string => typeof msg === "string")
    if (messages.length) return new ApiError(messages.join(" "), status)
  }
  return new ApiError(`Anropet misslyckades (HTTP ${status}).`, status)
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options })
  if (!response.ok) throw errorFromBody(response.status, await response.json().catch(() => ({})))
  return response.json() as Promise<T>
}

// ---- Översättning av svar ------------------------------------------------------------------------------------------

/** Sammanfattningen som backend skickar (joint_api.run_summary). */
export type BackendSummary = {
  run_id?: string; problem_id?: string | null; scenario_id?: string | null; created_at?: string | null
  solver_outcome: string | null; has_verified_solution: boolean; cost_is_proven_optimum?: boolean
  cost_ore: number | null; lower_bound_ore: number | null; gap_ore?: number | null; gap_relative: number | null
  changed_exams: number | null; exams_total?: number | null; staff_pool_size?: number | null
  wall_time_seconds: number | null; first_solution_seconds: number | null
  first_solution_basis?: string | null; first_solution_source?: string | null
  cancelled: boolean; warm_start_decision?: string | null
  parameters_changed_from_default?: unknown
  verdicts: { technical_validation: string; business_verification: string; provenance: string; technically_validated?: boolean; source?: string }
}

/** Tål att listan kommer som id:n, som objekt med id/label eller som en karta id -> värde. */
export function normalizeChangedParameters(raw: unknown): { id: string; label: string | null }[] {
  const items: unknown[] = Array.isArray(raw) ? raw : raw && typeof raw === "object" ? Object.keys(raw) : []
  return items.flatMap((item): { id: string; label: string | null }[] => {
    if (typeof item === "string") return [{ id: item, label: null }]
    const record = item as { id?: unknown; label?: unknown } | null
    return record && typeof record.id === "string" ? [{ id: record.id, label: typeof record.label === "string" ? record.label : null }] : []
  })
}

/** Översätter backendens fältnamn till vyernas. Saknade domar blir not_evaluated, aldrig godkända. */
export function toJointSummary(raw: BackendSummary): JointSummary {
  const verdicts = raw.verdicts ?? ({} as BackendSummary["verdicts"])
  const outcome = raw.solver_outcome ?? "unknown"
  return {
    run_id: raw.run_id ?? null, problem_id: raw.problem_id ?? null, scenario_id: raw.scenario_id ?? null, created_at: raw.created_at ?? null,
    cost_ore: raw.cost_ore ?? null, bound_ore: raw.lower_bound_ore ?? null, gap_ore: raw.gap_ore ?? null, gap: raw.gap_relative ?? null,
    changed_exams: raw.changed_exams ?? null, exams_total: raw.exams_total ?? null, staff_pool_size: raw.staff_pool_size ?? null,
    first_solution_seconds: raw.first_solution_seconds ?? null, first_solution_basis: raw.first_solution_basis ?? null,
    first_solution_source: raw.first_solution_source ?? null, wall_seconds: raw.wall_time_seconds ?? null,
    outcome, proven_optimum: raw.cost_is_proven_optimum === true || outcome === "optimal",
    has_verified_solution: raw.has_verified_solution === true, cancelled: raw.cancelled === true,
    warm_start_decision: raw.warm_start_decision ?? null,
    parameters_changed_from_default: normalizeChangedParameters(raw.parameters_changed_from_default),
    technical_validation: verdicts.technical_validation ?? "not_evaluated",
    business_verification: verdicts.business_verification ?? "not_evaluated",
    provenance: verdicts.provenance ?? "not_evaluated",
  }
}

/** Backendens "id" är filnamnet; problem-id är det körningarna sparas under. Saknas problem_id används namnet. */
export function toJointScenario(raw: Partial<JointScenario> & { id: string; name?: string }): JointScenario {
  return {
    id: raw.id, name: raw.name ?? raw.id, description: raw.description ?? "", problem_id: raw.problem_id ?? raw.name ?? raw.id,
    origin: raw.origin, subset: raw.subset ?? null,
  }
}

const enc = encodeURIComponent

export const jointApi: JointApi = {
  listScenarios: async () => (await request<{ scenarios: JointScenario[] }>("/api/joint-runs/scenarios")).scenarios.map(toJointScenario),
  parameters: scenarioId => request(`/api/joint-runs/parameters?scenario=${enc(scenarioId)}`),
  saveScenario: async body => toJointScenario(await request<JointScenario>("/api/joint-runs/scenarios", { method: "POST", body: JSON.stringify(body) })),
  listCandidates: async problemId => (await request<{ candidates: WarmStartCandidate[] }>(`/api/joint-runs/warm-start-candidates?problem_id=${enc(problemId)}`)).candidates,
  startRun: body => request("/api/joint-runs", { method: "POST", body: JSON.stringify(body) }),
  events: (jobId, after) => request(`/api/joint-runs/${enc(jobId)}/events?after=${after}`),
  cancel: async jobId => { await request(`/api/joint-runs/${enc(jobId)}/cancel`, { method: "POST" }) },
  runEvents: async runId => (await request<{ events: JointEvent[] }>(`/api/runs/${enc(runId)}/events`)).events,
  warmStart: async runId => {
    try {
      const record = await request<WarmStartRecord>(`/api/runs/${enc(runId)}/warm-start`)
      return record.decision === "not_recorded" ? null : record // 200 med not_recorded när beslutsfilen saknas
    } catch (error) { if (error instanceof ApiError && error.status === 404) return null; throw error }
  },
  summary: async runId => toJointSummary(await request<BackendSummary>(`/api/joint-runs/${enc(runId)}/summary`)),
  compare: async (runId, base) => toCompareResult(await request<unknown>(`/api/joint-runs/${enc(runId)}/compare?base=${enc(base)}`)),
  // Körningar listas ur sparade artefakter; /api/runs gäller den äldre motorn.
  listRuns: async () => (await request<{ candidates: WarmStartCandidate[] }>("/api/joint-runs/warm-start-candidates")).candidates
    .map(item => ({ run_id: item.run_id, scenario_id: item.problem_id, status: item.solver_outcome, engine: "joint" })),
}
