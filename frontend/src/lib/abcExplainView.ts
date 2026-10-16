import { formatKr } from "./jointFormat.ts"
import type { AbcExplained, ExplainOrigin, ExplainedDetail, ExplainedExamChange, ExplainedItem, ExplainedRoom } from "./abcTypes.ts"

const MINUS = "−"
const hourFormat = new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 1, minimumFractionDigits: 1 })

/** Kronor med tecken: plus för en ökning, riktigt minustecken för en minskning, utan tecken för noll. */
export function signedKr(ore: number | null | undefined): string {
  if (ore === null || ore === undefined) return "–"
  if (ore === 0) return formatKr(0)
  return `${ore > 0 ? "+" : MINUS}${formatKr(Math.abs(ore))}`
}

/** Betalda minuter som timmar, t.ex. "9,5 h". */
export const hours = (minutes: number): string => `${hourFormat.format(minutes / 60)} h`

export function signedHours(minutes: number): string {
  if (minutes === 0) return hours(0)
  return `${minutes > 0 ? "+" : MINUS}${hours(Math.abs(minutes))}`
}

export const signedCount = (value: number): string => value === 0 ? "0" : `${value > 0 ? "+" : MINUS}${Math.abs(value)}`

export const ORIGIN_TEXT: Record<ExplainOrigin, string> = {
  observed: "observerad", model_calculated: "modellberäknad", simulated: "simulerad", assumption: "antagen",
}

export const COST_KIND_TEXT: Record<string, string> = {
  model_calculated: "Modellberäknad kostnad",
  model_calculated_for_historical_bookings: "Modellberäknad kostnad för de historiska bokningarna",
}

export const STAFF_ORIGIN_TEXT: Record<string, string> = {
  model_calculated: "beräknad av modellen",
  model_calculated_from_booked_places: "beräknad av modellen ur bokade platser (inte observerad bemanning)",
}

export type RealizationView = { label: string; verified: boolean; tone: "ok" | "warn" | "bad" }

/** Hur en frigjord lokals besparing får läsas. Bara `verified` och `external_per_booking` är verifierade. */
export const REALIZATION_TEXT: Record<string, RealizationView> = {
  verified: { label: "Verifierad", verified: true, tone: "ok" },
  external_per_booking: { label: "Verifierad (debiteras per bokning)", verified: true, tone: "ok" },
  possible_unverified: { label: "Villkorad: villkoren är inte verifierade", verified: false, tone: "warn" },
  conditional: { label: "Villkorad: avtalsuppgifter saknas", verified: false, tone: "warn" },
  blocked_shared: { label: "Frigörs inte: delar avtal med en sal som används", verified: false, tone: "bad" },
  blocked_contract: { label: "Frigörs inte: avtalet kan inte sägas upp", verified: false, tone: "bad" },
}

export const realizationView = (status: string): RealizationView => REALIZATION_TEXT[status] ?? { label: status, verified: false, tone: "warn" }

export const ROOM_STATUS_TEXT: Record<ExplainedRoom["status"], string> = { kept: "Behålls", avoidable: "Kan avvaras", added: "Tillkommer" }

export const hasDetail = (explained: AbcExplained | undefined | null): explained is AbcExplained & ExplainedDetail => !!explained && !!explained.items && !!explained.total

/** Kostnadsposternas skillnader ska summera till totalskillnaden; gränssnittet visar det som en kontroll. */
export function itemsReconcile(explained: AbcExplained & ExplainedDetail): boolean {
  const difference = explained.total.difference_ore
  return difference !== null && explained.items.every(item => item.difference_ore !== null) && explained.items.reduce((sum, item) => sum + (item.difference_ore ?? 0), 0) === difference
}

/** Rubrik för totalen: minskar, ökar eller ändras inte, utan att kalla det en besparing. */
export function headline(explained: AbcExplained & ExplainedDetail): string {
  const difference = explained.total.difference_ore
  if (difference === null) return "Ingen totalskillnad kan redovisas"
  if (difference === 0) return "Modellkostnaden är oförändrad"
  return `Modellkostnaden ${difference < 0 ? "minskar" : "ökar"} med ${formatKr(Math.abs(difference))}`
}

export function direction(item: Pick<ExplainedItem, "difference_ore">): "down" | "up" | "same" {
  const difference = item.difference_ore ?? 0
  return difference < 0 ? "down" : difference > 0 ? "up" : "same"
}

/** En mening om uppdelningen i ändrat resursutnyttjande och ändrade priser; säger varför den saknas när den inte går att göra. */
export function splitSentence(explained: AbcExplained & ExplainedDetail): string {
  const { split } = explained
  if (!split.available) return split.reason ?? "Skillnaden kan inte delas upp i utnyttjande och priser."
  if (split.same_prices) return "Samma priser och regler på båda sidor: hela skillnaden är ändrat resursutnyttjande."
  return `Ändrat resursutnyttjande ${signedKr(split.usage_ore ?? 0)}; ändrade priser, regler eller antaganden ${signedKr(split.assumption_ore ?? 0)}.`
}

/** En etikett från backendens tentamenstagg ("room_freed:uu-r2" och så vidare). */
export function tagText(tag: string, roomName: (roomId: string) => string): string {
  if (tag.startsWith("room_freed:")) return `${roomName(tag.slice("room_freed:".length))} kan avvaras`
  if (tag === "external_avoided") return "Extern bokning undviks"
  if (tag === "external_added") return "Extern bokning tillkommer"
  return tag
}

export const changeText = (change: ExplainedExamChange["changes"][number]): string => ({ date: "datum", start: "klockslag", room: "sal" })[change]

/** Namnet på en sal ur jämförelsen, annars id:t. */
export function roomNamer(explained: AbcExplained & ExplainedDetail): (roomId: string) => string {
  const names = new Map(explained.rooms.map(room => [room.room_id, room.name]))
  return roomId => names.get(roomId) ?? roomId
}

/** Tentor som ändrats för en kostnadspost: de som har en tagg eller byter sal respektive tid som hör till posten. */
export function examsFor(item: ExplainedItem["key"], explained: AbcExplained & ExplainedDetail): ExplainedExamChange[] {
  const rows = explained.exams.changed
  if (item === "rooms") return rows.filter(row => row.tags.some(tag => tag.startsWith("room_freed:")) || row.changes.includes("room"))
  if (item === "external") return rows.filter(row => row.tags.some(tag => tag.startsWith("external_")))
  return rows.filter(row => row.changes.includes("date") || row.changes.includes("start") || row.changes.includes("room"))
}

/** Varningar som alltid ska synas: simulerade uppgifter, proxypriser, spärrade bokningar. */
export function qualityFlags(explained: AbcExplained): string[] {
  return hasDetail(explained) ? explained.data_quality.flags.map(flag => flag.text) : []
}
