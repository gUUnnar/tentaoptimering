import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { describe, it } from "node:test"
import { buildTimeline, layoutShares, MIN_SHARE, type Timeline } from "./jointTimeline.ts"
import { previousRoundFailed, segmentDetail, countsText } from "./jointTimelineDetail.ts"
import { timelineSummary } from "./jointTimelineSummary.ts"
import { buildFixtureEvents } from "./testing/jointFixture.ts"
import type { DayStatus, JointEvent } from "./jointTypes.ts"

// ---- Hjälpmedel för att bygga händelseföljder -----------------------------------------------------------------------

type Draft = Record<string, unknown> & { type: string; t: number }
const numbered = (drafts: Draft[]): JointEvent[] => drafts.map((draft, index) => ({ ...draft, seq: index + 1 }) as unknown as JointEvent)
const phase = (name: string, t: number, state: "started" | "finished"): Draft => ({ type: "phase", name, state, t })
/** En omgång dagkontroller: batch-händelser, en dag-händelse per datum och en slutlig batch. */
function checks(kind: string, t: number, outcomes: Record<string, DayStatus>): Draft[] {
  const dates = Object.keys(outcomes)
  const out: Draft[] = [{ type: "batch", kind, total: dates.length, done: 0, parallel: 1, workers_per_check: 1, statuses: {}, t }]
  dates.forEach((date, i) => {
    out.push({ type: "day", date, kind, status: outcomes[date], seconds: 1, t: t + i + 1 })
    out.push({ type: "batch", kind, total: dates.length, done: i + 1, parallel: 1, workers_per_check: 1, statuses: {}, t: t + i + 1 })
  })
  return out
}
const finished = (t: number, extra: Record<string, unknown> = {}): Draft => ({ type: "finished", outcome: "feasible_not_proven", cost_ore: 1, bound_ore: 1, cancelled: false, t, ...extra })

const OK: DayStatus = "optimal"
const FAIL: DayStatus = "infeasible"

/** Tre varv: varv 1 och 2 har dagar som inte gick, varv 3 går igenom. Ingen kontroll av förra körningen. */
function threeRounds(): JointEvent[] {
  return numbered([
    { type: "warm_start", decision: "not_used", explanation: "Ingen tidigare körning kunde användas.", source_run_id: null, t: 0 },
    phase("relaxation", 0, "started"), { type: "bound", lower_ore: 100, round: 1, t: 10 }, phase("relaxation", 10, "finished"),
    phase("day_checks", 10, "started"), ...checks("day", 10, { "2026-01-12": FAIL, "2026-01-13": FAIL, "2026-01-14": OK, "2026-01-15": FAIL, "2026-01-16": FAIL }), phase("day_checks", 20, "finished"),
    phase("repair", 20, "started"), ...checks("diagnosis", 20, { "2026-01-12": FAIL, "2026-01-13": OK }), phase("repair", 25, "finished"),
    phase("relaxation", 25, "started"), { type: "bound", lower_ore: 120, round: 2, t: 33 }, phase("relaxation", 33, "finished"),
    phase("day_checks", 33, "started"), ...checks("day", 33, { "2026-01-12": FAIL, "2026-01-13": OK, "2026-01-17": FAIL }), phase("day_checks", 38, "finished"),
    phase("relaxation", 38, "started"), { type: "bound", lower_ore: 130, round: 3, t: 44 }, phase("relaxation", 44, "finished"),
    phase("day_checks", 44, "started"), ...checks("day", 44, { "2026-01-12": OK, "2026-01-13": OK }), phase("day_checks", 47, "finished"),
    phase("history", 47, "started"), ...checks("history", 47, { "2026-01-12": OK }), phase("history", 50, "finished"),
    phase("finalize", 50, "started"), phase("finalize", 52, "finished"), finished(52),
  ])
}

const steps = (timeline: Timeline, block: number) => timeline.blocks[block].segments.map(segment => segment.step)

describe("tidslinje: varv och segment i körordning", () => {
  const timeline = buildTimeline(threeRounds(), 60)

  it("ett block per varv, med kontroll av förra körningen först och slutkontroll sist", () => {
    assert.deepEqual(timeline.blocks.map(block => block.label), ["Kontroll av förra körningen", "Varv 1", "Varv 2", "Varv 3", "Slutkontroll och sparande"])
    assert.equal(timeline.rounds, 3)
    assert.deepEqual(steps(timeline, 1), ["relaxation", "day_checks", "repair"])
    assert.deepEqual(steps(timeline, 2), ["relaxation", "day_checks"])
    assert.deepEqual(steps(timeline, 3), ["relaxation", "day_checks", "history"])
    assert.deepEqual(steps(timeline, 4), ["finalize"])
  })

  it("tid och status per segment", () => {
    const [relaxation, dayChecks, repair] = timeline.blocks[1].segments
    assert.deepEqual([relaxation.startedAt, relaxation.endedAt, relaxation.seconds], [0, 10, 10])
    assert.equal(dayChecks.seconds, 10)
    assert.equal(repair.seconds, 5)
    assert.ok(timeline.blocks.every(block => block.segments.every(segment => segment.status === "done")))
    assert.ok(timeline.blocks.slice(1).every(block => block.status === "done"))
    assert.equal(timeline.running, false)
    assert.equal(timeline.ended, "completed")
  })

  it("bredden är proportionell mot tiden med en lägsta synlig bredd och summerar till ett", () => {
    const all = timeline.blocks.flatMap(block => block.segments)
    const total = all.reduce((sum, segment) => sum + segment.share, 0) + timeline.blocks.filter(block => !block.segments.length).reduce((sum, block) => sum + block.share, 0)
    assert.ok(Math.abs(total - 1) < 1e-9, `summan ${total}`)
    assert.ok(all.every(segment => segment.share >= MIN_SHARE - 1e-9))
    const [relaxation1, dayChecks1, repair1] = timeline.blocks[1].segments
    assert.ok(relaxation1.share > repair1.share, "10 s ska vara bredare än 5 s")
    assert.ok(Math.abs(relaxation1.share - dayChecks1.share) < 1e-9, "lika lång tid, lika bred")
    assert.ok(Math.abs(timeline.blocks[1].share - (relaxation1.share + dayChecks1.share + repair1.share)) < 1e-9)
  })

  it("kontroller per segment: dagar klara av totalt och hur många som misslyckades", () => {
    const dayChecks = timeline.blocks[1].segments[1]
    assert.deepEqual(dayChecks.checks, [{ kind: "day", total: 5, done: 5, failed: 4, infeasible: 4, timedOut: 0 }])
    assert.deepEqual(dayChecks.failedDates, ["2026-01-12", "2026-01-13", "2026-01-15", "2026-01-16"])
    assert.equal(countsText(dayChecks.checks[0]), "5 av 5 dagar klara, 4 misslyckades")
    assert.equal(timeline.blocks[3].segments[1].failedDates.length, 0)
    assert.equal(countsText(timeline.blocks[3].segments[1].checks[0]), "2 av 2 dagar klara, ingen misslyckades")
  })

  it("undre gräns per varv hör till den grova planen", () => {
    assert.deepEqual([1, 2, 3].map(round => timeline.blocks[round].segments[0].boundOre), [100, 120, 130])
    assert.equal(timeline.blocks[1].segments[1].boundOre, null)
  })

  it("sammanfattning i klartext, härledd ur händelserna", () => {
    assert.deepEqual(timeline.failedDays, ["2026-01-12", "2026-01-13", "2026-01-15", "2026-01-16", "2026-01-17"])
    assert.equal(timeline.summary, "3 varv: den grova planen ändrades 2 gånger eftersom 5 dagar inte gick att genomföra.")
  })

  it("kontrollen av förra körningen hoppas över med skäl när ingen användes", () => {
    const warm = timeline.blocks[0]
    assert.equal(warm.status, "skipped")
    assert.equal(warm.segments.length, 0)
    assert.equal(warm.note, "Ingen tidigare körning kunde användas.")
    assert.ok(warm.share >= MIN_SHARE - 1e-9)
  })
})

describe("tidslinje: pågående, avbruten och misslyckad körning", () => {
  const all = threeRounds()
  const upTo = (t: number) => all.filter(event => event.t <= t && event.type !== "finished")

  it("ett pågående segment sträcker sig till nu, har status running och körningen ses som pågående", () => {
    const timeline = buildTimeline(upTo(40), 41.5)
    const running = timeline.blocks.flatMap(block => block.segments).filter(segment => segment.status === "running")
    assert.equal(running.length, 1)
    assert.equal(running[0].step, "relaxation")
    assert.equal(running[0].round, 3)
    assert.equal(running[0].endedAt, 41.5)
    assert.equal(running[0].seconds, 3.5)
    assert.equal(timeline.blocks[3].status, "running")
    assert.equal(timeline.running, true)
    assert.equal(timeline.ended, null)
    assert.equal(timeline.blocks.at(-1)?.status, "pending", "slutkontrollen väntar")
    assert.equal(timeline.summary, "Hittills 3 varv: den grova planen ändrades 2 gånger eftersom 5 dagar inte gick att genomföra.")
  })

  it("tid som inte hunnit ikapp startpunkten ger noll sekunder, aldrig negativ bredd", () => {
    const timeline = buildTimeline(upTo(40), 10)
    assert.ok(timeline.blocks.flatMap(block => block.segments).every(segment => segment.seconds >= 0 && segment.share > 0))
  })

  it("ingen händelse än: inga varv, väntande block och tom sammanfattning", () => {
    const timeline = buildTimeline([], 3)
    assert.equal(timeline.rounds, 0)
    assert.equal(timeline.summary, "")
    assert.deepEqual(timeline.blocks.map(block => block.status), ["pending", "pending"])
    assert.equal(timeline.running, false)
  })

  it("avbruten körning: öppet segment markeras som avbrutet och slutkontrollen som överhoppad", () => {
    const events = numbered([...upTo(40).map(event => ({ ...event })) as unknown as Draft[], finished(41, { outcome: "cancelled", cancelled: true })])
    const timeline = buildTimeline(events, 90)
    const last = timeline.blocks[3].segments[0]
    assert.equal(last.status, "stopped")
    assert.equal(last.endedAt, 41, "slutar vid körningens slut, inte vid nu")
    assert.equal(timeline.blocks[3].status, "stopped")
    assert.equal(timeline.ended, "cancelled")
    assert.equal(timeline.running, false)
    assert.equal(timeline.blocks.at(-1)?.status, "skipped")
    assert.equal(timeline.blocks.at(-1)?.note, "Körningen stoppades innan slutkontrollen.")
    assert.match(timeline.summary, /Körningen stoppades\.$/)
    assert.doesNotMatch(timeline.summary, /Hittills/)
  })

  it("misslyckad körning", () => {
    const events = numbered([...upTo(15).map(event => ({ ...event })) as unknown as Draft[], finished(16, { outcome: "failed", cost_ore: null, bound_ore: null, error: "fel" })])
    const timeline = buildTimeline(events, 20)
    assert.equal(timeline.ended, "failed")
    assert.equal(timeline.blocks[1].segments.at(-1)?.status, "stopped")
    assert.equal(timeline.blocks.at(-1)?.note, "Körningen misslyckades innan slutkontrollen.")
    assert.match(timeline.summary, /Körningen misslyckades\.$/)
  })

  it("segment som aldrig stängts i en avslutad körning räknas som klara och slutar vid körningens slut", () => {
    const raw = JSON.parse(readFileSync(new URL("./testing/contract/events_completed.json", import.meta.url), "utf8"))
    const end = raw.events.at(-1).t
    const timeline = buildTimeline(raw.events, end + 5)
    const relaxation = timeline.blocks[1].segments[0]
    assert.equal(relaxation.status, "done")
    assert.equal(relaxation.endedAt, end)
    assert.equal(timeline.blocks.at(-1)?.status, "skipped")
    assert.equal(timeline.blocks.at(-1)?.note, "Ingen slutkontroll registrerades.")
    assert.equal(timeline.summary, "1 varv.", "ingen dagkontroll-fas rapporterades, så inget påstås om dagarna")
  })

  it("händelser i fel ordning sorteras efter sekvensnummer", () => {
    const shuffled = [...threeRounds()].reverse()
    assert.equal(buildTimeline(shuffled, 60).summary, buildTimeline(threeRounds(), 60).summary)
  })
})

describe("tidslinje: körningar med och utan varmstart", () => {
  it("körning med varmstart: kontrollen av förra körningen är ett eget block med tid och utfall", () => {
    const timeline = buildTimeline(buildFixtureEvents("accepted"), 1000)
    const warm = timeline.blocks[0]
    assert.equal(warm.status, "done")
    assert.deepEqual(steps(timeline, 0), ["warm_start_check"])
    assert.ok(warm.seconds > 20 && warm.seconds < 30)
    assert.match(warm.note ?? "", /^Användes\. /)
    assert.deepEqual(timeline.blocks.map(block => block.label), ["Kontroll av förra körningen", "Varv 1", "Slutkontroll och sparande"])
    assert.deepEqual(steps(timeline, 1), ["relaxation", "day_checks", "repair", "history"])
    assert.equal(timeline.blocks[0].segments[0].checks[0].kind, "warm_start")
    assert.equal(timeline.blocks[0].segments[0].checks[0].total, 73)
  })

  it("avvisad varmstart: dagar som inte gick syns i segmentet och utfallet säger att den inte användes", () => {
    const timeline = buildTimeline(buildFixtureEvents("rejected"), 1000)
    const segment = timeline.blocks[0].segments[0]
    assert.equal(segment.failedDates.length, 5)
    assert.match(timeline.blocks[0].note ?? "", /^Användes inte\. /)
  })

  it("körning utan varmstart: blocket hoppas över med skälet från körningen", () => {
    const timeline = buildTimeline(buildFixtureEvents("none"), 1000)
    assert.equal(timeline.blocks[0].status, "skipped")
    assert.equal(timeline.blocks[0].note, "Ingen varmstart begärdes.")
    assert.equal(timeline.blocks[0].segments.length, 0)
  })

  it("rättningens olika kontrolltyper redovisas var för sig", () => {
    const timeline = buildTimeline(threeRounds(), 60)
    const repair = timeline.blocks[1].segments[2]
    assert.deepEqual(repair.checks.map(check => [check.kind, check.done, check.failed]), [["diagnosis", 2, 1]])
  })
})

describe("tidslinje: detaljer och sammanfattning", () => {
  const timeline = buildTimeline(threeRounds(), 60)

  it("detaljerna för ett segment: tid, klara dagar, misslyckade och vad det ledde till", () => {
    const block = timeline.blocks[1]
    const detail = segmentDetail(block.segments[1], block, null)
    assert.equal(detail.heading, "Varv 1: Kontroll av varje dag")
    assert.equal(detail.statusText, "Klar")
    assert.match(detail.timeText, /^10 s \(från 10 s till 20 s/)
    assert.equal(detail.checks[0].title, "Kontroll av varje dag")
    assert.equal(detail.checks[0].counts, "5 av 5 dagar klara, 4 misslyckades")
    assert.equal(detail.checks[0].consequence, "Dagen går inte att genomföra med den grova planens lokaler och bemanning. Den utreds och rättas i stegen efter.")
  })

  it("diagnosen får sin egen text, inte dagkontrollens", () => {
    const block = timeline.blocks[1]
    const detail = segmentDetail(block.segments[2], block, null)
    assert.match(detail.checks[0].consequence ?? "", /ens utan bemanningsgräns/)
    assert.match(detail.checks[0].consequence ?? "", /ändras därför i nästa varv/)
  })

  it("inget misslyckades ger ingen följdtext", () => {
    const block = timeline.blocks[3]
    assert.equal(segmentDetail(block.segments[1], block, null).checks[0].consequence, null)
  })

  it("grov plan i varv 2 nämner förra varvets misslyckade dagar och den bevisade gränsen", () => {
    const block = timeline.blocks[2]
    assert.equal(previousRoundFailed(timeline, 2), 4)
    assert.equal(previousRoundFailed(timeline, 1), null)
    const notes = segmentDetail(block.segments[0], block, previousRoundFailed(timeline, 2)).notes
    assert.ok(notes.some(note => /Förra varvet hade 4 dagar/.test(note)))
    assert.ok(notes.some(note => /Undre gräns/.test(note)))
  })

  it("sammanfattningen skriver inget som inte är känt", () => {
    assert.equal(timelineSummary({ rounds: 0, failedBeforeLast: 0, failedDays: 0, dayChecked: false, ended: null, running: false }), "")
    assert.equal(timelineSummary({ rounds: 1, failedBeforeLast: 0, failedDays: 0, dayChecked: false, ended: "completed", running: false }), "1 varv.")
    assert.equal(timelineSummary({ rounds: 2, failedBeforeLast: 0, failedDays: 0, dayChecked: true, ended: "completed", running: false }), "2 varv: den grova planen ändrades 1 gång.")
    assert.equal(timelineSummary({ rounds: 4, failedBeforeLast: 6, failedDays: 6, dayChecked: true, ended: "completed", running: false }), "4 varv: den grova planen ändrades 3 gånger eftersom 6 dagar inte gick att genomföra.")
    assert.equal(timelineSummary({ rounds: 2, failedBeforeLast: 1, failedDays: 1, dayChecked: true, ended: null, running: true }), "Hittills 2 varv: den grova planen ändrades 1 gång eftersom 1 dag inte gick att genomföra.")
    assert.equal(timelineSummary({ rounds: 1, failedBeforeLast: 0, failedDays: 2, dayChecked: true, ended: "completed", running: false }), "1 varv: 2 dagar gick inte att genomföra med den grova planen.")
  })
})

describe("tidslinje: bredder", () => {
  it("proportionella mot tiden när alla är över lägsta bredd", () => {
    const shares = layoutShares([10, 20, 70], 0.04)
    assert.deepEqual(shares.map(value => Math.round(value * 100)), [10, 20, 70])
  })
  it("små delar lyfts till lägsta bredd och de stora ger efter", () => {
    const shares = layoutShares([0.1, 50, 50, 0], 0.05)
    assert.ok(Math.abs(shares.reduce((a, b) => a + b, 0) - 1) < 1e-9)
    assert.ok(shares[0] >= 0.05 - 1e-9 && shares[3] >= 0.05 - 1e-9)
    assert.ok(Math.abs(shares[1] - shares[2]) < 1e-9)
    assert.ok(shares[1] < 0.475)
  })
  it("ingen tid alls eller för många delar ger lika bredd", () => {
    assert.deepEqual(layoutShares([0, 0, 0, 0]), [0.25, 0.25, 0.25, 0.25])
    assert.deepEqual(layoutShares(Array.from({ length: 40 }, () => 1)).map(value => Math.round(value * 1000)), Array.from({ length: 40 }, () => 25))
    assert.deepEqual(layoutShares([]), [])
  })
})
