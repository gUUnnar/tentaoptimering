import assert from "node:assert/strict"
import { describe, it } from "node:test"
import type { BookingItem, LocationSummary } from "./bookingTypes.ts"
import { addDays, daysBetween, isIsoDate, weekdayName } from "./dates.ts"
import { defaultRange, formatMinutes, groupByDay, linkIsUnclear, placeBars, rangeDays, rangeError, stepRange, summaryMeasures, timelineScale, toMinutes } from "./bookingView.ts"

const item = (id: string, date: string, start: string | null, end: string | null, extra: Partial<BookingItem> = {}): BookingItem => ({
  placement_id: id, exam_order_id: `o-${id}`, course_codes: "1AA001", course_name: "Analys", exam_type: "Ordinarie tenta", date, start, end,
  address: "A 1", room: "Sal 1", location_key: "a-1|sal-1", booked_places: 10, capacity: 100, seat_share: 0.1, status: "Klar", cancelled: false,
  digital: "Nej", ladok_link: "single_candidate", ladok_link_text: "", ...extra,
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
    assert.deepEqual(defaultRange({ location_key: "k", address: "a", room: null, label: "l", capacity: null, bookings: 1, first: "2026-02-09", last: "2026-03-01" }), { from: "2026-02-09", to: "2026-02-15" })
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
    assert.equal(linkIsUnclear("single_candidate"), false)
    for (const link of ["ambiguous_candidates", "no_candidate", "unknown"]) assert.equal(linkIsUnclear(link), true)
  })
})
