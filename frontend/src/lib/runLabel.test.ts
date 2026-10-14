import assert from "node:assert/strict"
import { describe, it } from "node:test"
import { toJointScenario } from "./jointApi.ts"
import { runLabel, runStart, scenarioName, startText } from "./runLabel.ts"

const scenarios = [toJointScenario({ id: "joint_underlay_period", name: "Alla tentor i underlaget (12 jan–31 mars 2026)", problem_id: "joint_underlay_period_2026", subset: { plan_area: "Uppsala", selection: "rule", exam_count: 1, description: "x" } })]
const run = { run_id: "20261013T141233Z-joint_underlay_period_2026", scenario_id: "joint_underlay_period_2026", created_at: "2026-10-13T14:12:33Z" }

describe("körningens namn", () => {
  it("scenariots namn slås upp via problem-id, annars visas id:t", () => {
    assert.equal(scenarioName(scenarios, "joint_underlay_period_2026"), "Alla tentor i underlaget (12 jan–31 mars 2026)")
    assert.equal(scenarioName(scenarios, "okänt_scenario"), "okänt_scenario")
  })
  it("starttiden läses ur created_at, annars ur körnings-id:t", () => {
    assert.equal(runStart(run.run_id, run.created_at)?.toISOString(), "2026-10-13T14:12:33.000Z")
    assert.equal(runStart(run.run_id)?.toISOString(), "2026-10-13T14:12:33.000Z")
    assert.equal(runStart("utan-tid"), null)
  })
  it("klockslag för i dag och datum för andra dagar", () => {
    const start = new Date(2026, 9, 13, 14, 12)
    assert.equal(startText(start, new Date(2026, 9, 13, 18, 0)), "14:12")
    assert.equal(startText(start, new Date(2026, 9, 14, 8, 0)), "13 okt 14:12")
  })
  it("namnet är scenario och klockslag, aldrig det tekniska id:t", () => {
    const text = runLabel(run, scenarios, new Date(2026, 9, 30))
    assert.match(text, /^Alla tentor i underlaget \(12 jan–31 mars 2026\), 13 okt \d\d:\d\d$/)
    assert.equal(text.includes("20261013"), false)
    assert.equal(runLabel({ run_id: "utan-tid", scenario_id: "x" }, []), "x")
  })
})
