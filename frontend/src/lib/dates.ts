// Datum som ÅÅÅÅ-MM-DD utan tidszonsfel: all räkning sker i UTC.

const ISO = /^\d{4}-\d{2}-\d{2}$/
const DAY_MS = 86_400_000

const toTime = (iso: string): number => Date.UTC(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10)))
const toIso = (time: number): string => new Date(time).toISOString().slice(0, 10)

/** Ett riktigt kalenderdatum (2026-02-30 är det inte). */
export const isIsoDate = (value: string): boolean => ISO.test(value) && toIso(toTime(value)) === value

export const addDays = (iso: string, days: number): string => toIso(toTime(iso) + days * DAY_MS)

export const daysBetween = (from: string, to: string): number => Math.round((toTime(to) - toTime(from)) / DAY_MS)

const WEEKDAYS = ["söndag", "måndag", "tisdag", "onsdag", "torsdag", "fredag", "lördag"]
export const weekdayName = (iso: string): string => WEEKDAYS[new Date(toTime(iso)).getUTCDay()]
