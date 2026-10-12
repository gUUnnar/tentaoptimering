import assert from "node:assert/strict"
import { describe, it } from "node:test"
import { isMockRequested } from "./jointApi.ts"
import { DEMO_RUN_ID, REJECTED_RUN_ID, buildFixtureEvents } from "./jointFixture.ts"
import { costStatement, describeVerdict, formatDuration, formatGap, formatKr } from "./jointFormat.ts"
import { mockJointApi } from "./jointMock.ts"
import {
  activeBatch, costSeries, currentBoundOre, currentCostOre, dayCounts, dayGrid, firstIncumbent, foldEvents, gapFraction, mergeEvents, stepViews,
} from "./jointState.ts"

const EVENT_TYPES = new Set(["phase", "batch", "day", "incumbent", "bound", "warm_start", "resources", "finished"])
const accepted = buildFixtureEvents("accepted")

describe("fixturen följer API-kontraktet", () => {
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
})

describe("jointState", () => {
  it("slutar med ett bevisat gap utan bevisat optimum", () => {
    const state = foldEvents(accepted)
    assert.equal(currentCostOre(state), 180_050_000)
    assert.equal(currentBoundOre(state), 173_900_000)
    const gap = gapFraction(currentCostOre(state), currentBoundOre(state))!
    assert.ok(gap > 0.03 && gap < 0.04)
    assert.equal(state.finished?.cancelled, false)
  })

  it("markerar första verifierade lösning med källa", () => {
    const first = firstIncumbent(foldEvents(accepted))
    assert.equal(first?.source, "varmstart (omkontrollerad)")
    assert.equal(first?.changed_exams, 0)
    assert.equal(firstIncumbent(foldEvents(buildFixtureEvents("rejected")))?.source, "relaxation, varv 1 (reparerad)")
  })

  it("visar inte en obekräftad placering som lösning före första incumbent", () => {
    const early = foldEvents(accepted.filter(event => event.t < 10))
    assert.equal(currentCostOre(early), null)
    assert.equal(firstIncumbent(early), null)
  })

  it("beräknar fassteg och hoppar över varmstart när ingen används", () => {
    const none = stepViews(foldEvents(buildFixtureEvents("none")), 1000)
    assert.equal(none[0].state, "skipped")
    assert.deepEqual(none.slice(1).map(step => step.state), ["done", "done", "done", "done"])
    const all = stepViews(foldEvents(accepted), 1000)
    assert.ok(all.every(step => step.state === "done"))
    assert.ok(all[1].seconds > 50 && all[1].seconds < 60)
  })

  it("räknar förbrukad tid för pågående fas med nowT", () => {
    const mid = foldEvents(accepted.filter(event => event.t <= 40))
    const steps = stepViews(mid, 40)
    assert.equal(steps[0].state, "done")
    assert.equal(steps[1].state, "active")
    assert.ok(steps[1].seconds > 10 && steps[1].seconds < 20)
    assert.equal(steps[2].state, "pending")
  })

  it("dagrutnät: väntande dagar, pågående uppskattas högst lika många som parallellt", () => {
    const mid = foldEvents(accepted.filter(event => event.t <= 85))
    const grid = dayGrid(mid, "economic_plan")
    assert.equal(grid.length, 73)
    const counts = dayCounts(grid)
    assert.ok(counts.running > 0 && counts.running <= 8)
    assert.equal(Object.values(counts).reduce((a, b) => a + b, 0), 73)
    assert.equal(activeBatch(mid)?.kind, "economic_plan")
    const done = foldEvents(accepted)
    assert.equal(dayCounts(dayGrid(done, "economic_plan")).pending, 0)
    assert.equal(dayCounts(dayGrid(done, "economic_plan")).unknown, 1)
    assert.equal(activeBatch(done), null)
  })

  it("mergeEvents ignorerar redan mottagna händelser", () => {
    const first = accepted.slice(0, 10)
    const merged = mergeEvents(first, accepted.slice(5, 15))
    assert.equal(merged.length, 15)
    assert.equal(mergeEvents(merged, accepted.slice(0, 15)), merged)
  })

  it("kostnadsserien är stegvis och slutar vid aktuell tid", () => {
    const series = costSeries(foldEvents(accepted), 500)
    assert.equal(series.at(-1)?.t, 500)
    assert.ok(series.some(point => point.upper === undefined) && series.some(point => point.lower !== undefined))
  })
})

describe("ärliga texter", () => {
  it("visar intervall utan bevisat optimum", () => {
    const statement = costStatement(180_050_000, 173_900_000, "feasible_not_proven")
    assert.equal(statement.proven, false)
    assert.match(statement.headline, /1\s?739\s?000–1\s?800\s?500 kr/)
    assert.match(statement.note, /inte en besparing/)
  })
  it("kallar bara bevisat optimum optimum", () => {
    assert.equal(costStatement(100, null, "feasible_not_proven").proven, false)
    assert.equal(costStatement(100, 90, "unknown").proven, false)
    assert.equal(costStatement(100, null, "optimal").proven, true)
    assert.equal(costStatement(null, null, null).headline, "–")
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
  it("mockläge via adressen", () => {
    assert.equal(isMockRequested("?mock=1"), true)
    assert.equal(isMockRequested("?x=1&mock=true"), true)
    assert.equal(isMockRequested(""), false)
    assert.equal(isMockRequested("?mock=0"), false)
  })
})

describe("mockad datakälla", () => {
  it("spelar upp avslutade körningar", async () => {
    const events = await mockJointApi.runEvents(DEMO_RUN_ID)
    assert.equal(events.length, accepted.length)
    const summary = await mockJointApi.summary(DEMO_RUN_ID)
    assert.equal(summary.cost_ore, 180_050_000)
    const describedBusiness = describeVerdict(summary.business_verification)
    assert.equal(describedBusiness.status, "not_evaluated")
    assert.equal((await mockJointApi.warmStart(DEMO_RUN_ID))?.decision, "accepted")
    assert.equal((await mockJointApi.warmStart(REJECTED_RUN_ID))?.decision, "rejected")
    assert.equal(await mockJointApi.warmStart("saknas"), null)
    await assert.rejects(() => mockJointApi.runEvents("saknas"))
  })

  it("kandidater filtreras på problem-id", async () => {
    assert.equal((await mockJointApi.listCandidates("term-vt-2027")).length, 3)
    assert.equal((await mockJointApi.listCandidates("annat")).length, 0)
  })

  it("jobb: delhämtning med after och stopp utan lösning ger ingen körning", async () => {
    const { job_id } = await mockJointApi.startRun({ scenario: "term-vt-2027", warm_start: "auto", threads: 0, memory_mb: null, parallel_day_checks: true })
    const first = await mockJointApi.events(job_id, 0)
    assert.equal(first.status, "running")
    const again = await mockJointApi.events(job_id, first.last_seq)
    assert.ok(again.events.every(event => event.seq > first.last_seq))
    await mockJointApi.cancel(job_id)
    const waiting = await mockJointApi.events(job_id, 0)
    assert.equal(waiting.status, "running", "stoppet tar tid: bästa lösningen sparas först")
    await new Promise(resolve => setTimeout(resolve, 1600))
    const done = await mockJointApi.events(job_id, 0)
    assert.equal(done.status, "cancelled")
    const last = done.events.at(-1)
    assert.equal(last?.type, "finished")
    assert.equal(last?.type === "finished" && last.cancelled, true)
    assert.equal(done.run_id, null)
  })
})
