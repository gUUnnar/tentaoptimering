// Typer för API-kontraktet "gemensam körning" (/api/joint-runs, /api/runs/{id}/events, .../warm-start).
// Kontraktet byggs parallellt av ett annat team; fält som kontraktet lämnar öppna är typade defensivt.

// problem_id är scenariots id i TOML-filen (det som körningarna sparas under), inte filnamnet.
export type JointScenario = { id: string; name: string; description: string; problem_id?: string }

export type WarmStartRequest = "auto" | "none" | (string & {})

export type StartJointRunBody = {
  scenario: string
  warm_start: WarmStartRequest
  threads: number // 0 = standard
  memory_mb: number | null
  parallel_day_checks: boolean
}

export type JointJobStatus = "running" | "completed" | "failed" | "cancelled"

export type PhaseName = "warm_start_check" | "relaxation" | "day_checks" | "repair" | "history" | "finalize"
export type DayStatus = "optimal" | "feasible" | "infeasible" | "unknown"
export type WarmStartDecisionName = "accepted" | "rejected" | "hint_only" | "not_used" | "not_recorded"

type EventBase = { seq: number; t: number } // t = sekunder sedan lösarens start

export type PhaseEvent = EventBase & { type: "phase"; name: PhaseName; state: "started" | "finished" }
export type BatchEvent = EventBase & {
  type: "batch"; kind: string; total: number; done: number; parallel: number; workers_per_check: number
  statuses: Record<string, number>
}
export type DayEvent = EventBase & { type: "day"; date: string; kind: string; status: DayStatus; seconds: number }
export type IncumbentEvent = EventBase & { type: "incumbent"; cost_ore: number; source: string; changed_exams: number }
export type BoundEvent = EventBase & { type: "bound"; lower_ore: number; round: number }
export type WarmStartEvent = EventBase & {
  type: "warm_start"; decision: WarmStartDecisionName; explanation: string; source_run_id: string | null
}
export type ResourcesEvent = EventBase & {
  type: "resources"; threads: number; memory_mb: number | null; parallel_checks: number; workers_per_check: number
}
export type FinishedEvent = EventBase & {
  type: "finished"; outcome: string; cost_ore: number | null; bound_ore: number | null; cancelled: boolean
}

export type JointEvent =
  | PhaseEvent | BatchEvent | DayEvent | IncumbentEvent | BoundEvent | WarmStartEvent | ResourcesEvent | FinishedEvent

export type EventsResponse = {
  status: JointJobStatus; events: JointEvent[]; last_seq: number; run_id: string | null; error?: string | null
}

export type WarmStartCandidate = {
  run_id: string; problem_id: string; solver_outcome: string; cost_ore: number | null
  has_placement: boolean; stored_technical_validation: string | null; warm_start_decision: string | null
}

export type WarmStartRecheck = {
  status: string; reasons: string[]; notes: string[]
  exams_reused: number; exams_without_start: number; exams_not_allowed: number
  days_checked: number; days_failed: number; check_seconds: number
  verified_cost_ore: number | null; hint_exams: number
  first_solution_seconds: number | null; first_solution_source: string | null
  final_cost_ore: number | null; final_source: string | null; interrupted: boolean
}

export type WarmStartRecord = {
  decision: WarmStartDecisionName
  explanation: string
  requested: string
  source: { run_id: string; cost_ore: number | null; technical_validation_now: string | null; result_sha256: string } | null
  changed_parameters: string[]
  recheck: WarmStartRecheck | null
  execution: { threads: number; memory_mb: number | null; parallel_day_checks: boolean; workers_per_check: number }
}

// Kontraktet anger inte formen på domarna; antingen en statussträng eller ett objekt med status/skäl accepteras.
export type VerdictValue = string | { status?: string; reason?: string; [key: string]: unknown } | null

export type JointSummary = {
  cost_ore: number | null; bound_ore: number | null; gap: number | null // gap som bråkdel, t.ex. 0.075
  changed_exams: number | null; first_solution_seconds: number | null; wall_seconds: number | null
  outcome: string
  /** Fullständig placering som den oberoende valideringen godkänner. Saknas den visas ingen lösning. */
  has_verified_solution?: boolean
  cancelled?: boolean
  technical_validation: VerdictValue
  business_verification: VerdictValue
  provenance: VerdictValue | Record<string, unknown>
}

export type SavedRun = { run_id: string; scenario_id: string; status: string; engine?: string; created_at?: string }
