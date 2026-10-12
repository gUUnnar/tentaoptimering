import type { CompareParameterChange, CompareResult, CompareRunRef, MetricDelta, MetricKey } from "./jointTypes.ts"
import { DASH, formatCount, formatDuration, formatKr } from "./jointFormat.ts"
import { formatLooseValue } from "./paramFormat.ts"

const num = (value: unknown): number | null => typeof value === "number" && Number.isFinite(value) ? value : null
const str = (value: unknown): string | null => typeof value === "string" ? value : null
const strings = (value: unknown): string[] => Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && item !== "") : []
const obj = (value: unknown): Record<string, unknown> => value && typeof value === "object" ? value as Record<string, unknown> : {}

const toRef = (value: unknown): CompareRunRef | null => {
  const raw = obj(value)
  return typeof raw.run_id === "string" ? {
    run_id: raw.run_id, scenario_id: str(raw.scenario_id) ?? "", created_at: str(raw.created_at), problem_id: str(raw.problem_id),
    solver_outcome: str(raw.solver_outcome), has_verified_solution: typeof raw.has_verified_solution === "boolean" ? raw.has_verified_solution : null,
  } : null
}

const METRIC_KEYS: MetricKey[] = ["cost_ore", "lower_bound_ore", "gap_ore", "changed_exams", "staff_pool_size", "rooms_used", "wall_time_seconds", "first_solution_seconds"]

/** Läser jämförelsesvaret defensivt: saknade mått blir null, aldrig noll. */
export function toCompareResult(raw: unknown): CompareResult {
  const body = obj(raw)
  const metrics: CompareResult["metrics"] = {}
  const source = obj(body.metrics)
  for (const key of METRIC_KEYS) {
    if (!(key in source)) continue
    const item = obj(source[key])
    metrics[key] = { old: num(item.old), new: num(item.new), delta: num(item.delta) }
  }
  const run = toRef(body.run)
  return {
    run: run ?? { run_id: "", scenario_id: "", created_at: null },
    base: toRef(body.base),
    comparable: body.comparable === true,
    reason: str(body.reason),
    parameter_changes: (Array.isArray(body.parameter_changes) ? body.parameter_changes : []).map(item => {
      const change = obj(item)
      return { id: str(change.id) ?? "", label: str(change.label) ?? str(change.id) ?? "", group: str(change.group) ?? "", unit: str(change.unit), old: change.old, new: change.new }
    }),
    metrics,
    uncertainty_ore: num(body.uncertainty_ore),
    interpretable: typeof body.interpretable === "boolean" ? body.interpretable : null,
    interpretation: str(body.interpretation) ?? "",
    assumption_changes: { cost: strings(obj(body.assumption_changes).cost), demand: strings(obj(body.assumption_changes).demand) },
  }
}

// ---- Presentation --------------------------------------------------------------------------------------------------

type MetricKind = "money" | "count" | "seconds"
export const METRIC_DEFS: { key: MetricKey; label: string; kind: MetricKind; hint?: string }[] = [
  { key: "cost_ore", label: "Verifierad kostnad", kind: "money", hint: "Lägsta kostnad hittills som är kontrollerad (modellkostnad)." },
  { key: "lower_bound_ore", label: "Undre gräns", kind: "money", hint: "Lägsta kostnad som bevisats möjlig." },
  { key: "gap_ore", label: "Avstånd mellan dem", kind: "money", hint: "Verifierad kostnad minus undre gräns. Optimum ligger någonstans däremellan." },
  { key: "changed_exams", label: "Flyttade tentor", kind: "count" },
  { key: "staff_pool_size", label: "Vaktpool", kind: "count", hint: "Antal vakter i den anonyma poolen." },
  { key: "rooms_used", label: "Salar som används", kind: "count" },
  { key: "first_solution_seconds", label: "Tid till första lösning", kind: "seconds" },
  { key: "wall_time_seconds", label: "Total tid", kind: "seconds" },
]

const MINUS = "−"
const SAME = "Oförändrat"

function formatValue(kind: MetricKind, value: number | null): string {
  if (value === null) return DASH
  return kind === "money" ? formatKr(value) : kind === "count" ? formatCount(value) : formatDuration(value)
}

/** Skillnad med tydligt tecken. Noll skrivs "Oförändrat". Okänd skillnad skrivs som tankstreck. */
export function formatDelta(kind: MetricKind, delta: number | null): { text: string; direction: "up" | "down" | "same" | "unknown" } {
  if (delta === null) return { text: DASH, direction: "unknown" }
  const magnitude = Math.abs(delta)
  const rounded = kind === "money" ? Math.round(magnitude / 100) : kind === "count" ? Math.round(magnitude) : Math.round(magnitude * 10) / 10
  if (rounded === 0) return { text: SAME, direction: "same" }
  const body = kind === "money" ? formatKr(magnitude) : kind === "count" ? formatCount(magnitude) : formatDuration(magnitude)
  return delta > 0 ? { text: `+${body}`, direction: "up" } : { text: `${MINUS}${body}`, direction: "down" }
}

/** Har kostnads- eller efterfrågeantaganden ändrats mellan körningarna? Då jämförs inga kostnadsbelopp. */
export const assumptionsChanged = (result: CompareResult): boolean =>
  result.assumption_changes.cost.length > 0 || result.assumption_changes.demand.length > 0

const PHYSICAL_KEYS: ReadonlySet<MetricKey> = new Set(["rooms_used", "staff_pool_size", "changed_exams"])
const MONEY_KEYS: ReadonlySet<MetricKey> = new Set(["cost_ore", "lower_bound_ore", "gap_ore"])
const TIME_KEYS: ReadonlySet<MetricKey> = new Set(["wall_time_seconds", "first_solution_seconds"])
export const NOT_COMPARED_TEXT = "Jämförs inte (andra antaganden)"

export type MetricRow = {
  key: MetricKey; label: string; hint?: string; old: string; new: string; delta: string; direction: "up" | "down" | "same" | "unknown"
  /** Kostnadsrad som inte jämförs eftersom antagandena ändrats: ingen skillnad visas. */
  notCompared: boolean
  /** Fysiskt mått (salar, vaktpool, flyttade tentor) som framhävs när antaganden ändrats. */
  physical: boolean
}

export function metricRows(result: CompareResult): MetricRow[] {
  const assumptions = assumptionsChanged(result)
  const rows = METRIC_DEFS.flatMap((def): MetricRow[] => {
    const metric: MetricDelta | undefined = result.metrics[def.key]
    if (!metric) return []
    const notCompared = assumptions && result.comparable && MONEY_KEYS.has(def.key)
    // Är körningarna inte jämförbara skickar backend inga skillnader; då räknas inga fram. Ändrade antaganden: aldrig en kostnadsskillnad.
    const delta = notCompared ? null : metric.delta ?? (result.comparable && metric.old !== null && metric.new !== null ? metric.new - metric.old : null)
    const shown = formatDelta(def.kind, delta)
    // En körning utan verifierad lösning har inga lösningsmått: de visas inte ens om servern skulle skicka dem.
    const hidden = (ref: CompareResult["run"] | null) => ref?.has_verified_solution === false && !TIME_KEYS.has(def.key)
    const value = (side: number | null, ref: CompareResult["run"] | null) => formatValue(def.kind, hidden(ref) ? null : side)
    return [{
      key: def.key, label: def.label, hint: def.hint, old: value(metric.old, result.base), new: value(metric.new, result.run),
      delta: notCompared ? NOT_COMPARED_TEXT : shown.text, direction: notCompared ? "unknown" : shown.direction,
      notCompared, physical: assumptions && result.comparable && PHYSICAL_KEYS.has(def.key),
    }]
  })
  // Ändrade antaganden: de fysiska måtten är det som går att jämföra och står därför först.
  return assumptions && result.comparable ? [...rows.filter(row => row.physical), ...rows.filter(row => !row.physical)] : rows
}

export type AssumptionView = { title: string; groups: { label: string; items: string[] }[]; text: string }

/** Rutan "Antaganden har ändrats". Null när inga antaganden ändrats. */
export function assumptionView(result: CompareResult): AssumptionView | null {
  if (!assumptionsChanged(result)) return null
  const { cost, demand } = result.assumption_changes
  const groups = [
    ...(cost.length ? [{ label: "Kostnadsantaganden som ändrats", items: cost }] : []),
    ...(demand.length ? [{ label: "Efterfrågan (tentor och antal tentander) som ändrats", items: demand }] : []),
  ]
  return {
    title: "Antaganden har ändrats", groups,
    text: "Kostnadsbelopp jämförs bara mellan körningar med samma antaganden, så ingen kostnadsskillnad visas. Jämför i stället salar, bemanningspool och antal flyttade tentor.",
  }
}

export type ChangeRow = { id: string; label: string; group: string; oldText: string; newText: string }
export const changeRows = (changes: CompareParameterChange[]): ChangeRow[] =>
  changes.map(change => ({ id: change.id, label: change.label, group: change.group, oldText: formatLooseValue(change, change.old), newText: formatLooseValue(change, change.new) }))

export type InterpretationView = { tone: "interpretable" | "not_interpretable" | "unknown"; title: string; text: string }

/** Backendens tolkning är huvudmeningen. Rubriken säger om skillnaden går att tolka, med ord och inte bara färg. */
export function interpretationView(result: CompareResult): InterpretationView {
  const fallback = result.reason ?? ""
  const text = result.interpretation.trim() || fallback
  if (!result.comparable) return { tone: "not_interpretable", title: "Körningarna går inte att jämföra", text: text || "Körningarna har olika förutsättningar och kan inte jämföras kostnadsmässigt." }
  if (result.interpretable === true) return { tone: "interpretable", title: "Skillnaden går att tolka", text }
  if (result.interpretable === false) return { tone: "not_interpretable", title: "Skillnaden går inte att tolka som en förbättring eller försämring", text }
  return { tone: "unknown", title: "Det går inte att bedöma om skillnaden är tolkningsbar", text }
}

export const NO_PREVIOUS_RUN_TEXT = "Det finns ingen tidigare körning av samma scenario att jämföra med. Kör scenariot en gång till med en ändrad parameter, så visas jämförelsen här."
