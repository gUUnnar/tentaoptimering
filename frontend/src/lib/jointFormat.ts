import type { DayStatus, WarmStartDecisionName } from "./jointTypes.ts"

const number = new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 0 })
const decimal = new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 1, minimumFractionDigits: 1 })

export const DASH = "–"

/** Öre till hela kronor, t.ex. "1 823 000 kr". */
export function formatKr(ore: number | null | undefined): string {
  return ore === null || ore === undefined ? DASH : `${number.format(Math.round(ore / 100))} kr`
}

/** Kort kronform för diagramaxlar, t.ex. "1,82 Mkr". */
export function formatMkr(ore: number): string {
  return `${new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 2 }).format(ore / 100 / 1_000_000)} Mkr`
}

export function formatGap(fraction: number | null | undefined): string {
  return fraction === null || fraction === undefined ? DASH : `${decimal.format(fraction * 100)} %`
}

/** Sekunder som "12 s" eller "2 min 04 s". */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) return DASH
  if (seconds < 60) return `${seconds < 10 ? decimal.format(seconds) : number.format(seconds)} s`
  const whole = Math.round(seconds)
  return `${Math.floor(whole / 60)} min ${String(whole % 60).padStart(2, "0")} s`
}

export const formatCount = (value: number | null | undefined): string => value === null || value === undefined ? DASH : number.format(value)

/**
 * Ärlig kostnadsredovisning: utan bevisat optimum visas ett intervall "undre gräns–verifierad kostnad"
 * och aldrig en enskild siffra som kan läsas som besparing.
 */
export type CostStatement = { proven: boolean; headline: string; note: string }
export function costStatement(costOre: number | null, boundOre: number | null, outcome: string | null): CostStatement {
  if (costOre === null) return { proven: false, headline: DASH, note: "Ingen verifierad lösning finns ännu." }
  const proven = outcome === "optimal" || (boundOre !== null && boundOre >= costOre)
  if (proven) return { proven: true, headline: formatKr(costOre), note: "Bevisat optimum för den modellerade kostnaden. Det är ännu ingen verifierad besparing; jämförelse mot faktisk kostnad kräver separat underlag." }
  if (boundOre === null) return { proven: false, headline: `högst ${formatKr(costOre)}`, note: "Ingen undre gräns är bevisad. Kostnaden är bara en övre gräns och är inte ett bevisat optimum." }
  return {
    proven: false, headline: `${rangeKr(boundOre, costOre)}`,
    note: "Optimum är inte bevisat. Den verkliga minimikostnaden ligger någonstans i intervallet. Intervallet är inte en besparing.",
  }
}

const rangeKr = (lowOre: number, highOre: number): string => `${number.format(Math.round(lowOre / 100))}–${number.format(Math.round(highOre / 100))} kr`

export const DAY_STATUS_TEXT: Record<DayStatus | "pending" | "running", string> = {
  pending: "Väntar", running: "Pågår", optimal: "Optimal", feasible: "Genomförbar", infeasible: "Ogenomförbar", unknown: "Tidsgräns",
}

export const DAY_STATUS_HELP: Record<DayStatus | "pending" | "running", string> = {
  pending: "Kontrollen har inte körts ännu.",
  running: "Kontrollen körs (uppskattat; kontraktet saknar händelse för påbörjad dag).",
  optimal: "Dagen är löst och kostnaden bevisad optimal för dagen.",
  feasible: "Dagen har en genomförbar lösning men optimum är inte bevisat.",
  infeasible: "Dagen saknar genomförbar lösning med den fasta planen.",
  unknown: "Kontrollen avbröts av tidsgränsen utan avgörande svar.",
}

const KIND_TEXT: Record<string, string> = {
  warm_start: "Varmstartens dagkontroll", warm_start_check: "Varmstartens dagkontroll", day_checks: "Dagkontroller av ekonomisk plan",
  exact: "Exakta dagkontroller", economic_plan: "Dagkontroller av ekonomisk plan", history: "Historikbyten", history_swap: "Historikbyten", repair: "Reparation",
}
export const kindLabel = (kind: string): string => KIND_TEXT[kind] ?? `Kontroller (${kind})`

export const DECISION_TEXT: Record<WarmStartDecisionName, { label: string; help: string }> = {
  accepted: { label: "Accepterad", help: "Den tidigare placeringen klarade omkontrollen och blev första verifierade lösning." },
  rejected: { label: "Avvisad", help: "Den tidigare placeringen klarade inte omkontrollen mot de nya reglerna och användes inte som lösning." },
  hint_only: { label: "Endast ledtråd", help: "Placeringen gavs som ledtråd till lösaren men räknades inte som verifierad lösning." },
  not_used: { label: "Ej använd", help: "Ingen varmstart användes i denna körning." },
  not_recorded: { label: "Ej registrerad", help: "Körningen saknar uppgift om varmstart. Det betyder inte att den inte användes." },
}

export const OUTCOME_TEXT: Record<string, string> = {
  optimal: "Bevisat optimum",
  feasible_not_proven: "Genomförbar lösning, optimum ej bevisat",
  feasible: "Genomförbar lösning, optimum ej bevisat",
  infeasible: "Ingen genomförbar lösning",
  unknown: "Ingen lösning inom tidsgränsen",
  cancelled: "Stoppad av användaren",
}
export const outcomeLabel = (outcome: string | null | undefined): string => outcome ? OUTCOME_TEXT[outcome] ?? outcome : DASH

export const JOB_STATUS_TEXT: Record<string, string> = { running: "Pågår", completed: "Klar", failed: "Misslyckades", cancelled: "Stoppad" }

export const VERDICT_TEXT: Record<string, string> = {
  pass: "Godkänd (pass)", fail: "Underkänd (fail)", not_evaluated: "Ej utvärderad (not_evaluated)", not_applicable: "Ej tillämplig (not_applicable)",
}

export type VerdictView = { status: string | null; reason: string | null; details: [string, string][] }

/** Läser en dom som antingen en statussträng eller ett objekt. Saknat värde blir status null, aldrig ett godkännande. */
export function describeVerdict(value: unknown): VerdictView {
  if (value === null || value === undefined) return { status: null, reason: null, details: [] }
  if (typeof value === "string") return { status: value, reason: null, details: [] }
  if (typeof value !== "object") return { status: String(value), reason: null, details: [] }
  const { status, reason, ...rest } = value as Record<string, unknown>
  const text = (item: unknown) => typeof item === "string" ? item : JSON.stringify(item)
  return {
    status: typeof status === "string" ? status : null,
    reason: typeof reason === "string" ? reason : null,
    details: Object.entries(rest).map(([key, item]) => [key, text(item)] as [string, string]),
  }
}
