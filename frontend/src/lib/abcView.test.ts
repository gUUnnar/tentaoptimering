import assert from "node:assert/strict"
import { describe, it } from "node:test"
import type { AbcRun } from "./abcTypes.ts"
import { compareOptions, costSideText, latestOfKind, outcomeText, percentOf, runsAsScenarios, scenarioIdForRun, utilizationSeries, wishLines } from "./abcView.ts"

const run = (over: Partial<AbcRun>): AbcRun => ({
  run_id: "20261014T120000Z-joint_base", name: "B – Grundoptimering, 12:00", named: true, kind: "B", base_run_id: null, problem_id: "joint_base",
  created_at: null, solver_outcome: "feasible_not_proven", has_placement: true, cost_ore: 150_000_000, exam_count: 10, changes_from_base: null, current_underlay: true, ...over,
})

describe("A, B och C i gränssnittet", () => {
  it("scenario-id för en körning följer serverns regel", () => {
    assert.equal(scenarioIdForRun("20261014T120000Z-joint_base"), "run-20261014t120000z-joint_base")
    assert.ok(scenarioIdForRun("x".repeat(200)).length <= 80)
  })
  it("A står först bland jämförelsealternativen och körningar behåller sin ordning", () => {
    const options = compareOptions([run({}), run({ run_id: "b", name: "Egen", kind: "C" })])
    assert.deepEqual(options.map(item => item.ref), ["actual", "20261014T120000Z-joint_base", "b"])
    assert.match(options[2].label, /^C · Egen$/)
  })
  it("utfall utan lösning visar ingen kostnad", () => {
    assert.equal(outcomeText(run({ has_placement: false, solver_outcome: "infeasible", cost_ore: null })), "Ingen genomförbar lösning")
    assert.match(outcomeText(run({})), /optimum ej bevisat, modellkostnad/)
    assert.match(outcomeText(run({ solver_outcome: "optimal" })), /^Bevisat optimal/)
  })
  it("senaste körningen av en typ föredrar en med lösning", () => {
    const failed = run({ run_id: "new", has_placement: false })
    const ok = run({ run_id: "old" })
    assert.equal(latestOfKind([failed, ok], "B")?.run_id, "old")
    assert.equal(latestOfKind([failed], "B")?.run_id, "new")
    assert.equal(latestOfKind([failed], "C"), null)
  })
  it("en körning blir ett scenarioval med samma urval som sitt scenario", () => {
    const subset = { plan_area: "Uppsala", selection: "rule", exam_count: 5, description: "x" } as never
    const [item] = runsAsScenarios([run({})], [{ id: "joint_base", name: "B", description: "", problem_id: "joint_base", subset }])
    assert.equal(item.id, "run-20261014t120000z-joint_base")
    assert.equal(item.origin, "run")
    assert.equal(item.subset, subset)
  })
  it("kostnadssidor skiljer historisk kostnad från modellkostnad", () => {
    assert.equal(costSideText({ kind: "historical", available: false, note: "n" }).kindLabel, "Historisk kostnad")
    assert.equal(costSideText({ kind: "model", available: false }).value, "ingen verifierad lösning")
    assert.match(costSideText({ kind: "model", available: true, total_ore: 100_000, lower_bound_ore: null, gap_ore: null, proven_optimum: false, components: [], note: "m" }).value, /1\s?000 kr/)
  })
  it("beläggningsserien slår ihop datum och lämnar saknade värden tomma", () => {
    const day = (date: string, share: number | null) => ({ date, exams: 1, seats: 1, rooms: 1, capacity_known: 1, peak_seats_in_known_rooms: 1, share })
    assert.deepEqual(utilizationSeries([day("2026-01-12", 0.5)], [day("2026-01-13", 0.7)]), [
      { date: "2026-01-12", left: 0.5, right: null }, { date: "2026-01-13", left: null, right: 0.7 }])
  })
  it("andelar och önskemålsrader utan tolkning", () => {
    assert.equal(percentOf(1, 4), 25)
    assert.equal(percentOf(1, 0), null)
    const lines = wishLines({ available: true, orders: 10, status: { reserves_given: 4, reason_only: 4, neither: 2 }, reason_without_letters: 1 })
    assert.equal(lines.length, 3)
    assert.match(lines[1], /varav 1 utan bokstäver/)
    assert.match(wishLines({ available: false, reason: "saknas" })[0], /saknas/)
  })
})
