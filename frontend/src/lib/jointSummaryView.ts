import type { JointSummary } from "./jointTypes.ts"
import { costStatement, formatCount, formatDuration, formatGap, formatKr, firstSolutionBasisText, outcomeLabel, sourceLabel, type CostStatement } from "./jointFormat.ts"
import { gapFraction } from "./jointState.ts"

export type ChangedParameter = { id: string; label: string | null }

/** Parametrar som avviker från standard, med etikett från summary, annars från parameterlistan, annars bara id. */
export function changedParameters(summary: JointSummary, labels: Record<string, string>): ChangedParameter[] {
  return summary.parameters_changed_from_default.map(item => ({ id: item.id, label: item.label ?? labels[item.id] ?? null }))
}

export function changedParametersHeading(summary: JointSummary): string {
  const count = Math.max(summary.parameters_changed_from_default.length, summary.parameters_changed_count ?? 0)
  if (count === 0) return "Inga parametrar avviker från standardvärdena i den här körningen."
  return `${count} ${count === 1 ? "parameter avviker" : "parametrar avviker"} från standardvärdet i den här körningen:`
}

export type StatView = { label: string; value: string; hint?: string }

export type SummaryView =
  | { verified: false; reason: string; stats: StatView[]; outcomeText: null; statement: null }
  | { verified: true; reason: null; stats: StatView[]; outcomeText: string; statement: CostStatement }

/**
 * Det som sammanfattningen visar. Utan verifierad lösning finns varken kostnad, gräns, intervall eller andra
 * lösningsmått: bara skälet. Aldrig en siffra som kan läsas som en lösning.
 */
export function summaryView(summary: JointSummary): SummaryView {
  if (!summary.has_verified_solution) {
    const fallback = summary.cancelled ? "Körningen stoppades innan någon fullständig, kontrollerad lösning fanns." : "Körningen har ingen fullständig, kontrollerad lösning."
    const stats: StatView[] = summary.wall_seconds !== null ? [{ label: "Total tid", value: formatDuration(summary.wall_seconds) }] : []
    return { verified: false, reason: summary.unverified_reason ?? fallback, stats, outcomeText: null, statement: null }
  }
  const gap = summary.gap ?? gapFraction(summary.cost_ore, summary.bound_ore)
  const basis = firstSolutionBasisText(summary.first_solution_basis)
  const firstHint = [basis, summary.first_solution_source ? `från ${sourceLabel(summary.first_solution_source)}` : ""].filter(Boolean).join(", ")
  return {
    verified: true, reason: null, outcomeText: outcomeLabel(summary.outcome),
    statement: costStatement(summary.cost_ore, summary.bound_ore, summary.proven_optimum),
    stats: [
      { label: "Verifierad kostnad", hint: "Lägsta kostnad hittills som är kontrollerad", value: formatKr(summary.cost_ore) },
      { label: "Undre gräns", hint: "Lägsta kostnad som bevisats möjlig", value: formatKr(summary.bound_ore) },
      { label: "Gap", hint: summary.gap_ore !== null ? `${formatKr(summary.gap_ore)} över undre gräns` : "Avstånd mellan de två", value: formatGap(gap) },
      { label: "Flyttade tentor", hint: summary.exams_total !== null ? `av ${formatCount(summary.exams_total)}` : undefined, value: formatCount(summary.changed_exams) },
      { label: "Vaktpool", hint: "Antal vakter", value: formatCount(summary.staff_pool_size) },
      { label: "Tid till första lösning", hint: firstHint || undefined, value: formatDuration(summary.first_solution_seconds) },
      { label: "Total tid", value: formatDuration(summary.wall_seconds) },
    ],
  }
}
