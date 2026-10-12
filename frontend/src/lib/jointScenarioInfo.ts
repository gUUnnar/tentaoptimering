import type { JointScenario } from "./jointTypes.ts"

const count = new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 0 })

/** Urvalet i klartext, t.ex. "Hela terminen, Uppsala, 1 172 tentor". */
export function subsetText(scenario: JointScenario | undefined): string {
  const subset = scenario?.subset
  if (!subset) return ""
  const base = (subset.description ?? "").trim() || subset.plan_area
  if (subset.exam_count === null || subset.exam_count === undefined || /tentor|tentamen/i.test(base)) return base
  return `${base}, ${count.format(subset.exam_count)} tentor`
}

export type RuntimeEstimate = { text: string; long: boolean }

/**
 * Ärlig körtidsuppgift utifrån antal tentor. Underlaget är mätningar i docs/OPTIMERINGSSTRATEGI.md
 * (120 tentor: under en minut; hela terminen: första lösning efter 2 minuter, tidsgräns 5 minuter).
 * Tiden beror på datorn och på vilka parametrar som ändras.
 */
export function runtimeEstimate(examCount: number | null | undefined): RuntimeEstimate | null {
  if (examCount === null || examCount === undefined) return null
  if (examCount >= 500) return { long: true, text: "Hela terminen tar cirka 2–5 minuter. Du kan följa körningen medan den pågår och stoppa den; den bästa kontrollerade lösningen hittills sparas då." }
  if (examCount >= 100) return { long: false, text: "Ett urval av den här storleken tar oftast någon minut." }
  return { long: false, text: "Ett litet urval tar oftast under en minut." }
}
