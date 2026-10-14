import { TriangleAlert } from "lucide-react"
import { InfoTip } from "@/components/ui/info-tip"
import { scenarioDetails } from "@/lib/jointScenarioInfo"
import type { JointScenario, PeriodCoverage } from "@/lib/jointTypes"
import { coverageText } from "@/lib/period"
import { scenarioFacts, type Fact, type UnderlayFact } from "@/lib/scenarioFacts"
import type { PeriodCheck } from "@/lib/jointTypes"
import type { PeriodChoice } from "@/lib/period"

type Props = { scenario: JointScenario | undefined; choice: PeriodChoice | null; check: PeriodCheck | null; coverage: PeriodCoverage | null; underlay: UnderlayFact }

/** Det som ska köras på en rad: tentor, område, period och underlag. Längre förklaringar ligger bakom ⓘ och står bara där. */
export function ScenarioFacts({ scenario, choice, check, coverage, underlay }: Props) {
  if (!scenario) return null
  const facts = scenarioFacts(scenario, choice, check, coverage, underlay)
  const details = scenarioDetails(scenario)
  const hasMore = !!(details.description || details.coverageNote || coverage)
  return <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-slate-900" aria-label="Det som körs">
    {facts.map((fact, index) => <FactItem key={fact.key} fact={fact} first={index === 0}/>)}
    {hasMore && <InfoTip label="Mer om scenariot">
      {details.description && <span className="block">{details.description}</span>}
      {details.coverageNote && <span className="block">{details.coverageNote}</span>}
      {coverage && <span className="block">{coverageText(coverage)}{coverage.bookings ? ` Lokalbokningar finns ${coverage.bookings.first}–${coverage.bookings.last} men ger ingen efterfrågan och kan inte optimeras utan deltagarantal.` : ""}</span>}
      {coverage && <span className="block"><strong>{coverage.planning_basis.label}.</strong> {coverage.planning_basis.note}</span>}
    </InfoTip>}
  </p>
}

function FactItem({ fact, first }: { fact: Fact; first: boolean }) {
  return <>
    {!first && <span aria-hidden="true" className="text-slate-500">·</span>}
    <span className={fact.attention ? "inline-flex items-center gap-1 font-medium" : undefined}>
      {fact.attention && <TriangleAlert size={14} className="text-amber-700" aria-hidden="true"/>}{fact.text}
    </span>
  </>
}
