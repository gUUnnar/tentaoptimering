import { formatKr } from "./jointFormat.ts"
import type { AbcCostSide, AbcKind, AbcRun, AbcUtilizationDay, AbcWishes } from "./abcTypes.ts"
import { ACTUAL_REF } from "./abcApi.ts"
import type { JointScenario } from "./jointTypes.ts"

/** Scenario-id som startar en ny körning från en sparad körning (samma regel som servern: `run-` och körnings-id:t i gemener). */
export const scenarioIdForRun = (runId: string): string => `run-${runId.toLowerCase()}`.slice(0, 80)

/** Id:t för grundoptimeringens scenario (B). */
export const BASE_SCENARIO_ID = "joint_base"

export const KIND_TITLE: Record<AbcKind, string> = { A: "A – Faktisk bokning", B: "B – Grundoptimering", C: "C – Egen körning" }

export const KIND_EXPLANATION: Record<AbcKind, string> = {
  A: "Hur tentorna faktiskt bokades: datum, tid, salar och bokade platser, utan någon optimering. Ineffektiva bokningar återges som de är.",
  B: "Optimering utifrån verksamhetens önskemål (önskat datum och reservdatum) med dokumenterade grundvärden.",
  C: "Optimering med parametrar du själv valt. Du kan göra hur många som helst och jämföra dem med A, B och varandra.",
}

/** Resultatet av en körning i klartext, utan att presentera en kostnad som saknar verifierad lösning. */
export function outcomeText(run: Pick<AbcRun, "solver_outcome" | "has_placement" | "cost_ore">): string {
  if (!run.has_placement) return run.solver_outcome === "infeasible" ? "Ingen genomförbar lösning" : "Ingen lösning"
  const cost = run.cost_ore === null ? "" : `, modellkostnad ${formatKr(run.cost_ore)}`
  return run.solver_outcome === "optimal" ? `Bevisat optimal${cost}` : `Lösning, optimum ej bevisat${cost}`
}

/** Jämförelsealternativen: A först, sedan körningarna i den ordning de kommer (senaste först). */
export function compareOptions(runs: AbcRun[]): { ref: string; label: string }[] {
  return [{ ref: ACTUAL_REF, label: KIND_TITLE.A }, ...runs.map(run => ({ ref: run.run_id, label: `${run.kind} · ${run.name}` }))]
}

/** Den senaste körningen av en typ som har en lösning (annars den senaste av typen), eller null. */
export function latestOfKind(runs: AbcRun[], kind: "B" | "C"): AbcRun | null {
  const of = runs.filter(run => run.kind === kind)
  return of.find(run => run.has_placement) ?? of[0] ?? null
}

/** Scenarioposter för körningar så att en körning kan väljas som utgångspunkt på samma sätt som ett scenario. */
export function runsAsScenarios(runs: AbcRun[], scenarios: JointScenario[]): JointScenario[] {
  return runs.map(run => {
    const base = scenarios.find(item => item.problem_id === run.problem_id)
    return {
      id: scenarioIdForRun(run.run_id), name: run.name, problem_id: run.problem_id ?? "", origin: "run" as const,
      description: `Utgår från körningen ”${run.name}” och dess parametrar.`, subset: base?.subset ?? null,
    }
  })
}

/** Andel i procent av en total, avrundad till heltal; null om totalen saknas. */
export const percentOf = (value: number | null | undefined, total: number | null | undefined): number | null =>
  value === null || value === undefined || !total ? null : Math.round((value / total) * 100)

/** Kostnadssidan i klartext: vilken sorts kostnad det är, och att den inte finns om den saknas. */
export function costSideText(side: AbcCostSide): { kindLabel: string; value: string; note: string | null } {
  if (side.kind === "historical") return { kindLabel: "Historisk kostnad", value: "saknas i underlaget", note: side.note }
  if (!side.available) return { kindLabel: "Modellkostnad", value: "ingen verifierad lösning", note: null }
  return { kindLabel: "Modellkostnad", value: formatKr(side.total_ore), note: side.note }
}

/** Beläggningen över tid som serie för diagrammet: ett datum per punkt med båda sidornas andel (null där en sida saknar uppgift). */
export function utilizationSeries(left: AbcUtilizationDay[], right: AbcUtilizationDay[]): { date: string; left: number | null; right: number | null }[] {
  const days = [...new Set([...left, ...right].map(item => item.date))].sort()
  const byDate = (rows: AbcUtilizationDay[]) => new Map(rows.map(row => [row.date, row.share]))
  const a = byDate(left), b = byDate(right)
  return days.map(date => ({ date, left: a.get(date) ?? null, right: b.get(date) ?? null }))
}

/** Hur komplett verksamhetens önskemål är, som korta rader. Inget tolkas: motiveringarnas innehåll ingår inte. */
export function wishLines(wishes: AbcWishes): string[] {
  if (!wishes.available || !wishes.status || !wishes.orders) return [wishes.reason ?? "Önskemålen saknas i underlaget."]
  const s = wishes.status
  const lines = [
    `${wishes.orders} bokningsbeställningar. Reservdatum angivna för ${s.reserves_given ?? 0}.`,
    `${s.reason_only ?? 0} saknar reservdatum men har en motivering (varav ${wishes.reason_without_letters ?? 0} utan bokstäver, till exempel ”.” eller ”-”).`,
    `${s.neither ?? 0} saknar både reservdatum och motivering.`,
  ]
  if (wishes.orders_with_conflicting_wishes) lines.push(`${wishes.orders_with_conflicting_wishes} beställningar har motstridiga önskemål mellan sina rader.`)
  return lines
}
