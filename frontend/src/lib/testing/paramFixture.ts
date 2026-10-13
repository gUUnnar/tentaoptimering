import type { CompareResult, ParameterInfo } from "../jointTypes.ts"

// Testdata för parameterlogiken. Formen följer kontraktet GET /api/joint-runs/parameters. Värdena är påhittade.
// Appkod får aldrig importera den här filen.

const base = { default: null, scenario_value: null, value: null, differs_from_default: false, basis: "assumption", engine_support: "implemented", editable: true, choices: null, unit: null, help_text: "Hjälptext.", advanced: false }
let order = 0
const make = (patch: Partial<ParameterInfo> & Pick<ParameterInfo, "id" | "value_type">): ParameterInfo => {
  const value = patch.value !== undefined ? patch.value : patch.default
  return { ...base, label: patch.id, group: "Test", order: order++, ...patch, default: patch.default, scenario_value: patch.scenario_value ?? null, value } as ParameterInfo
}

export const PARAMETERS: ParameterInfo[] = [
  make({ id: "window.later_days", value_type: "integer", unit: "days", default: 0, label: "Får senareläggas", group: "Tidsflexibilitet" }),
  make({ id: "calendar.weekdays", value_type: "integer_list", default: [1, 2, 3, 4, 5, 6, 7], label: "Tillåtna veckodagar", group: "Tidsflexibilitet" }),
  make({ id: "calendar.start_times", value_type: "time_list", default: ["08:00", "14:00"], label: "Tillåtna starttider", group: "Tidsflexibilitet" }),
  make({ id: "calendar.start_date", value_type: "date", default: "", label: "Första tillåtna datum", group: "Tidsflexibilitet" }),
  make({ id: "calendar.end_date", value_type: "date", default: "", label: "Sista tillåtna datum", group: "Tidsflexibilitet" }),
  make({ id: "calendar.earliest_start_time", value_type: "time", default: "08:00", label: "Tidigaste start", group: "Tidsflexibilitet" }),
  make({ id: "demand.rounding", value_type: "choice", default: "up", label: "Avrundning", group: "Efterfrågan", choices: [{ value: "up", label: "Uppåt" }, { value: "nearest", label: "Närmaste" }] }),
  make({ id: "rooms.selection", value_type: "room_id_list", default: [], label: "Lokaler som får användas", group: "Lokaler" }),
  make({ id: "flex.movable_types", value_type: "string_list", default: ["ordinarie", "omtenta", "dugga", "hybrid"], label: "Flyttbara tentamenstyper", group: "Tidsflexibilitet" }),
  make({ id: "rooms.allow_split", value_type: "boolean", default: true, label: "Tillåt delning", group: "Lokaler" }),
  make({ id: "cost.staff_session_ore", value_type: "integer", unit: "ore_per_session", default: 125000, label: "Vaktkostnad per pass", group: "Kostnader" }),
  make({ id: "cost.annualization_factor", value_type: "number", unit: "factor", default: 1.5, label: "Årsfaktor", group: "Kostnader" }),
  make({ id: "staffing.ladder", value_type: "staffing_ladder", label: "Bemanningstrappa", group: "Bemanning",
    default: [{ max_participants: 50, required_staff: 1 }, { max_participants: 150, required_staff: 2 }, { max_participants: 300, required_staff: 3 }] }),
  make({ id: "staffing.shifts", value_type: "time_range_list", default: [{ start: "07:30", end: "19:30" }], label: "Arbetspass", group: "Bemanning" }),
  make({ id: "calendar.blocked_ranges", value_type: "date_range_list", default: [], label: "Spärrade perioder", group: "Tidsflexibilitet" }),
  make({ id: "digital.compatibility_matrix", value_type: "matrix", default: {}, label: "Kompatibilitetsmatris", group: "Digitalt", editable: true }),
  make({ id: "rules.keep_course_order", value_type: "boolean", default: true, label: "Behåll ordningen inom kurs", group: "Regler", editable: false, engine_support: "contract_only" }),
  make({ id: "solver.seed", value_type: "integer", default: 0, label: "Slumpfrö", group: "Mål", advanced: true }),
]

export const byId = (id: string): ParameterInfo => {
  const found = PARAMETERS.find(item => item.id === id)
  if (!found) throw new Error(`Saknas i testdata: ${id}`)
  return found
}

export const COMPARE_OK: CompareResult = {
  run: { run_id: "r2", scenario_id: "joint_real_subset", created_at: "2026-10-12T10:00:00" },
  base: { run_id: "r1", scenario_id: "joint_real_subset", created_at: "2026-10-12T09:00:00" },
  comparable: true, reason: null,
  parameter_changes: [{ id: "cost.staff_session_ore", label: "Vaktkostnad per pass", group: "Kostnader", unit: "ore_per_session", old: 125000, new: 130000 }],
  metrics: {
    cost_ore: { old: 182_300_000, new: 181_000_000, delta: -1_300_000 },
    lower_bound_ore: { old: 177_300_000, new: 177_300_000, delta: 0 },
    changed_exams: { old: 242, new: 250, delta: 8 },
    wall_time_seconds: { old: 299.2, new: 120, delta: -179.2 },
    first_solution_seconds: { old: 109.6, new: null, delta: null },
  },
  assumption_changes: { cost: [], demand: [] },
  uncertainty_ore: 5_000_000, interpretable: false,
  interpretation: "Kostnaden sjönk med 13 000 kr, men det är mindre än osäkerheten (50 000 kr).",
}
