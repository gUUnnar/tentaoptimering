import assert from "node:assert/strict"
import { describe, it } from "node:test"
import { toJointScenario } from "./jointApi.ts"
import { isMissingUnderlayMessage, jobProgress, scenarioNeedsUnderlay, underlayStatus } from "./underlay.ts"

const rule = (exam_count: number | null) => toJointScenario({ id: "r", name: "R", subset: { plan_area: "Uppsala", selection: "rule", exam_count, description: "Hela terminen" } })
const list = toJointScenario({ id: "l", name: "L", subset: { plan_area: "Uppsala", selection: "event_list", exam_count: 12, description: "12 tentor" } })

describe("förberett underlag", () => {
  it("regelbaserat urval utan antal tentor betyder att underlaget saknas", () => {
    assert.equal(scenarioNeedsUnderlay(rule(null)), true)
    assert.equal(scenarioNeedsUnderlay(rule(1172)), false)
    assert.equal(scenarioNeedsUnderlay(list), false)
    assert.equal(scenarioNeedsUnderlay(undefined), false)
  })
  it("status ur scenariolistan", () => {
    assert.equal(underlayStatus([]), "unknown")
    assert.equal(underlayStatus([list]), "unknown")
    assert.equal(underlayStatus([list, rule(null)]), "missing")
    assert.equal(underlayStatus([list, rule(null), rule(1172)]), "present")
  })
  it("känner igen serverfel om saknat underlag men inte andra fel", () => {
    assert.equal(isMissingUnderlayMessage("FileNotFoundError: [Errno 2] No such file or directory: 'x/optimization_demands.csv'"), true)
    assert.equal(isMissingUnderlayMessage("Scenariot finns inte bland de gemensamma scenarierna."), false)
    assert.equal(isMissingUnderlayMessage("Servern avvisade värdet."), false)
    assert.equal(isMissingUnderlayMessage(null), false)
  })
  it("jobbstatus", () => {
    assert.equal(jobProgress("completed"), "completed")
    assert.equal(jobProgress("failed"), "failed")
    assert.equal(jobProgress("queued"), "running")
    assert.equal(jobProgress("running"), "running")
  })
})
