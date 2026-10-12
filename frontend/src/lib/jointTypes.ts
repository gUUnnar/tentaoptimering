// Typer för API-kontraktet för optimeringen (/api/joint-runs/*, /api/runs/{id}/events, .../warm-start).
// Belopp är alltid heltal i öre i API:et; gränssnittet visar och matar in kronor (se paramUnits.ts).

// ---- Scenarier och parametrar --------------------------------------------------------------------------------------

export type ScenarioSubset = {
  plan_area: string
  selection: "event_list" | "rule" | (string & {})
  exam_count: number | null
  description: string
}

// problem_id är scenariots id i TOML-filen (det som körningarna sparas under), inte filnamnet.
export type JointScenario = {
  id: string; name: string; description: string; problem_id: string
  origin?: "bundled" | "user" | (string & {})
  subset?: ScenarioSubset | null
}

export type ParamValueType =
  | "integer" | "number" | "boolean" | "choice" | "date" | "time"
  | "time_list" | "integer_list" | "string_list" | "staffing_ladder" | "date_range_list" | "time_range_list"
  | (string & {}) // matrix, rule_set, room_list m.fl.: visas skrivskyddat

export type ParamChoice = { value: string | number | boolean; label: string }
export type EngineSupport = "implemented" | "contract_only" | (string & {})

export type ParameterInfo = {
  id: string; label: string; group: string; value_type: ParamValueType; unit: string | null; help_text: string
  default: unknown
  /** Värdet scenariot själv sätter; saknas (null) när scenariot använder standardvärdet. */
  scenario_value: unknown
  /** Gällande värde i scenariot (scenario_value om det finns, annars default). Det här är jämförelsepunkten för ändringar. */
  value: unknown
  differs_from_default: boolean
  basis: string
  engine_support: EngineSupport
  editable: boolean
  choices: ParamChoice[] | null
  order: number
  advanced?: boolean
}

/** `group` på varje parameter är ett grupp-id; läsbara namn och ordning kommer i group_labels och group_order. */
export type ParametersResponse = {
  catalog_version: string; scenario_id: string; parameters: ParameterInfo[]
  group_labels?: Record<string, string>; group_order?: string[]
}

export type FieldError = { id: string; message: string }

export type SaveScenarioBody = { name: string; description: string; base: string; parameters: Record<string, unknown> }

// ---- Körning -------------------------------------------------------------------------------------------------------

export type WarmStartRequest = "auto" | "none" | (string & {})

export type StartJointRunBody = {
  scenario: string
  warm_start: WarmStartRequest
  threads: number // 0 = standard
  memory_mb: number | null
  parallel_day_checks: boolean
  parameters?: Record<string, unknown>
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
/** En dagkontroll är färdig. `block` finns när kontrollen gällde flera dagar i följd; `date` är då den första. */
export type DayEvent = EventBase & { type: "day"; date: string; kind: string; status: DayStatus; seconds: number; block?: string[] }
/** En dagkontroll har börjat. */
export type DayStartedEvent = EventBase & { type: "day_started"; date: string; kind: string; block?: string[] }
export type IncumbentEvent = EventBase & { type: "incumbent"; cost_ore: number; source: string; changed_exams: number }
export type BoundEvent = EventBase & { type: "bound"; lower_ore: number; round: number }
export type WarmStartEvent = EventBase & {
  type: "warm_start"; decision: WarmStartDecisionName; explanation: string; source_run_id: string | null
}
export type ResourcesEvent = EventBase & {
  type: "resources"; threads: number; memory_mb: number | null; parallel_checks: number; workers_per_check: number
}
export type FinishedEvent = EventBase & {
  type: "finished"; outcome: string; cost_ore: number | null; bound_ore: number | null; cancelled: boolean; error?: string | null
}

export type JointEvent =
  | PhaseEvent | BatchEvent | DayEvent | DayStartedEvent | IncumbentEvent | BoundEvent | WarmStartEvent | ResourcesEvent | FinishedEvent

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

// ---- Resultat ------------------------------------------------------------------------------------------------------

// Domarna kan komma som statussträng eller som objekt med status/skäl; saknat värde tolkas som not_evaluated.
export type VerdictValue = string | { status?: string; reason?: string; [key: string]: unknown } | null

export type JointSummary = {
  run_id: string | null; problem_id: string | null; scenario_id: string | null; created_at: string | null
  cost_ore: number | null; bound_ore: number | null; gap_ore: number | null
  gap: number | null // gap som bråkdel, t.ex. 0.075
  changed_exams: number | null; exams_total: number | null; staff_pool_size: number | null
  first_solution_seconds: number | null; first_solution_basis: string | null; first_solution_source: string | null
  wall_seconds: number | null
  outcome: string
  proven_optimum: boolean
  /** Fullständig placering som den oberoende valideringen godkänner. Saknas den visas ingen lösning. */
  has_verified_solution: boolean
  cancelled: boolean
  warm_start_decision: string | null
  /** Parametrar som skiljer sig från katalogens standardvärde (inte från scenariot). */
  parameters_changed_from_default: { id: string; label: string | null }[]
  technical_validation: VerdictValue
  business_verification: VerdictValue
  provenance: VerdictValue | Record<string, unknown>
}

export type SavedRun = { run_id: string; scenario_id: string; status: string; engine?: string; created_at?: string }

// ---- Jämförelse mellan två körningar -------------------------------------------------------------------------------

export type CompareRunRef = {
  run_id: string; scenario_id: string; created_at: string | null
  problem_id?: string | null; solver_outcome?: string | null; has_verified_solution?: boolean | null
}
export type CompareParameterChange = { id: string; label: string; group: string; unit: string | null; old: unknown; new: unknown }
export type MetricDelta = { old: number | null; new: number | null; delta: number | null }
export type MetricKey =
  | "cost_ore" | "lower_bound_ore" | "gap_ore" | "changed_exams" | "staff_pool_size" | "rooms_used"
  | "wall_time_seconds" | "first_solution_seconds"

export type CompareResult = {
  run: CompareRunRef
  base: CompareRunRef | null
  comparable: boolean
  reason: string | null
  parameter_changes: CompareParameterChange[]
  metrics: Partial<Record<MetricKey, MetricDelta>>
  uncertainty_ore: number | null
  interpretable: boolean | null
  interpretation: string
}
