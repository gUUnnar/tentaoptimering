// Typer för /api/abc/*: A (faktisk bokning), B (grundoptimering) och C (egna körningar).

export type AbcKind = "A" | "B" | "C"

/** En sparad körning i körningshistoriken. */
export type AbcRun = {
  run_id: string
  /** Det namn körningen sparades med, eller (äldre körningar) scenario och starttid. */
  name: string
  named: boolean
  kind: "B" | "C"
  base_run_id: string | null
  problem_id: string | null
  created_at: string | null
  solver_outcome: string | null
  has_placement: boolean
  cost_ore: number | null
  exam_count: number
  changes_from_base: Record<string, unknown> | null
  /** Byggd på det underlag som gäller nu; null när det inte går att avgöra. */
  current_underlay: boolean | null
}

export type WishRank = "first" | "reserve_1" | "reserve_2" | "other" | "unknown"

export type AbcWishes = {
  available: boolean
  reason?: string
  events?: number
  orders?: number
  status?: Record<string, number>
  status_text?: Record<string, string>
  reason_without_letters?: number
  orders_with_conflicting_wishes?: number
  orders_with_several_events?: number
  booked_date_rank?: Record<string, number>
  not_booked_events?: number
}

export type AbcHeader = {
  ref: string
  kind: AbcKind
  name: string
  available: boolean
  unavailable_reason: string | null
  stale: { current: boolean; reason: string | null } | null
  scope: { exam_count: number; participants?: number; booked?: number; not_booked?: number; booked_places?: number }
}

export type AbcMetricRow = { key: string; label: string; left: number | null; right: number | null; delta: number | null }
export type AbcWishRow = { key: WishRank; label: string; left: number | null; right: number | null }

export type AbcChangeItem = {
  exam_event_id: string
  course: string | null
  left: { date: string | null; start: string | null; rooms: string[] }
  right: { date: string | null; start: string | null; rooms: string[] }
  time_changed: boolean
  room_changed: boolean | null
}

export type AbcChanges = {
  compared: number
  unchanged: number
  time_changed: number
  room_changed: number
  rooms_not_comparable: number
  list: AbcChangeItem[]
  list_truncated: boolean
  note: string
}

export type AbcRoomUsage = {
  label: string
  room_id: string | null
  kind: string
  capacity: number | null
  in_model_register: boolean
  sessions: number
  days: number
  booked_minutes: number
  peak_seats: number
  peak_share: number | null
}

export type AbcUtilizationDay = {
  date: string
  exams: number | null
  seats: number
  rooms: number
  capacity_known: number | null
  peak_seats_in_known_rooms: number | null
  share: number | null
}

export type AbcCostSide =
  | { kind: "historical"; available: false; note: string }
  | { kind: "model"; available: false }
  | {
    kind: "model"; available: true; total_ore: number | null; lower_bound_ore: number | null; gap_ore: number | null
    proven_optimum: boolean | null; components: { key: string; label: string; ore: number | null }[]; note: string
  }

export type AbcCost = {
  left: AbcCostSide
  right: AbcCostSide
  model_difference: { ore: number; uncertainty_ore: number | null; label: string } | null
  interpretation: string | null
  interpretable: boolean | null
  savings_requirements: string[]
}

export type AbcParameterChange = { id: string; label: string; group: string; unit: string | null; old: unknown; new: unknown }

export type AbcUnplaced = { exam_event_id: string | null; course: string | null; reason: string; applies_to?: string }

export type AbcCompare = {
  left: AbcHeader
  right: AbcHeader
  comparable: boolean
  reasons: string[]
  metrics: AbcMetricRow[]
  wish_distribution: AbcWishRow[]
  changes: AbcChanges | null
  unplaced: { left: AbcUnplaced[]; right: AbcUnplaced[] }
  rooms: { left: AbcRoomUsage[]; right: AbcRoomUsage[]; only_left: string[]; only_right: string[] }
  utilization: { left: AbcUtilizationDay[]; right: AbcUtilizationDay[] }
  cost: AbcCost
  parameter_changes: AbcParameterChange[]
  parameter_note: string | null
  notes: string[]
}

export type AbcProfile = {
  ref: string
  kind: AbcKind
  name: string
  available: boolean
  unavailable_reason: string | null
  scope: AbcHeader["scope"]
  metrics: Record<string, number | null>
  wish_distribution: Record<string, number>
  notes: string[]
  unplaced: AbcUnplaced[]
  cost: AbcCostSide
}
