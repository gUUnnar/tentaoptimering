import type { JointScenario } from "./jointTypes.ts"

const count = new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 0 })

/** Urvalet i klartext, t.ex. "Alla tentor som är klara för modellering i Uppsala …, 1 172 tentor". */
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
 * (120 tentor: under en minut; 1 172 tentor: första lösning efter 2 minuter, tidsgräns 5 minuter).
 * Tiden beror på datorn och på vilka parametrar som ändras.
 */
export function runtimeEstimate(examCount: number | null | undefined): RuntimeEstimate | null {
  if (examCount === null || examCount === undefined) return null
  if (examCount >= 500) return { long: true, text: "Ett urval med så många tentor tar cirka 2–5 minuter. Du kan följa körningen medan den pågår och stoppa den; den bästa kontrollerade lösningen hittills sparas då." }
  if (examCount >= 100) return { long: false, text: "Ett urval av den här storleken tar oftast någon minut." }
  return { long: false, text: "Ett litet urval tar oftast under en minut." }
}

const MONTHS = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
const ISO_RANGE = /(\d{4})-(\d{2})-(\d{2})\s*(?:till|–|-|—)\s*(\d{4})-(\d{2})-(\d{2})/
const NO_LATER = /Underlaget innehåller inga tentor efter[^.]*\./i

const dayMonth = (month: string, day: string) => `${Number(day)} ${MONTHS[Number(month) - 1] ?? month}`

export type ScenarioDetails = {
  /** Perioden som scenariot omfattar, t.ex. "12 januari–31 mars 2026". Null om scenariots uppgifter inte anger någon. */
  period: string | null
  /** Scenariots egen upplysning om att underlaget saknar tentor efter perioden, om den finns. */
  coverageNote: string | null
  /** Beskrivningen utan upplysningen ovan. */
  description: string
}

/** Perioden och täckningen ur scenariots egna uppgifter (urvalets beskrivning och scenariobeskrivningen). Inget påhittas. */
export function scenarioDetails(scenario: JointScenario | undefined): ScenarioDetails {
  const description = scenario?.description ?? ""
  const range = ISO_RANGE.exec(scenario?.subset?.description ?? "") ?? ISO_RANGE.exec(description)
  let period: string | null = null
  if (range) {
    const [, y1, m1, d1, y2, m2, d2] = range
    period = y1 === y2 ? `${dayMonth(m1, d1)}–${dayMonth(m2, d2)} ${y1}` : `${dayMonth(m1, d1)} ${y1}–${dayMonth(m2, d2)} ${y2}`
  }
  const note = NO_LATER.exec(description)?.[0] ?? null
  return { period, coverageNote: note, description: note ? description.replace(note, "").replace(/\s{2,}/g, " ").trim() : description.trim() }
}
