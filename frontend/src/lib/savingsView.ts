import { formatKr } from "./jointFormat.ts"
import type { SavingsReady } from "./savingsApi.ts"

/** Andel av Nuläge-kostnaden som potentialen utgör, i hela procent; null om Nuläge saknar kostnad. */
export function savingsPercent(baselineOre: number, potentialOre: number): number | null {
  return baselineOre > 0 ? Math.round((potentialOre / baselineOre) * 100) : null
}

export type SavingsHeadline = { amount: string; versus: string; range: string | null; positive: boolean }

/** Rubrik och stödtexter för potentialen. Intervallet visas bara när sökningarna inte är bevisat optimala. */
export function savingsHeadline(result: SavingsReady): SavingsHeadline {
  const { potential_ore: potential, potential_low_ore: low, potential_high_ore: high, baseline, run } = result
  const percent = savingsPercent(baseline.cost_ore, potential)
  const sign = percent === null || percent === 0 ? "" : percent > 0 ? "−" : "+"
  const versus = `Nuläge ${formatKr(baseline.cost_ore)} per år, den här körningen ${formatKr(run.cost_ore)}${percent === null ? "" : ` (${sign}${Math.abs(percent)} %)`}`
  const range = low === high ? null : `Mellan ${formatKr(low)} och ${formatKr(high)} beroende på hur nära optimum sökningarna kom.`
  return { amount: `${formatKr(potential)} per år`, versus, range, positive: potential > 0 }
}
