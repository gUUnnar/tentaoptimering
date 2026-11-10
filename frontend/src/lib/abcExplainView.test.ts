import assert from "node:assert/strict"
import { describe, it } from "node:test"
import type { AbcExplained, ExplainedDetail } from "./abcTypes.ts"
import { examsFor, hasDetail, headline, itemsReconcile, realizationView, roomNamer, signedHours, signedKr, splitSentence, tagText } from "./abcExplainView.ts"

const side = { kind: "C", name: "x", cost_kind: "model_calculated", cost_kind_text: "t", resource_data: null, staffing_origin: "model_calculated", priced_by: "own", reservations: null, optimum: { gap_kr: null, proven: true } }

const detail = (over: Partial<ExplainedDetail> = {}): AbcExplained & ExplainedDetail => ({
  available: true, reasons: [], notes: [],
  basis: { left: side, right: side },
  total: { left_kr: 1_757, right_kr: 1_036, difference_kr: -721, label: "" },
  split: { available: true, usage_kr: -721, assumption_kr: 0, same_prices: true },
  items: [
    { key: "rooms", label: "Hyrda lokaler", left_kr: 1_400, right_kr: 1_000, difference_kr: -400, usage_kr: -400, assumption_kr: 0, drivers: [] },
    { key: "external", label: "Externa bokningar", left_kr: 300, right_kr: 0, difference_kr: -300, usage_kr: -300, assumption_kr: 0, drivers: [] },
    { key: "staff", label: "Personal (betald tid)", left_kr: 57, right_kr: 36, difference_kr: -21, usage_kr: -21, assumption_kr: 0, drivers: [] },
  ],
  rooms: [{ room_id: "own-b", name: "Egen sal B", kind: "internal", status: "avoidable" }],
  exams: {
    compared: 3, unchanged: 1, time_changed: 1, room_changed: 2, changed_count: 2, truncated: false, changed: [
      { exam_event_id: "e2", course: "E2", participants: 60, before: { date: "d", start: "08:00", rooms: [], room_ids: ["ext-1"] }, after: { date: "d", start: "14:00", rooms: [], room_ids: ["own-a"] }, changes: ["start", "room"], tags: ["external_avoided"] },
      { exam_event_id: "e3", course: "E3", participants: 40, before: { date: "d", start: "14:00", rooms: [], room_ids: ["own-b"] }, after: { date: "d", start: "14:00", rooms: [], room_ids: ["own-a"] }, changes: ["room"], tags: ["room_freed:own-b"] },
    ],
  },
  ...over,
} as never)

describe("förklarad besparing i gränssnittet", () => {
  it("kostnadsposterna ska summera till totalskillnaden", () => {
    assert.ok(itemsReconcile(detail()))
    const broken = detail()
    broken.items[0] = { ...broken.items[0], difference_kr: -390 }
    assert.ok(!itemsReconcile(broken))
    assert.ok(!itemsReconcile(detail({ total: { left_kr: 1, right_kr: 1, difference_kr: null, label: "" } })))
    const withheld = detail()
    withheld.items = withheld.items.map(item => ({ ...item, difference_kr: null }))
    assert.ok(!itemsReconcile(withheld), "a blocked comparison has no differences to reconcile")
  })
  it("rubriken säger minskar eller ökar och kallar det aldrig en besparing", () => {
    assert.match(headline(detail()), /^Modellkostnaden minskar med 721 kr$/)
    assert.match(headline(detail({ total: { left_kr: 1, right_kr: 2, difference_kr: 1, label: "" } })), /ökar med 1 kr/)
    assert.match(headline(detail({ total: { left_kr: 1, right_kr: 1, difference_kr: null, label: "" } })), /Ingen totalskillnad/)
    assert.doesNotMatch(headline(detail()), /besparing/i)
  })
  it("tecken och timmar", () => {
    assert.equal(signedKr(-21), "−21 kr")
    assert.equal(signedKr(21), "+21 kr")
    assert.equal(signedKr(0), "0 kr")
    assert.equal(signedKr(null), "–")
    assert.equal(signedHours(-210), "−3,5 h")
    assert.equal(signedHours(90), "+1,5 h")
  })
  it("uppdelningen i utnyttjande och priser, eller skälet till att den saknas", () => {
    assert.match(splitSentence(detail()), /hela skillnaden är ändrat resursutnyttjande/)
    const changed = detail({ split: { available: true, usage_kr: -418, assumption_kr: 500, same_prices: false } })
    assert.match(splitSentence(changed), /Ändrat resursutnyttjande −418 kr; ändrade priser, regler eller antaganden \+500 kr/)
    assert.match(splitSentence(detail({ split: { available: false, reason: "salen saknar pris" } })), /salen saknar pris/)
  })
  it("bara observerade och avtalsstödda besparingar är verifierade", () => {
    assert.ok(realizationView("verified").verified)
    for (const status of ["possible_unverified", "conditional", "blocked_shared", "blocked_contract", "okänd"]) assert.ok(!realizationView(status).verified, status)
  })
  it("tentor kopplas till kostnadsposten de förklarar", () => {
    const explained = detail()
    assert.deepEqual(examsFor("external", explained).map(row => row.exam_event_id), ["e2"])
    assert.deepEqual(examsFor("rooms", explained).map(row => row.exam_event_id), ["e2", "e3"])
    assert.equal(tagText("room_freed:own-b", roomNamer(explained)), "Egen sal B kan avvaras")
    assert.equal(tagText("external_avoided", roomNamer(explained)), "Extern bokning undviks")
  })
  it("ett svar utan detaljer känns igen", () => {
    assert.ok(!hasDetail({ available: false, reasons: ["x"], notes: [] }))
    assert.ok(hasDetail(detail()))
  })
})
