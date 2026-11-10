import assert from "node:assert/strict"
import { describe, it } from "node:test"
import type { SavingsReady } from "./savingsApi.ts"
import { savingsHeadline, savingsPercent } from "./savingsView.ts"

const facts = (cost: number, bound: number | null = cost) => ({ cost_kr: cost, bound_kr: bound, staff_pool_size: 3, changed_exams: 0, exams_total: 12 })
const ready = (over: Partial<SavingsReady>): SavingsReady =>
  ({ state: "ready", baseline: facts(858_000), run: facts(379_000), potential_kr: 479_000, potential_low_kr: 479_000, potential_high_kr: 479_000, components: [], job: null, ...over })

describe("besparingspotential", () => {
  it("andel av kostnaden med låsta datum", () => {
    assert.equal(savingsPercent(858_000, 479_000), 56)
    assert.equal(savingsPercent(0, 10), null)
  })
  it("rubrik utan intervall när båda körningarna är bevisat optimala", () => {
    const head = savingsHeadline(ready({}))
    assert.match(head.amount, /479\s?000 kr per år/)
    assert.match(head.versus, /858\s?000 kr.*379\s?000 kr.*−56 %/)
    assert.equal(head.range, null)
    assert.equal(head.positive, true)
  })
  it("intervall när gränserna skiljer", () => {
    const head = savingsHeadline(ready({ potential_low_kr: 400_000, potential_high_kr: 500_000 }))
    assert.match(head.range ?? "", /Mellan 400\s?000 kr och 500\s?000 kr/)
  })
  it("ingen besparing redovisas som positiv när Låsta datum inte är dyrare", () => {
    const head = savingsHeadline(ready({ potential_kr: 0, potential_low_kr: 0, potential_high_kr: 0, run: facts(858_000) }))
    assert.equal(head.positive, false)
    assert.match(head.versus, /\(0 %\)/)
  })
})
