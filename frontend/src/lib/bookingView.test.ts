import assert from "node:assert/strict"
import { describe, it } from "node:test"
import type { BookingItem, CompareDemand, LocationSummary } from "./bookingTypes.ts"
import { addDays, daysBetween, isIsoDate, weekdayName } from "./dates.ts"
import { defaultRange, flagLabel, flagList, formatMinutes, linkLabel, moveText, overviewMeasures, placeText, unnamedShare, groupByDay, linkIsUnclear, placeBars, rangeDays, rangeError, stepRange, summaryMeasures, timelineScale, toMinutes } from "./bookingView.ts"

const item = (id: string, date: string, start: string | null, end: string | null, extra: Partial<BookingItem> = {}): BookingItem => ({
  placement_id: id, exam_order_id: `o-${id}`, course_codes: "1AA001", course_name: "Analys", exam_type: "Ordinarie tenta", date, start, end,
  address: "A 1", room: "Sal 1", location_key: "a-1|sal-1", booked_places: 10, capacity: 100, seat_share: 0.1, status: "Klar", cancelled: false,
  digital: "Nej", identification: "room_matched", identification_text: "", place_label: "A 1 – Sal 1", flags: [], status_class: "active", ladok_coverage: "within", link_certainty: "unique", link_text: "", ...extra,
})

describe("datum", () => {
  it("räknar över månads- och skottårsskifte och känner igen ogiltiga datum", () => {
    assert.equal(addDays("2026-02-27", 3), "2026-03-02")
    assert.equal(addDays("2028-02-28", 1), "2028-02-29")
    assert.equal(daysBetween("2026-01-12", "2026-01-18"), 6)
    assert.equal(isIsoDate("2026-02-30"), false)
    assert.equal(weekdayName("2026-02-09"), "måndag")
  })
})

describe("lokalvyns tidslinje", () => {
  it("klockslag och längder", () => {
    assert.equal(toMinutes("08:30"), 510)
    assert.equal(toMinutes(null), null)
    assert.equal(toMinutes("8:30"), null)
    assert.equal(formatMinutes(360), "6 h")
    assert.equal(formatMinutes(95), "1 h 35 min")
    assert.equal(formatMinutes(20), "20 min")
  })
  it("skalan följer bokningarna men är minst 08–18", () => {
    assert.deepEqual(timelineScale([]), { from: 480, to: 1080 })
    assert.deepEqual(timelineScale([item("a", "d", "07:30", "20:15")]), { from: 420, to: 1260 })
    assert.deepEqual(timelineScale([item("a", "d", "10:00", "12:00")]), { from: 480, to: 1080 })
  })
  it("överlappande bokningar får egna rader och placeras i procent av skalan", () => {
    const scale = { from: 480, to: 1080 }
    const { bars, lanes } = placeBars([item("b", "d", "10:00", "14:00"), item("a", "d", "08:00", "12:00"), item("c", "d", "14:00", "16:00")], scale)
    assert.equal(lanes, 2)
    assert.deepEqual(bars.map(bar => [bar.item.placement_id, bar.lane]), [["a", 0], ["b", 1], ["c", 0]])  // c börjar när a slutat
    assert.equal(bars[0].left, 0)
    assert.equal(Math.round(bars[0].width), 40)
    assert.equal(Math.round(bars[1].left), 20)
  })
  it("bokning utan tid placeras inte och förvanskas inte", () => {
    const { bars, lanes } = placeBars([item("x", "d", null, null)], { from: 480, to: 1080 })
    assert.deepEqual([bars.length, lanes], [0, 1])
  })
  it("grupperar per datum i ordning och hoppar över rader utan datum", () => {
    const days = groupByDay([item("2", "2026-02-10", "08:00", "09:00"), item("1", "2026-02-09", "08:00", "09:00"), item("3", "2026-02-09", "10:00", "11:00"), item("z", "", null, null, { date: null })])
    assert.deepEqual(days.map(([date, rows]) => [date, rows.length]), [["2026-02-09", 2], ["2026-02-10", 1]])
  })
})

describe("intervall", () => {
  it("fel och steg", () => {
    assert.equal(rangeError({ from: "2026-02-09", to: "2026-02-15" }), null)
    assert.match(rangeError({ from: "2026-02-15", to: "2026-02-09" }) ?? "", /inte vara senare/)
    assert.match(rangeError({ from: "", to: "2026-02-09" }) ?? "", /båda datumen/)
    assert.equal(rangeDays({ from: "2026-02-09", to: "2026-02-15" }), 7)
    assert.deepEqual(stepRange({ from: "2026-02-09", to: "2026-02-15" }, 1), { from: "2026-02-16", to: "2026-02-22" })
    assert.deepEqual(stepRange({ from: "2026-02-09", to: "2026-02-15" }, -1), { from: "2026-02-02", to: "2026-02-08" })
    assert.deepEqual(defaultRange({ location_key: "k", address: "a", room: null, identification: "address_only", label: "l", capacity: null, bookings: 1, first: "2026-02-09", last: "2026-03-01" }), { from: "2026-02-09", to: "2026-02-15" })
  })
})

describe("mått", () => {
  const summary: LocationSummary = { bookings: 13, cancelled_bookings: 2, exam_orders: 12, days_with_bookings: 3, booked_minutes: 660, booked_places: 486, capacity: 206, peak_places: 190, peak_share_of_capacity: 0.922, untimed_bookings: 0 }
  const definitions = { booked_time: "tid", booked_places: "platser", seat_share: "andel", attendance: "okänd närvaro" }
  it("varje mått har sin definition och verklig närvaro är okänd, aldrig noll", () => {
    const rows = Object.fromEntries(summaryMeasures(summary, definitions).map(row => [row.label, row]))
    assert.equal(rows["Bokad tid"].value, "11 h")
    assert.equal(rows["Bokad tid"].hint, "tid")
    assert.equal(rows["Bokningar"].hint, "12 tentamina; 2 avbokade ingår inte")
    assert.equal(rows["Högsta samtidiga bokning"].value, "190 av 206 platser")
    assert.match(rows["Högsta samtidiga bokning"].hint, /^92 % av kapaciteten/)
    assert.equal(rows["Verklig närvaro"].value, "okänd")
    assert.match(rows["Dagar med bokning"].hint, /inte detsamma som lediga/)
  })
  it("utan känd kapacitet anges ingen andel", () => {
    const rows = Object.fromEntries(summaryMeasures({ ...summary, capacity: null, peak_share_of_capacity: null }, definitions).map(row => [row.label, row]))
    assert.equal(rows["Högsta samtidiga bokning"].value, "190 platser")
    assert.match(rows["Högsta samtidiga bokning"].hint, /Kapacitet okänd/)
  })
  it("tveksamma Ladok-kopplingar märks", () => {
    assert.equal(linkIsUnclear("unique"), false)
    assert.equal(linkIsUnclear("none_outside_coverage"), false)  // kan inte finnas: inte oklar, inte tillämplig
    for (const link of ["ambiguous", "none_within_coverage", "none_coverage_unknown"]) assert.equal(linkIsUnclear(link), true)
    assert.equal(linkLabel("none_outside_coverage"), "Utanför Ladok-period")
  })
})

describe("översikt per period och adress", () => {
  const totals = { placements: 54, cancelled_placements: 2, exam_orders: 31, booked_places: 1585, addresses: 4, no_address_placements: 1, address_only_placements: 22, exam_orders_in_several_places: 22 }
  it("tentamina räknas en gång, bokningar utan sal och utan adress redovisas, närvaro är okänd", () => {
    const rows = Object.fromEntries(overviewMeasures(totals, { booked_places: "platser", attendance: "okänd närvaro" }).map(row => [row.label, row]))
    assert.equal(rows["Tentamina"].value, "31")
    assert.match(rows["Tentamina"].hint, /22 använder flera lokaler/)
    assert.match(rows["Bokningsrader"].hint, /2 avbokade ingår inte/)
    assert.equal(rows["Sal saknas i uttaget"].value, "22")
    assert.match(rows["Sal saknas i uttaget"].hint, /Orsaken är okänd/)
    assert.equal(rows["Utan adress"].value, "1")
    assert.equal(rows["Verklig närvaro"].value, "okänd")
  })
  it("andel utan salnamn", () => {
    assert.equal(unnamedShare(59, 41), 41)
    assert.equal(unnamedShare(0, 0), null)
  })
})

describe("jämförelse mot körning", () => {
  const demand = (extra: Partial<CompareDemand> = {}): CompareDemand => ({
    exam_demand_id: "e", course_code: "1AA001", participants: 90, duration_minutes: 240, movable: true,
    original: { date: "2026-02-09", start: "08:00", slot_id: "2026-02-09T08:00" }, simulated: { date: "2026-02-10", start: "14:00", slot_id: "2026-02-10T14:00" },
    moved: true, date_shift_days: 1, start_changed: true, simulated_rooms: [], rooms_compared: true, same_rooms: false, booked_rooms_without_name: 0,
    booked_addresses: ["Gata 1"], simulated_addresses: ["Gata 3"], same_addresses: false, ...extra,
  })
  it("flyttad, oförändrad och saknad tid", () => {
    assert.equal(moveText(demand()), "Flyttad (1 dag senare): 2026-02-09 kl. 08:00 → 2026-02-10 kl. 14:00.")
    assert.match(moveText(demand({ date_shift_days: -3 })), /3 dagar tidigare/)
    assert.match(moveText(demand({ date_shift_days: 0 })), /samma dag/)
    assert.equal(moveText(demand({ moved: false, simulated: { date: "2026-02-09", start: "08:00", slot_id: "x" } })), "Oförändrad: 2026-02-09 kl. 08:00.")
    assert.match(moveText(demand({ simulated: null })), /saknas/)
  })
  it("salar jämförs bara när alla bokade lokaler har salnamn; adress går alltid", () => {
    assert.equal(placeText(demand()), "Adress: bokad Gata 1, simulerad Gata 3. Andra salar än bokningen.")
    assert.equal(placeText(demand({ same_addresses: true, same_rooms: true, simulated_addresses: ["Gata 1"] })), "Samma adress (Gata 1). Samma salar.")
    assert.match(placeText(demand({ rooms_compared: false, same_rooms: null, booked_rooms_without_name: 2 })), /Salar jämförs inte: 2 bokade lokaler saknar salnamn/)
    assert.match(placeText(demand({ rooms_compared: false, same_rooms: null, booked_rooms_without_name: 1 })), /1 bokad lokal saknar salnamn/)
    assert.match(placeText(demand({ rooms_compared: false, same_rooms: null, booked_addresses: [] })), /okänd adress/)
  })
})

describe("fynd i datat", () => {
  it("koder får läsbar text, okända koder visas som de är, och störst fynd kommer först", () => {
    assert.equal(flagLabel("room_missing"), "sal saknas i uttaget")
    assert.equal(flagLabel("something_new"), "something_new")
    assert.deepEqual(flagList({ flags: { date_missing: 1, room_missing: 22 } }).map(item => [item.code, item.count]), [["room_missing", 22], ["date_missing", 1]])
  })
})
