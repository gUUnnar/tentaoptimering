import assert from "node:assert/strict"
import { describe, it } from "node:test"
import type { PeriodCheck, PeriodCoverage } from "./jointTypes.ts"
import { addDays, checkText, coverageText, isIsoDate, periodInputError, periodPresets } from "./period.ts"
import { DEFAULT_RUN_OPTIONS, toStartBody } from "./runOptions.ts"

const BASIS = { mode: "exploratory", fixed_bookings_considered: false, label: "Explorativ planering", note: "n", cost_note: "c" }
const COVERAGE: PeriodCoverage = {
  data_available: true, planning_basis: BASIS, bookings: null,
  demand: { first: "2026-01-12", last: "2026-03-31", source: "Ladok", ready_events: 10, not_ready_events: 1 },
  days: [{ date: "2026-01-12", ready: 2, not_ready: 0 }, { date: "2026-03-30", ready: 5, not_ready: 1 }],
}

describe("planeringsperiod", () => {
  it("känner igen riktiga datum och räknar dagar över månadsskifte", () => {
    assert.equal(isIsoDate("2026-02-28"), true)
    assert.equal(isIsoDate("2026-02-30"), false)
    assert.equal(isIsoDate("2026-2-3"), false)
    assert.equal(addDays("2026-02-27", 3), "2026-03-02")
  })
  it("fel i valet före anrop", () => {
    assert.match(periodInputError({ from: "", to: "2026-01-02" }) ?? "", /båda datumen/)
    assert.match(periodInputError({ from: "2026-01-05", to: "2026-01-02" }) ?? "", /inte vara senare/)
    assert.equal(periodInputError({ from: "2026-01-02", to: "2026-01-02" }), null)
  })
  it("genvägarna utgår från underlaget och stannar inom täckningen", () => {
    const presets = Object.fromEntries(periodPresets(COVERAGE).map(item => [item.id, item.choice]))
    assert.deepEqual(presets.day, { from: "2026-03-30", to: "2026-03-30" })
    assert.deepEqual(presets.week, { from: "2026-03-30", to: "2026-03-31" })
    assert.deepEqual(presets.month, { from: "2026-01-12", to: "2026-02-08" })
    assert.deepEqual(presets.all, { from: "2026-01-12", to: "2026-03-31" })
    assert.deepEqual(periodPresets(null), [])
    assert.deepEqual(periodPresets({ ...COVERAGE, demand: null }), [])
  })
  it("texter om kontrollen: antal, utan deltagarantal och felet", () => {
    const check: PeriodCheck = { date_from: "a", date_to: "b", ready_events: 1, not_ready_events: 2, planned_from: "a", planned_to: "b", warnings: [], error: null, can_plan: true }
    assert.equal(checkText(check), "1 tenta kan planeras, 2 utan deltagarantal (ingår inte).")
    assert.equal(checkText({ ...check, error: "Utanför underlaget.", can_plan: false }), "Utanför underlaget.")
    assert.match(coverageText(COVERAGE), /2026-01-12–2026-03-31/)
    assert.match(coverageText({ ...COVERAGE, demand: null }), /inget förberett/)
  })
  it("perioden skickas med i startkroppen bara när den är vald", () => {
    assert.equal("period" in toStartBody("s", DEFAULT_RUN_OPTIONS, {}), false)
    assert.equal("period" in toStartBody("s", DEFAULT_RUN_OPTIONS, {}, null), false)
    assert.deepEqual(toStartBody("s", DEFAULT_RUN_OPTIONS, {}, { from: "2026-02-09", to: "2026-02-09" }).period, { date_from: "2026-02-09", date_to: "2026-02-09" })
  })
})
