import assert from "node:assert/strict"
import { describe, it } from "node:test"
import { toJointScenario } from "./jointApi.ts"
import { formatBytes, formatWhen, isMissingUnderlayMessage, jobIsActive, jobProgress, scenarioNeedsUnderlay, stateIsUsable } from "./underlay.ts"
import type { PreparationJob } from "./underlayApi.ts"

const rule = (exam_count: number | null) => toJointScenario({ id: "r", name: "R", subset: { plan_area: "Uppsala", selection: "rule", exam_count, description: "Alla tentor i underlaget" } })
const list = toJointScenario({ id: "l", name: "L", subset: { plan_area: "Uppsala", selection: "event_list", exam_count: 12, description: "12 tentor" } })
const job = (status: string): PreparationJob => ({ job_id: "j", status, error: null, progress: { step: null, label: "", index: 0, total: 7 }, steps: [] })

describe("förberett underlag", () => {
  it("regelbaserat urval utan antal tentor betyder att underlaget saknas", () => {
    assert.equal(scenarioNeedsUnderlay(rule(null)), true)
    assert.equal(scenarioNeedsUnderlay(rule(1172)), false)
    assert.equal(scenarioNeedsUnderlay(list), false)
    assert.equal(scenarioNeedsUnderlay(undefined), false)
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
  it("ett pågående jobb känns igen ur serverns svar, till exempel efter omladdning", () => {
    assert.equal(jobIsActive(job("running")), true)
    assert.equal(jobIsActive(job("queued")), true)
    assert.equal(jobIsActive(job("completed")), false)
    assert.equal(jobIsActive(job("failed")), false)
    assert.equal(jobIsActive(null), false)
  })
  it("underlag som inte är aktuellt går att använda men visas med varning", () => {
    assert.equal(stateIsUsable("current"), true)
    assert.equal(stateIsUsable("stale"), true)
    assert.equal(stateIsUsable("missing"), false)
    assert.equal(stateIsUsable("unverified"), false)
  })
  it("format", () => {
    assert.equal(formatBytes(512), "512 B")
    assert.equal(formatBytes(2048), "2 kB")
    assert.equal(formatBytes(3 * 1024 * 1024), "3,0 MB")
    assert.equal(formatWhen("inte-ett-datum"), "inte-ett-datum")
    assert.match(formatWhen("2026-10-13T12:35:42+00:00"), /^2026-10-13 \d\d:35$/)
  })
})
