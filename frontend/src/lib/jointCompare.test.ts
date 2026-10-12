import assert from "node:assert/strict"
import { describe, it } from "node:test"
import { changeRows, formatDelta, interpretationView, metricRows, toCompareResult } from "./jointCompare.ts"
import { costStatement, describeVerdict, formatDuration, formatGap, formatKr, kindLabel, sourceLabel } from "./jointFormat.ts"
import { COMPARE_OK } from "./testing/paramFixture.ts"

describe("jämförelse av körningar", () => {
  it("läser svaret defensivt: saknade mått blir null, aldrig noll", () => {
    const result = toCompareResult({ run: { run_id: "r2", scenario_id: "s" }, base: null, comparable: false, reason: "Ingen tidigare körning.", metrics: { cost_ore: { old: null, new: 5 } } })
    assert.equal(result.base, null)
    assert.equal(result.metrics.cost_ore?.delta, null)
    assert.equal(result.metrics.cost_ore?.new, 5)
    assert.equal(result.metrics.changed_exams, undefined)
    assert.equal(result.interpretable, null)
    assert.deepEqual(result.parameter_changes, [])
  })

  it("formaterar skillnader med tydligt tecken", () => {
    assert.deepEqual(formatDelta("money", -1_300_000), { text: "−13 000 kr", direction: "down" })
    assert.equal(formatDelta("count", 8).text, "+8")
    assert.equal(formatDelta("count", 0).text, "Oförändrat")
    assert.equal(formatDelta("money", 40).text, "Oförändrat", "under en krona räknas som oförändrat")
    assert.equal(formatDelta("seconds", null).text, "–")
    assert.match(formatDelta("seconds", -179.2).text, /^−2 min 59 s$/)
  })

  it("måtttabellen visar gammalt, nytt och skillnad och räknar fram saknad skillnad", () => {
    const rows = metricRows(COMPARE_OK)
    const cost = rows.find(row => row.key === "cost_ore")!
    assert.match(cost.old, /^1\s823\s000 kr$/)
    assert.match(cost.new, /^1\s810\s000 kr$/)
    assert.match(cost.delta, /^−13 000 kr$/)
    assert.equal(rows.find(row => row.key === "lower_bound_ore")!.delta, "Oförändrat")
    assert.equal(rows.find(row => row.key === "changed_exams")!.delta, "+8")
    const first = rows.find(row => row.key === "first_solution_seconds")!
    assert.equal(first.new, "–")
    assert.equal(first.delta, "–")
    assert.equal(first.direction, "unknown")
    assert.equal(rows.some(row => row.key === "rooms_used"), false, "mått som backend inte skickar visas inte")
    const computed = metricRows({ ...COMPARE_OK, metrics: { staff_pool_size: { old: 40, new: 38, delta: null } } })
    assert.equal(computed[0].delta, "−2")
  })

  it("ej jämförbara körningar: inga skillnader räknas fram och orsaken visas", () => {
    const result = toCompareResult({
      run: { run_id: "r2", scenario_id: "s", problem_id: "p", solver_outcome: "optimal", has_verified_solution: true },
      base: { run_id: "r1", scenario_id: "s", has_verified_solution: false },
      comparable: false, reason: "Körningarna gäller olika tentamängder.", interpretation: "Körningarna gäller olika tentamängder.",
      uncertainty_ore: null, interpretable: null, metrics: { cost_ore: { old: 100, new: 90, delta: null } },
    })
    assert.equal(result.base?.has_verified_solution, false)
    assert.equal(result.run.problem_id, "p")
    const row = metricRows(result)[0]
    assert.equal(row.delta, "–")
    const view = interpretationView(result)
    assert.equal(view.tone, "not_interpretable")
    assert.equal(view.text, "Körningarna gäller olika tentamängder.")
    assert.deepEqual(metricRows(toCompareResult({ run: { run_id: "r2" }, base: null, comparable: false, metrics: {} })), [])
  })

  it("listar ändrade parametrar med gammalt och nytt värde i klartext", () => {
    const [row] = changeRows(COMPARE_OK.parameter_changes)
    assert.equal(row.label, "Vaktkostnad per pass")
    assert.match(row.oldText, /^1\s250\skr per tillfälle$/)
    assert.match(row.newText, /^1\s300\skr per tillfälle$/)
    const ladder = changeRows([{ id: "staffing.ladder", label: "Trappa", group: "Bemanning", unit: null, old: [{ max_participants: 50, required_staff: 1 }], new: [{ max_participants: 60, required_staff: 1 }] }])
    assert.equal(ladder[0].oldText, "upp till 50 deltagare: 1 vakt")
    assert.equal(ladder[0].newText, "upp till 60 deltagare: 1 vakt")
    const weekdays = changeRows([{ id: "calendar.weekdays", label: "Dagar", group: "Tid", unit: null, old: [1, 2, 3, 4, 5, 6, 7], new: [1, 2, 3, 4, 5] }])
    assert.equal(weekdays[0].oldText, "Alla veckodagar")
    assert.equal(weekdays[0].newText, "mån, tis, ons, tors, fre")
  })

  it("tolkningen är huvudmeningen och markeras med ord", () => {
    const not = interpretationView(COMPARE_OK)
    assert.equal(not.tone, "not_interpretable")
    assert.match(not.title, /går inte att tolka/)
    assert.equal(not.text, COMPARE_OK.interpretation)
    assert.equal(interpretationView({ ...COMPARE_OK, interpretable: true }).tone, "interpretable")
    assert.match(interpretationView({ ...COMPARE_OK, interpretable: true }).title, /går att tolka/)
    assert.equal(interpretationView({ ...COMPARE_OK, interpretable: null }).tone, "unknown")
    const incomparable = interpretationView({ ...COMPARE_OK, comparable: false, interpretation: "", reason: "Olika urval." })
    assert.equal(incomparable.tone, "not_interpretable")
    assert.equal(incomparable.text, "Olika urval.")
  })
})

describe("ärliga texter", () => {
  it("visar intervall utan bevisat optimum", () => {
    const statement = costStatement(180_050_000, 173_900_000, false)
    assert.equal(statement.proven, false)
    assert.match(statement.headline, /1\s?739\s?000–1\s?800\s?500 kr/)
    assert.match(statement.note, /ingen besparing/)
  })
  it("kallar bara bevisat optimum optimum", () => {
    assert.equal(costStatement(100, null, false).proven, false)
    assert.equal(costStatement(100, 90, false).proven, false)
    assert.equal(costStatement(100, null, true).proven, true)
    assert.equal(costStatement(null, null, false).headline, "–")
  })
  it("saknad dom blir aldrig godkänd", () => {
    assert.equal(describeVerdict(undefined).status, null)
    assert.equal(describeVerdict(null).status, null)
    assert.equal(describeVerdict("pass").status, "pass")
    assert.deepEqual(describeVerdict({ status: "not_evaluated", reason: "x", a: 1 }).details, [["a", "1"]])
  })
  it("formaterar tal på svenska", () => {
    assert.match(formatKr(182_300_000), /^1\s?823\s?000 kr$/)
    assert.equal(formatKr(null), "–")
    assert.equal(formatDuration(124), "2 min 04 s")
    assert.equal(formatDuration(8.34), "8,3 s")
    assert.match(formatGap(0.075), /^7,5\s%$/)
  })
  it("översätter lösarens beteckningar och undviker facktermer", () => {
    assert.equal(sourceLabel("warm start"), "förra körningens placering")
    assert.equal(sourceLabel("round 2"), "varv 2 av grov plan och dagkontroll")
    assert.equal(sourceLabel("round 3 history"), "varv 3, försök att behålla ursprungliga tider")
    assert.equal(sourceLabel(null), "–")
    for (const text of [kindLabel("warm_start"), kindLabel("economic_plan"), kindLabel("history"), kindLabel("repair")]) {
      assert.doesNotMatch(text, /relaxation|varmstart|batch|CP-SAT/i)
    }
  })
})
