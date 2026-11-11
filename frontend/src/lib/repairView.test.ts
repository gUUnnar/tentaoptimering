import assert from "node:assert/strict"
import { describe, it } from "node:test"
import type { RepairResult } from "./repairApi.ts"
import { canApplyRepair, repairEffectText, repairIsVerified, repairProgressText, repairTitle, repairVerifiedText } from "./repairView.ts"

const result = (over: Partial<RepairResult> = {}): RepairResult => ({
  kind: "joint_repair", status: "found", summary: "x", parameters: { "calendar.weekdays": [1, 2, 3, 4, 5, 6] }, steps: [{ id: "weekday:6", label: "Tillåt lördag i kalendern", side_effect: null }],
  explorative: false, verified: { outcome: "solution", seconds: 2.1 }, exams_without_occasion: { before: 6, after: 0 }, searched: ["Kalender och datum"], note: "n", attempts: [], seconds: 3, ...over,
})

describe("förslag på minsta ändring", () => {
  it("verifierat är bara ett förslag där solvern hittade en lösning", () => {
    assert.equal(repairIsVerified(result()), true)
    assert.equal(repairIsVerified(result({ status: "unproven", verified: null })), false)
    assert.equal(repairIsVerified(result({ status: "found", verified: null })), false)
    assert.match(repairVerifiedText(result()), /hittade en lösning med förslaget på 2.1 s/)
    assert.match(repairVerifiedText(result({ status: "unproven", verified: null })), /inte bevisat/)
    assert.equal(repairVerifiedText(result({ status: "not_found", verified: null })), "")
  })

  it("bara ett förslag med ändringar kan föras över till formuläret", () => {
    assert.equal(canApplyRepair(result()), true)
    assert.equal(canApplyRepair(result({ status: "unproven", verified: null })), true)
    assert.equal(canApplyRepair(result({ status: "nothing_needed", parameters: {}, steps: [] })), false)
    assert.equal(canApplyRepair(result({ status: "not_found", parameters: { "x": 1 }, verified: null })), false)
    assert.equal(canApplyRepair(result({ parameters: {} })), false)
  })

  it("rubriker och effekt säger vad som gäller", () => {
    assert.match(repairTitle(result()), /minsta ändringen/)
    assert.match(repairTitle(result({ status: "unproven" })), /inte hunnit visa/)
    assert.match(repairTitle(result({ status: "not_found" })), /Ingen lösning hittades/)
    assert.equal(repairEffectText(result()), "Tentor utan tillåtet tillfälle: 6 → 0.")
    assert.equal(repairEffectText(result({ exams_without_occasion: { before: 0, after: 0 } })), "")
    assert.equal(repairProgressText(null), "Söker …")
    assert.equal(repairProgressText("Prövar: Tillåt lördag i kalendern"), "Prövar: Tillåt lördag i kalendern …")
  })
})
