import type { JointScenario, PeriodCheck, PeriodCoverage } from "./jointTypes.ts"
import { scenarioDetails } from "./jointScenarioInfo.ts"
import type { PeriodChoice } from "./period.ts"
import type { UnderlayState } from "./underlayApi.ts"
import { formatWhen } from "./underlay.ts"

const count = new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 0 })

export type UnderlayFact = { preparedAt: string; state: UnderlayState } | null

export type Fact = { key: "exams" | "area" | "period" | "underlay"; text: string; attention?: boolean }

/**
 * De fyra uppgifterna om det som ska köras, var och en en gång: antal tentor, planeringsområde, period och underlagets datum.
 * Ett valt datumintervall går före scenariots egen period, och dess tentor räknas av servern.
 */
export function scenarioFacts(scenario: JointScenario | undefined, choice: PeriodChoice | null, check: PeriodCheck | null,
  coverage: PeriodCoverage | null, underlay: UnderlayFact): Fact[] {
  const facts: Fact[] = []
  const exams = choice ? check?.ready_events : scenario?.subset?.exam_count
  if (exams !== null && exams !== undefined) facts.push({ key: "exams", text: `${count.format(exams)} ${exams === 1 ? "tenta" : "tentor"}` })
  if (scenario?.subset?.plan_area) facts.push({ key: "area", text: scenario.subset.plan_area })
  const period = choice ? `${choice.from} – ${choice.to}` : scenarioDetails(scenario).period ?? (coverage?.demand ? `${coverage.demand.first} – ${coverage.demand.last}` : null)
  if (period) facts.push({ key: "period", text: period })
  if (underlay) {
    const current = underlay.state === "current"
    facts.push({ key: "underlay", text: `Underlag ${formatWhen(underlay.preparedAt)}${current ? "" : ", inte aktuellt"}`, attention: !current })
  }
  return facts
}
