import assert from "node:assert/strict"
import { describe, it } from "node:test"
import type { SavingsReady } from "./savingsApi.ts"
import { savingsHeadline, savingsPercent } from "./savingsView.ts"

const facts = (cost: number, bound: number | null = cost) => ({ cost_ore: cost, bound_ore: bound, staff_pool_size: 3, changed_exams: 0, exams_total: 12 })
const ready = (over: Partial<SavingsReady>): SavingsReady =>
  ({ state: "ready", baseline: facts(85_800_000), run: facts(37_900_000), potential_ore: 47_900_000, potential_low_ore: 47_900_000, potential_high_ore: 47_900_000, components: [], job: null, ...over })

describe("besparingspotential", () => {
  it("andel av Nuläge", () => {
    assert.equal(savingsPercent(85_800_000, 47_900_000), 56)
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
    const head = savingsHeadline(ready({ potential_low_ore: 40_000_000, potential_high_ore: 50_000_000 }))
    assert.match(head.range ?? "", /Mellan 400\s?000 kr och 500\s?000 kr/)
  })
  it("ingen besparing redovisas som positiv när Nuläge inte är dyrare", () => {
    const head = savingsHeadline(ready({ potential_ore: 0, potential_low_ore: 0, potential_high_ore: 0, run: facts(85_800_000) }))
    assert.equal(head.positive, false)
    assert.match(head.versus, /\(0 %\)/)
  })
})
