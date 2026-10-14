import assert from "node:assert/strict"
import { describe, it } from "node:test"
import type { PrecheckResult } from "./precheckApi.ts"
import { precheckError, precheckTitle, precheckTone } from "./precheckView.ts"

const result = (over: Partial<PrecheckResult>): PrecheckResult => ({ verdict: "unclear", exams_total: 10, blocked_exams: 0, must_move_exams: 0, solver_outcome: "x", seconds: 2.5, reasons: [], ...over })

describe("förkontroll", () => {
  it("bara bevisade hinder är hinder", () => {
    assert.equal(precheckTone("impossible"), "blocker")
    assert.equal(precheckTone("blocked"), "blocker")
    assert.equal(precheckTone("possible"), "info")
    assert.equal(precheckTone("unclear"), "info")
  })
  it("rubrikerna säger vad som är bevisat och inte mer", () => {
    assert.match(precheckTitle(result({ verdict: "impossible" })), /bevisat att tentorna inte ryms/)
    assert.match(precheckTitle(result({ verdict: "blocked", blocked_exams: 1 })), /1 tenta har inget tillåtet tillfälle/)
    assert.match(precheckTitle(result({ verdict: "blocked", blocked_exams: 3 })), /3 tentor har inget tillåtet tillfälle/)
    assert.match(precheckTitle(result({ verdict: "possible", seconds: 2.5 })), /lösning hittades på 2.5 s/)
    assert.match(precheckTitle(result({ verdict: "unclear" })), /inget bevis för att det går/)
  })
  it("jobbfel som text", () => {
    assert.equal(precheckError("fel"), "fel")
    assert.equal(precheckError({ message: "kraschade" }), "kraschade")
    assert.equal(precheckError(null), "Förkontrollen misslyckades.")
  })
})
