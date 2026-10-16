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
  /** Besparingen mellan alternativen förklarad ner till lokaler, bokningar och betald personaltid. */
  explained: AbcExplained
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

// ---- Förklarad besparing mellan två alternativ (se abc_explain.py) ----

export type ExplainOrigin = "observed" | "model_calculated" | "simulated" | "assumption"

export type ExplainedBasisSide = {
  kind: AbcKind
  name: string
  /** `model_calculated` för en körning, `model_calculated_for_historical_bookings` för A prissatt med körningens regler. */
  cost_kind: string
  cost_kind_text: string
  resource_data: { pack_id: string; origin: ExplainOrigin; origins: ExplainOrigin[] } | null
  staffing_origin: "model_calculated" | "model_calculated_from_booked_places"
  priced_by: "own" | "the_other_alternative"
  reservations: string | null
  optimum: { gap_ore: number | null; proven: boolean | null }
}

export type ExplainedDriver = { kind: string; text: string; ore?: number; room_id?: string; count?: number; paid_minutes?: number; passes?: number }

export type ExplainedItem = {
  key: "rooms" | "external" | "staff"
  label: string
  left_ore: number
  right_ore: number
  /** Null när totalskillnaden spärras (ofullständigt eller oförenligt underlag): bara före och efter visas. */
  difference_ore: number | null
  /** Förändrat resursutnyttjande (samma priser) respektive ändrade priser och antaganden; null när uppdelning inte går. */
  usage_ore: number | null
  assumption_ore: number | null
  parts?: { key: string; label: string; left_ore: number; right_ore: number; difference_ore: number | null }[]
  drivers: ExplainedDriver[]
}

export type ExplainedRealization = { status: string; reason: string; contract: { name: string; avoidable: string; notice_months: number | null; earliest_release_date: string | null; one_off_cost_ore: number | null; origin: ExplainOrigin } | null }

export type ExplainedRoomSide = { used: boolean; reserved_only: boolean; sessions: number; booked_minutes: number; fixed_ore: number; external_ore: number; peak_participants: number }

export type ExplainedRoom = {
  room_id: string
  name: string
  kind: "internal" | "external"
  capacity: number | null
  cost_origin: string | null
  cost_object_id: string | null
  status: "kept" | "avoidable" | "added"
  left: ExplainedRoomSide
  right: ExplainedRoomSide
  difference_ore: number
  fixed_difference_ore: number
  external_difference_ore: number
  booked_minutes_difference: number
  reserved_only: boolean
}

export type ExplainedSession = {
  room_id: string; room: string; date: string; start: string; end: string; participants: number; staff: number
  paid_minutes: number; external_ore: number; external: boolean; exams: string[]
}

export type ExplainedExamChange = {
  exam_event_id: string
  course: string | null
  participants: number | null
  before: { date: string | null; start: string | null; rooms: string[]; room_ids: string[] }
  after: { date: string | null; start: string | null; rooms: string[]; room_ids: string[] }
  changes: ("date" | "start" | "room")[]
  tags: string[]
}

export type ExplainedStaffTotals = { passes: number; paid_minutes: number; worked_minutes: number; minimum_top_up_minutes: number; travel_minutes: number; pool: number }

/** Det som finns när båda sidor har en verifierad lösning, också när totalskillnaden spärras (`available` falskt). */
export type ExplainedDetail = {
    basis: { left: ExplainedBasisSide; right: ExplainedBasisSide }
    total: { left_ore: number; right_ore: number; difference_ore: number | null; label: string }
    split: { available: boolean; usage_ore?: number; assumption_ore?: number; same_prices?: boolean; note?: string; reason?: string }
    items: ExplainedItem[]
    rooms: ExplainedRoom[]
    added_rooms: string[]
    sessions: {
      removed: ExplainedSession[]; added: ExplainedSession[]; changed: { before: ExplainedSession; after: ExplainedSession; paid_minutes_difference: number }[]
      unchanged: number; counts: { left: number; right: number; removed: number; added: number; changed: number }; truncated: boolean
      external: { left: number; right: number; avoided: ExplainedSession[]; added: ExplainedSession[]; avoided_ore: number; added_ore: number }
    }
    staffing: {
      unit: string; left: ExplainedStaffTotals; right: ExplainedStaffTotals; difference: ExplainedStaffTotals
      per_day: { date: string; left_passes: number; right_passes: number; left_paid_minutes: number; right_paid_minutes: number; difference_paid_minutes: number }[]
      days_compared: number
      origin: { left: string; right: string }
      observed_staffing: { left: { date: string; room_id: string; staff_count: number; paid_minutes: number | null; origin: ExplainOrigin }[]; right: { date: string; room_id: string; staff_count: number; paid_minutes: number | null; origin: ExplainOrigin }[] }
    }
    exams: { compared: number; unchanged: number; time_changed: number; room_changed: number; changed: ExplainedExamChange[]; changed_count: number; truncated: boolean }
    realization: {
      items: { room_id: string; name: string; kind: string; modelled_saving_ore: number; realization: ExplainedRealization }[]
      summary: { modelled_saving_ore: number; verified_ore: number; conditional_ore: number; blocked_ore: number; note: string }
      contract_basis: { pack_id: string; origin: ExplainOrigin; sha256: string } | null
      note: string
    }
    savings_kinds: {
      historical: { available: boolean; note: string }
      model_calculated: { available: boolean; difference_ore: number | null }
      theoretical_annual_potential: { available: boolean; ore: number | null; note: string }
      verified_realisable: { available: boolean; ore: number; note: string }
    }
    summary: string | null
    data_quality: { simulated: boolean; flags: { key: string; text: string }[] }
}

/** `available` är sant bara när en total skillnad kan redovisas; annars står skälen i `reasons` och detaljerna är märkta ofullständiga. */
export type AbcExplained = { available: boolean; reasons: string[]; notes: string[] } & Partial<ExplainedDetail>
