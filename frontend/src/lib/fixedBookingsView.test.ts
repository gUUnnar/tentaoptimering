import assert from "node:assert/strict"
import { describe, it } from "node:test"
import type { FixedBookings } from "./precheckApi.ts"
import { actionText, bookingTime, fixedBookingsSummary } from "./fixedBookingsView.ts"

const data = (over: Partial<FixedBookings> = {}): FixedBookings => ({ status: "read", blocking: 12, removed: 0, unidentified_bookings: 12, unidentified_booked_places: 163, groups: [], bookings: [], truncated: false, note: "", ...over })

describe("fasta bokningar i förkontrollen", () => {
  it("klockslag över midnatt", () => {
    assert.equal(bookingTime({ start_minute: 480, end_minute: 780 }), "08:00–13:00")
    assert.equal(bookingTime({ start_minute: 1380, end_minute: 1500 }), "23:00–01:00")
  })
  it("sammanfattningen säger vad som spärrar, vad som tagits bort och vad som är okänt", () => {
    assert.equal(fixedBookingsSummary(data()), "12 spärrar salar; 12 saknar identifierad sal (okänd upptagenhet).")
    assert.match(fixedBookingsSummary(data({ removed: 3 })), /3 har tagits bort efter ditt val/)
  })
  it("borttagning beskrivs som ett uttryckligt val", () => {
    assert.match(actionText("remove"), /uttryckligt val/)
    assert.match(actionText("keep_fixed"), /spärras/)
  })
})
