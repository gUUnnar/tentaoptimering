import type { FixedBookings } from "./precheckApi"

export const ACTION_TEXT: Record<string, string> = {
  keep_fixed: "Behåll fast: salen spärras under bokningens tid",
  remove: "Ta bort: spärrar ingenting (uttryckligt val, körningen blir en egen körning och märks explorativ)",
}

/** Begränsningen som alltid visas intill kostnaden när fasta bokningar finns. */
export const STAFF_LIMIT =
  "Kvarvarande fasta bokningar påverkar salspärrar och lokalkostnad (en sal med fast bokning räknas som använd), men deras vaktpersonal ingår inte i kostnaden."

export const actionText = (action: string): string => ACTION_TEXT[action] ?? action

/** Klockslag för en bokning, t.ex. "08:00–13:00". */
export function bookingTime(item: { start_minute: number; end_minute: number }): string {
  const clock = (minutes: number) => `${String(Math.floor(minutes / 60) % 24).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`
  return `${clock(item.start_minute)}–${clock(item.end_minute)}`
}

/** En mening: hur många bokningar som spärrar, hur många som tagits bort efter val och hur många som är okända. */
export function fixedBookingsSummary(data: FixedBookings): string {
  const parts = [`${data.blocking} spärrar salar`]
  if (data.removed > 0) parts.push(`${data.removed} har tagits bort efter ditt val och spärrar ingenting`)
  parts.push(`${data.unidentified_bookings} saknar identifierad sal (okänd upptagenhet)`)
  return `${parts.join("; ")}.`
}
