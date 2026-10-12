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
 * och aldrig en enskild siffra som kan läsas som besparing. Kostnaden är en modellkostnad, inte faktisk kostnad.
 */
export type CostStatement = { proven: boolean; headline: string; note: string }
export function costStatement(costOre: number | null, boundOre: number | null, provenOptimum: boolean): CostStatement {
  if (costOre === null) return { proven: false, headline: DASH, note: "Ingen kontrollerad lösning finns ännu." }
  const proven = provenOptimum || (boundOre !== null && boundOre >= costOre)
  if (proven) return { proven: true, headline: formatKr(costOre), note: "Lägsta möjliga kostnad i modellen är bevisad. Det är ändå en modellkostnad och ingen kontrollerad besparing; jämförelse mot faktisk kostnad kräver separat underlag." }
  if (boundOre === null) return { proven: false, headline: `högst ${formatKr(costOre)}`, note: "Ingen undre gräns är bevisad än. Kostnaden är bara den lägsta kontrollerade hittills och är inte ett bevisat optimum." }
  return {
    proven: false, headline: `${rangeKr(boundOre, costOre)}`,
    note: "Det lägsta möjliga är inte bevisat. Den lägsta möjliga kostnaden i modellen ligger någonstans i intervallet. Intervallet är ingen besparing.",
  }
}

const rangeKr = (lowOre: number, highOre: number): string => `${number.format(Math.round(lowOre / 100))}–${number.format(Math.round(highOre / 100))} kr`

export const DAY_STATUS_TEXT: Record<DayStatus | "pending" | "running", string> = {
  pending: "Väntar", running: "Pågår", optimal: "Klar, bästa möjliga", feasible: "Klar, går att genomföra", infeasible: "Går inte", unknown: "Tidsgräns nådd",
}

export const DAY_STATUS_HELP: Record<DayStatus | "pending" | "running", string> = {
  pending: "Dagen har inte kontrollerats ännu.",
  running: "Dagen kontrolleras just nu.",
  optimal: "Dagen går att genomföra och är bevisat den billigaste möjliga för dagen.",
  feasible: "Dagen går att genomföra, men det är inte bevisat att den är billigast möjliga.",
  infeasible: "Dagen går inte att genomföra med den fasta planen. Den rättas i nästa steg.",
  unknown: "Kontrollen hann inte bli klar inom tidsgränsen och gav inget säkert svar.",
}

const KIND_TEXT: Record<string, string> = {
  warm_start: "Förra körningens placering, dag för dag", warm_start_check: "Förra körningens placering, dag för dag",
  day_checks: "Kontroll av varje dag mot den grova planen", economic_plan: "Kontroll av varje dag mot den grova planen", exact: "Noggrann kontroll av varje dag",
  history: "Försök att behålla ursprungliga tider", history_swap: "Försök att behålla ursprungliga tider",
  repair: "Rättning av dagar som inte gick",
}
export const kindLabel = (kind: string): string => KIND_TEXT[kind] ?? `Kontroller (${kind})`

/** Var en lösning kom ifrån, med lösarens egna beteckningar översatta ("warm start", "round 2", "round 2 history"). */
export function sourceLabel(source: string | null | undefined): string {
  if (!source) return DASH
  const text = source.trim()
  if (/^warm start/i.test(text)) return "förra körningens placering"
  const history = /^round\s+(\d+)\s+history$/i.exec(text)
  if (history) return `varv ${history[1]}, försök att behålla ursprungliga tider`
  const round = /^round\s+(\d+)$/i.exec(text)
  if (round) return `varv ${round[1]} av grov plan och dagkontroll`
  return text
}

export const DECISION_TEXT: Record<WarmStartDecisionName, { label: string; help: string }> = {
  accepted: { label: "Användes", help: "Förra körningens placering klarade den nya kontrollen och blev första kontrollerade lösning." },
  rejected: { label: "Användes inte", help: "Förra körningens placering klarade inte kontrollen mot de nya reglerna och användes inte som lösning." },
  hint_only: { label: "Endast som ledtråd", help: "Förra körningens placering gavs som ledtråd men räknades inte som kontrollerad lösning." },
  not_used: { label: "Ingen start från förra körningen", help: "Körningen startade från noll." },
  not_recorded: { label: "Ej registrerat", help: "Körningen saknar uppgift om start från en tidigare körning. Det betyder inte att den inte användes." },
}

export const OUTCOME_TEXT: Record<string, string> = {
  optimal: "Bevisat lägsta kostnad i modellen",
  feasible_not_proven: "Lösning som går att genomföra, lägsta kostnad ej bevisad",
  feasible: "Lösning som går att genomföra, lägsta kostnad ej bevisad",
  infeasible: "Ingen lösning går att genomföra",
  unknown: "Ingen lösning inom tidsgränsen",
  no_feasibility_conclusion: "Ingen lösning inom tidsgränsen",
  failed: "Körningen misslyckades",
  cancelled: "Stoppad av användaren",
}
export const outcomeLabel = (outcome: string | null | undefined): string => outcome ? OUTCOME_TEXT[outcome] ?? outcome : DASH

export const JOB_STATUS_TEXT: Record<string, string> = { running: "Pågår", completed: "Klar", failed: "Misslyckades", cancelled: "Stoppad" }

export const VERDICT_TEXT: Record<string, string> = {
  pass: "Godkänd (pass)", fail: "Underkänd (fail)", not_evaluated: "Ej bedömd (not_evaluated)", not_applicable: "Gäller inte (not_applicable)",
}

export const FIRST_SOLUTION_BASIS: Record<string, string> = {
  solver_start: "räknat från att beräkningen startade", run_start: "räknat från att körningen startade",
}
export const firstSolutionBasisText = (basis: string | null | undefined): string => basis ? FIRST_SOLUTION_BASIS[basis] ?? basis : ""

export type VerdictView ={ status: string | null; reason: string | null; details: [string, string][] }

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
