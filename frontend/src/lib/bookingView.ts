import type { BookingItem, BookingLocation, LocationSummary } from "./bookingTypes.ts"
import { addDays, daysBetween, isIsoDate } from "./dates.ts"

// Rena hjälpfunktioner för lokalvyn: tidslinjens placering, mått i läsbar form och datumsteg.

export const toMinutes = (clock: string | null): number | null => {
  const match = clock?.match(/^(\d{2}):(\d{2})$/)
  return match ? Number(match[1]) * 60 + Number(match[2]) : null
}

export function formatMinutes(minutes: number): string {
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return hours === 0 ? `${rest} min` : rest === 0 ? `${hours} h` : `${hours} h ${rest} min`
}

export const percent = (value: number | null): string => value === null ? "okänd" : `${Math.round(value * 100)} %`

/** Tidslinjens skala: hela timmar runt dagens bokningar, minst 08–18, så att dagar går att jämföra. */
export function timelineScale(items: BookingItem[]): { from: number; to: number } {
  const starts = items.map(item => toMinutes(item.start)).filter((value): value is number => value !== null)
  const ends = items.map(item => toMinutes(item.end)).filter((value): value is number => value !== null)
  return {
    from: Math.min(8 * 60, ...starts.map(value => Math.floor(value / 60) * 60)),
    to: Math.max(18 * 60, ...ends.map(value => Math.ceil(value / 60) * 60)),
  }
}

export type PlacedBar = { item: BookingItem; left: number; width: number; lane: number }

/** Placerar en dags bokningar på tidslinjen (procent av skalan) och lägger överlappande bokningar i egna rader. */
export function placeBars(items: BookingItem[], scale: { from: number; to: number }): { bars: PlacedBar[]; lanes: number } {
  const span = scale.to - scale.from
  const timed = items
    .map(item => ({ item, start: toMinutes(item.start), end: toMinutes(item.end) }))
    .filter((entry): entry is { item: BookingItem; start: number; end: number } => entry.start !== null && entry.end !== null && entry.end > entry.start)
    .sort((a, b) => a.start - b.start || a.end - b.end)
  const laneEnds: number[] = []
  const bars = timed.map(({ item, start, end }) => {
    let lane = laneEnds.findIndex(laneEnd => laneEnd <= start)
    if (lane === -1) { lane = laneEnds.length; laneEnds.push(end) } else laneEnds[lane] = end
    return { item, left: ((start - scale.from) / span) * 100, width: ((end - start) / span) * 100, lane }
  })
  return { bars, lanes: Math.max(1, laneEnds.length) }
}

/** Bokningar per datum, i datumordning. Dagar utan bokning tas inte med: de är inte "lediga", bara utan bokning i underlaget. */
export function groupByDay(items: BookingItem[]): [string, BookingItem[]][] {
  const days = new Map<string, BookingItem[]>()
  for (const item of items) if (item.date) days.set(item.date, [...(days.get(item.date) ?? []), item])
  return [...days.entries()].sort(([a], [b]) => a.localeCompare(b))
}

export type Range = { from: string; to: string }

export const rangeError = (range: Range): string | null =>
  !isIsoDate(range.from) || !isIsoDate(range.to) ? "Ange båda datumen." : range.from > range.to ? "Startdatum får inte vara senare än slutdatum." : null

/** Antal dagar i intervallet, inklusive båda ändarna. */
export const rangeDays = (range: Range): number => daysBetween(range.from, range.to) + 1

/** Nästa eller föregående intervall av samma längd. */
export const stepRange = (range: Range, direction: 1 | -1): Range => {
  const days = rangeDays(range)
  return { from: addDays(range.from, direction * days), to: addDays(range.to, direction * days) }
}

/** Standardintervall för en lokal: en vecka från dess första bokning. */
export const defaultRange = (location: BookingLocation): Range => ({ from: location.first, to: addDays(location.first, 6) })

export type Measure = { label: string; value: string; hint: string }

/** Måtten för en lokal och ett intervall, med det som saknas uttryckligen angivet (aldrig noll i stället för okänt). */
export function summaryMeasures(summary: LocationSummary, definitions: Record<string, string>): Measure[] {
  return [
    { label: "Bokningar", value: String(summary.bookings), hint: `${summary.exam_orders} tentamina${summary.cancelled_bookings ? `; ${summary.cancelled_bookings} avbokade ingår inte` : ""}` },
    { label: "Dagar med bokning", value: String(summary.days_with_bookings), hint: "Dagar utan bokning i underlaget är inte detsamma som lediga." },
    { label: "Bokad tid", value: formatMinutes(summary.booked_minutes), hint: definitions.booked_time ?? "" },
    { label: "Bokade platser", value: String(summary.booked_places), hint: definitions.booked_places ?? "" },
    { label: "Högsta samtidiga bokning", value: summary.capacity === null ? `${summary.peak_places} platser` : `${summary.peak_places} av ${summary.capacity} platser`,
      hint: summary.peak_share_of_capacity === null ? "Kapacitet okänd, så ingen andel kan anges." : `${percent(summary.peak_share_of_capacity)} av kapaciteten. ${definitions.seat_share ?? ""}` },
    { label: "Verklig närvaro", value: "okänd", hint: definitions.attendance ?? "" },
  ]
}

export const linkLabel = (link: string): string =>
  link === "single_candidate" ? "Trolig Ladok-koppling" : link === "ambiguous_candidates" ? "Tvetydig Ladok-koppling" : link === "no_candidate" ? "Ingen Ladok-koppling" : "Koppling ej bedömd"

/** Är kopplingen till Ladok något annat än en enda trolig kandidat? Sådana kopplingar märks, de gissas inte bort. */
export const linkIsUnclear = (link: string): boolean => link !== "single_candidate"
