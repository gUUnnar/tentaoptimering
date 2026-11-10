import { formatKr } from "./jointFormat.ts"
import type { SavingsReady } from "./savingsApi.ts"

/** Andel av kostnaden med låsta datum som potentialen utgör, i hela procent; null om den saknar kostnad. */
export function savingsPercent(baselineKr: number, potentialKr: number): number | null {
  return baselineKr > 0 ? Math.round((potentialKr / baselineKr) * 100) : null
}

export type SavingsHeadline = { amount: string; versus: string; range: string | null; positive: boolean }

/** Rubrik och stödtexter för potentialen. Intervallet visas bara när sökningarna inte är bevisat optimala. */
export function savingsHeadline(result: SavingsReady): SavingsHeadline {
  const { potential_kr: potential, potential_low_kr: low, potential_high_kr: high, baseline, run } = result
  const percent = savingsPercent(baseline.cost_kr, potential)
  const sign = percent === null || percent === 0 ? "" : percent > 0 ? "−" : "+"
  const versus = `Låsta datum ${formatKr(baseline.cost_kr)} per år, den här körningen ${formatKr(run.cost_kr)}${percent === null ? "" : ` (${sign}${Math.abs(percent)} %)`}`
  const range = low === high ? null : `Mellan ${formatKr(low)} och ${formatKr(high)} beroende på hur nära optimum sökningarna kom.`
  return { amount: `${formatKr(potential)} per år`, versus, range, positive: potential > 0 }
}
