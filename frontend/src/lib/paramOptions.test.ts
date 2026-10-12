import assert from "node:assert/strict"
import { describe, it } from "node:test"
import { toJointOptions } from "./jointApi.ts"
import { computeChanges, changesToRequest } from "./paramDiff.ts"
import {
  availableOptions, defaultMovableLabels, digitalText, groupRooms, groupSummary, needsOptions, optionKind, roomsDraft, roomSummary, selectedRoomIds, selectedTypeValues,
  typeLabel, typesDraft, unknownRoomIds, unmatchedWords,
} from "./paramOptions.ts"
import { NO_ROOMS_DRAFT, parseDraft, toDraft } from "./paramValues.ts"
import { NO_OPTIONS, OPTIONS } from "./testing/optionsFixture.ts"
import { byId } from "./testing/paramFixture.ts"

const rooms = OPTIONS.rooms
const types = OPTIONS.exam_types
const ROOMS = byId("rooms.selection")
const MOVABLE = byId("flex.movable_types")

describe("vilka parametrar som väljs bland alternativ", () => {
  it("salslistan och flyttbara typer kräver alternativ, övriga inte", () => {
    assert.equal(optionKind(ROOMS), "rooms")
    assert.equal(optionKind(MOVABLE), "types")
    assert.equal(needsOptions(byId("calendar.weekdays")), false)
    assert.equal(needsOptions(byId("rooms.allow_split")), false)
  })
  it("alternativen räknas som saknade när underlaget saknas", () => {
    assert.equal(availableOptions({ status: "ready", error: "", data: NO_OPTIONS }), null)
    assert.equal(availableOptions({ status: "ready", error: "", data: OPTIONS }), OPTIONS)
    assert.equal(availableOptions({ status: "error", error: "x", data: null }), null)
    assert.equal(availableOptions({ status: "loading", error: "", data: null }), null)
  })
})

describe("salar: markering och utkast", () => {
  it("tom lista är alla salar markerade", () => {
    assert.deepEqual(selectedRoomIds([], rooms), rooms.map(room => room.room_id))
    assert.deepEqual(selectedRoomIds(["B-201", "A-101"], rooms), ["A-101", "B-201"])
    assert.deepEqual(selectedRoomIds([NO_ROOMS_DRAFT], rooms), [])
  })
  it("alla markerade ger tom lista, ingen ger ett fel, annars listan", () => {
    assert.deepEqual(roomsDraft(rooms, rooms.map(room => room.room_id), []), [])
    assert.deepEqual(roomsDraft(rooms, ["A-101", "B-201"], []), ["A-101", "B-201"])
    assert.deepEqual(roomsDraft(rooms, [], []), [NO_ROOMS_DRAFT])
    assert.deepEqual(parseDraft(ROOMS, [NO_ROOMS_DRAFT]), { ok: false, error: "Minst en sal måste vara vald." })
  })
  it("samma markering som från början ger det ursprungliga utkastet", () => {
    assert.deepEqual(roomsDraft(rooms, ["B-201", "A-101"], ["A-101", "B-201"]), ["A-101", "B-201"])
    const everything = rooms.map(room => room.room_id)
    assert.deepEqual(roomsDraft(rooms, everything, everything), everything)
  })
  it("sal-id måste finnas bland alternativen", () => {
    assert.deepEqual(parseDraft(ROOMS, ["A-101", "Z-9"], { roomIds: rooms.map(room => room.room_id) }), { ok: false, error: 'Salen "Z-9" finns inte bland salarna i underlaget.' })
    assert.deepEqual(parseDraft(ROOMS, ["B-201", "A-101"], { roomIds: rooms.map(room => room.room_id) }), { ok: true, value: ["A-101", "B-201"] })
    assert.deepEqual(parseDraft(ROOMS, []), { ok: true, value: [] })
    assert.equal(parseDraft(ROOMS, ["A-101", "A-101"]).ok, false)
    assert.deepEqual(unknownRoomIds(["A-101", "Z-9"], rooms), ["Z-9"])
  })
  it("grupperas per byggnad och sammanfattas med antal salar och platser", () => {
    const groups = groupRooms(rooms)
    assert.deepEqual(groups.map(group => [group.title, group.rooms.length]), [["Storgatan 1", 2], ["Lillgatan 2", 2], ["Byggnad saknas i underlaget", 1]])
    assert.equal(groupSummary(groups[0], ["A-101"]), "1 av 2 valda")
    assert.equal(roomSummary(rooms, ["A-101", "A-102"]).text, "2 av 5 salar valda, 180 platser")
    assert.equal(roomSummary(rooms, rooms.map(room => room.room_id)).text, "Alla salar (5 salar, 220 platser)")
    const none = roomSummary(rooms, [])
    assert.deepEqual([none.none, none.all, none.text], [true, false, "0 av 5 salar valda, 0 platser"])
  })
  it("digitalstöd i klartext", () => {
    assert.deepEqual((["all", "partial", "none", "unknown"] as const).map(digitalText),
      ["Digital: alla platser", "Digital: delvis", "Digital: nej", "Digital: okänt"])
  })
  it("en ändring av salarna går med i anropet som lista av strängar; oförändrat ger ingen ändring", () => {
    const edit = roomsDraft(rooms, ["A-101"], toDraft(ROOMS))
    assert.deepEqual(changesToRequest(computeChanges([ROOMS], { [ROOMS.id]: edit }, OPTIONS)), { "rooms.selection": ["A-101"] })
    assert.deepEqual(computeChanges([ROOMS], { [ROOMS.id]: roomsDraft(rooms, rooms.map(room => room.room_id), toDraft(ROOMS)) }, OPTIONS), [])
  })
})

describe("flyttbara tentamenstyper", () => {
  const original = toDraft(MOVABLE)
  it("en typ är markerad om något ord är en delsträng av typens värde", () => {
    assert.deepEqual(selectedTypeValues(original, types), ["ordinarie tentamen", "omtenta", "dugga", "hybridtenta"])
    assert.equal(selectedTypeValues(original, types).includes("hemtenta"), false)
    assert.deepEqual(selectedTypeValues([" DUGGA "], types), ["dugga"])
    assert.deepEqual(selectedTypeValues([""], types), [])
  })
  it("oförändrad markering behåller det ursprungliga värdet", () => {
    assert.deepEqual(typesDraft(types, ["omtenta", "ordinarie tentamen", "dugga", "hybridtenta"], original), ["ordinarie", "omtenta", "dugga", "hybrid"])
    assert.deepEqual(computeChanges([MOVABLE], { [MOVABLE.id]: original }, OPTIONS), [])
  })
  it("ändrad markering skrivs som typernas värden", () => {
    const draft = typesDraft(types, [...selectedTypeValues(original, types), "hemtenta"], original)
    assert.deepEqual(draft, ["ordinarie tentamen", "omtenta", "dugga", "hybridtenta", "hemtenta"])
    const [change] = computeChanges([MOVABLE], { [MOVABLE.id]: draft }, OPTIONS)
    assert.deepEqual(changesToRequest([change]), { "flex.movable_types": draft })
    assert.deepEqual(typesDraft(types, ["dugga"], original), ["dugga"])
    assert.deepEqual(typesDraft(types, [], original), [])
  })
  it("etiketter med antal, standardläge och ord som inte träffar någon typ", () => {
    assert.equal(typeLabel(types[2]), "Dugga (22)")
    assert.deepEqual(defaultMovableLabels(MOVABLE, types), ["Ordinarie tentamen", "Omtenta", "Dugga", "Hybridtenta"])
    assert.deepEqual(unmatchedWords(["dugga", "kompletteringstenta"], types), ["kompletteringstenta"])
  })
})

describe("alternativsvaret från backend", () => {
  it("normaliseras; saknat underlag ger tomma listor", () => {
    const out = toJointOptions({ ...OPTIONS, exam_types: [{ value: "Dugga", label: "Dugga", count: 3 }], rooms: [{ room_id: "A", label: "", building_id: null, address: null, capacity: null, digital: "konstigt" }] })
    assert.deepEqual(out.exam_types, [{ value: "dugga", label: "Dugga", count: 3 }])
    assert.deepEqual(out.rooms, [{ room_id: "A", label: "A", building_id: null, address: null, capacity: null, digital: "unknown" }])
    assert.deepEqual(toJointOptions({ ...OPTIONS, data_available: false }), { ...NO_OPTIONS, plan_area: "Uppsala" })
    assert.deepEqual(toJointOptions(null).rooms, [])
    assert.equal(toJointOptions(null).data_available, false)
  })
})
