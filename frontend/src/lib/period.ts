import type { PeriodCheck, PeriodCoverage } from "./jointTypes.ts"

// Val av planeringsperiod: genvägar, enkel kontroll och text. Själva kontrollen mot underlaget görs av servern.

export type PeriodChoice = { from: string; to: string }

const ISO = /^\d{4}-\d{2}-\d{2}$/
const DAY_MS = 86_400_000

const toTime = (iso: string): number => Date.UTC(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10)))
const toIso = (time: number): string => new Date(time).toISOString().slice(0, 10)

export const isIsoDate = (value: string): boolean => ISO.test(value) && toIso(toTime(value)) === value

export const addDays = (iso: string, days: number): string => toIso(toTime(iso) + days * DAY_MS)

/** Fel i själva valet (före anrop till servern), eller null. */
export function periodInputError(choice: PeriodChoice): string | null {
  if (!isIsoDate(choice.from) || !isIsoDate(choice.to)) return "Ange båda datumen."
  return choice.from > choice.to ? "Startdatum får inte vara senare än slutdatum." : null
}

export type PeriodPreset = { id: string; label: string; choice: PeriodChoice }

/** Genvägar som utgår från underlaget: en dag och en vecka från dagen med flest tentor, en månad från första dagen, och hela underlaget. */
export function periodPresets(coverage: PeriodCoverage | null): PeriodPreset[] {
  const demand = coverage?.demand
  if (!coverage || !demand) return []
  const busiest = coverage.days.reduce((best, day) => day.ready > best.ready ? day : best, coverage.days[0])
  const clamp = (iso: string) => iso > demand.last ? demand.last : iso
  const start = busiest?.date ?? demand.first
  return [
    { id: "day", label: "En dag", choice: { from: start, to: start } },
    { id: "week", label: "En vecka", choice: { from: start, to: clamp(addDays(start, 6)) } },
    { id: "month", label: "En månad", choice: { from: demand.first, to: clamp(addDays(demand.first, 27)) } },
    { id: "all", label: "Hela underlaget", choice: { from: demand.first, to: demand.last } },
  ]
}

/** En mening om vad som är planeringsbart i perioden. */
export function checkText(check: PeriodCheck): string {
  if (check.error) return check.error
  const unclear = check.not_ready_events ? `, ${check.not_ready_events} utan deltagarantal (ingår inte)` : ""
  return `${check.ready_events} ${check.ready_events === 1 ? "tenta" : "tentor"} kan planeras${unclear}.`
}

export const coverageText = (coverage: PeriodCoverage): string =>
  coverage.demand
    ? `Deltagarantal (${coverage.demand.source}) finns ${coverage.demand.first}–${coverage.demand.last}: ${coverage.demand.ready_events} tentor.`
    : "Det finns inget förberett efterfrågeunderlag."

export const sameChoice = (a: PeriodChoice | null, b: PeriodChoice | null): boolean => a === b || (!!a && !!b && a.from === b.from && a.to === b.to)
