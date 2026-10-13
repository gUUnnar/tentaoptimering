import assert from "node:assert/strict"
import { describe, it } from "node:test"
import { DEMO_RUN_ID, buildFixtureEvents, fixtureSummary } from "./testing/jointFixture.ts"
import {
  activeBatch, applyEvent, costSeries, currentBoundOre, currentCostOre, dayCounts, dayGrid, emptyJointState, firstIncumbent, foldEvents,
  gapFraction, hasRealStarts, mergeEvents,
} from "./jointState.ts"
import type { JointEvent } from "./jointTypes.ts"

const EVENT_TYPES = new Set(["phase", "batch", "day", "day_started", "incumbent", "bound", "warm_start", "resources", "finished"])
const accepted = buildFixtureEvents("accepted")

describe("testdata följer API-kontraktet", () => {
  for (const warm of ["accepted", "rejected", "none"] as const) {
    it(`händelserna är välformade (${warm})`, () => {
      const events = buildFixtureEvents(warm)
      events.forEach((event, i) => {
        assert.equal(event.seq, i + 1)
        assert.ok(EVENT_TYPES.has(event.type), event.type)
        if (i > 0) assert.ok(event.t >= events[i - 1].t, "t ska vara icke-avtagande")
        if (event.type === "day") assert.ok(["optimal", "feasible", "infeasible", "unknown"].includes(event.status))
        if (event.type === "batch") assert.ok(event.done <= event.total)
      })
      assert.equal(events.at(-1)?.type, "finished")
    })
  }
  it("sammanfattningen har samma form som adaptern ger", () => {
    const summary = fixtureSummary(accepted, "accepted")
    assert.equal(summary.run_id, DEMO_RUN_ID)
    assert.equal(summary.cost_ore, 180_050_000)
    assert.equal(summary.business_verification, "not_evaluated")
  })
})

describe("reducerare: kostnad och faser", () => {
  it("slutar med ett bevisat gap utan bevisat optimum", () => {
    const state = foldEvents(accepted)
    assert.equal(currentCostOre(state), 180_050_000)
    assert.equal(currentBoundOre(state), 173_900_000)
    const gap = gapFraction(currentCostOre(state), currentBoundOre(state))!
    assert.ok(gap > 0.03 && gap < 0.04)
    assert.equal(state.finished?.cancelled, false)
  })

  it("markerar första verifierade lösning med källa", () => {
    assert.equal(firstIncumbent(foldEvents(accepted))?.source, "warm start")
    assert.equal(firstIncumbent(foldEvents(accepted))?.changed_exams, 0)
    assert.equal(firstIncumbent(foldEvents(buildFixtureEvents("rejected")))?.source, "round 1")
  })

  it("visar inte en obekräftad placering som lösning före första incumbent", () => {
    const early = foldEvents(accepted.filter(event => event.t < 10))
    assert.equal(currentCostOre(early), null)
    assert.equal(firstIncumbent(early), null)
  })

  it("mergeEvents ignorerar redan mottagna händelser", () => {
    const merged = mergeEvents(accepted.slice(0, 10), accepted.slice(5, 15))
    assert.equal(merged.length, 15)
    assert.equal(mergeEvents(merged, accepted.slice(0, 15)), merged)
  })

  it("kostnadsserien är stegvis och slutar vid aktuell tid", () => {
    const series = costSeries(foldEvents(accepted), 500)
    assert.equal(series.at(-1)?.t, 500)
    assert.ok(series.some(point => point.upper === undefined) && series.some(point => point.lower !== undefined))
  })
})

describe("reducerare: händelsen day_started och dagrutnätet", () => {
  const during = foldEvents(accepted.filter(event => event.t <= 85))

  it("pågående dagar kommer från day_started och har datum", () => {
    assert.equal(hasRealStarts(during, "economic_plan"), true)
    const grid = dayGrid(during, "economic_plan")
    assert.equal(grid.length, 73)
    const running = grid.filter(cell => cell.kind === "running")
    assert.ok(running.length > 0 && running.length <= 8)
    assert.ok(running.every(cell => cell.kind === "running" && /^\d{4}-\d{2}-\d{2}$/.test(cell.date)))
    assert.equal(grid.filter(cell => cell.kind === "pending" && cell.running).length, 0, "ingen uppskattning när händelsen finns")
    const counts = dayCounts(grid)
    assert.equal(counts.running, running.length)
    assert.equal(Object.values(counts).reduce((a, b) => a + b, 0), 73)
    assert.equal(activeBatch(during)?.kind, "economic_plan")
  })

  it("en färdig dag slutar vara pågående och en slutförd körning har inga pågående rutor", () => {
    const start: JointEvent = { seq: 1, t: 1, type: "day_started", date: "2027-01-11", kind: "k" }
    const batch: JointEvent = { seq: 2, t: 1, type: "batch", kind: "k", total: 2, done: 0, parallel: 1, workers_per_check: 1, statuses: {} }
    const started = foldEvents([start, batch])
    assert.deepEqual(dayGrid(started, "k").map(cell => cell.kind), ["running", "pending"])
    const done = applyEvent(started, { seq: 3, t: 5, type: "day", date: "2027-01-11", kind: "k", status: "optimal", seconds: 4 })
    assert.deepEqual(dayGrid(done, "k").map(cell => cell.kind), ["known", "pending"])
    const ended = applyEvent(started, { seq: 4, t: 9, type: "finished", outcome: "failed", cost_ore: null, bound_ore: null, cancelled: false, error: "fel" })
    assert.equal(dayCounts(dayGrid(ended, "k")).running, 0)
  })

  it("utan day_started uppskattas pågående och högst så många som får köras samtidigt", () => {
    const old = foldEvents(accepted.filter(event => event.type !== "day_started" && event.t <= 85))
    assert.equal(hasRealStarts(old, "economic_plan"), false)
    const counts = dayCounts(dayGrid(old, "economic_plan"))
    assert.ok(counts.running > 0 && counts.running <= 8)
  })

  it("en upprepad kontroll (ny start efter färdig dag) visas som pågående igen", () => {
    const batch: JointEvent = { seq: 1, t: 1, type: "batch", kind: "k", total: 1, done: 0, parallel: 1, workers_per_check: 1, statuses: {} }
    let state = foldEvents([batch,
      { seq: 2, t: 1, type: "day_started", date: "2027-01-11", kind: "k" },
      { seq: 3, t: 5, type: "day", date: "2027-01-11", kind: "k", status: "unknown", seconds: 4 }])
    assert.deepEqual(dayGrid(state, "k").map(cell => cell.kind), ["known"])
    state = applyEvent(state, { seq: 4, t: 6, type: "day_started", date: "2027-01-11", kind: "k", block: ["2027-01-11", "2027-01-12"] })
    assert.deepEqual(dayGrid(state, "k").map(cell => cell.kind), ["running"])
    state = applyEvent(state, { seq: 5, t: 9, type: "day", date: "2027-01-11", kind: "k", status: "feasible", seconds: 3 })
    const grid = dayGrid(state, "k")
    assert.deepEqual(grid.map(cell => cell.kind), ["known"])
    assert.equal(grid[0].kind === "known" && grid[0].cell.status, "feasible")
  })

  it("bevarar block för kontroller som gällde flera dagar", () => {
    const state = foldEvents(accepted)
    const repair = state.days.repair
    assert.deepEqual(repair.find(cell => cell.block)?.block?.length, 2)
  })

  it("färdig körning har inga väntande dagar och en dag med tidsgräns", () => {
    const done = foldEvents(accepted)
    const counts = dayCounts(dayGrid(done, "economic_plan"))
    assert.equal(counts.pending, 0)
    assert.equal(counts.unknown, 1)
    assert.equal(activeBatch(done), null)
    assert.deepEqual(emptyJointState().started, {})
  })
})
