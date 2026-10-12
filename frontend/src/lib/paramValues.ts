import type { ParameterInfo, ParamValueType } from "./jointTypes.ts"
import { oreToKrText, parseKrToOre, unitInfo } from "./paramUnits.ts"

// Redigeringsutkast, tolkning och validering per värdetyp. Utkastet är det som användaren skriver (oftast text);
// tolkningen ger det värde som skickas till API:et, eller ett begripligt felmeddelande.

export type LadderRow = { max: string; staff: string }
export type RangeRow = { start: string; end: string }
export type ParseResult = { ok: true; value: unknown } | { ok: false; error: string }
/** Det som tolkningen behöver veta utöver parametern: vilka sal-id:n som finns i underlaget (okänt = ingen kontroll). */
export type ParseContext = { roomIds?: readonly string[] }
/** Utkastet för "ingen sal vald". Tom lista betyder alla salar, så "ingen" behöver en egen markering. Den kan aldrig skickas: tolkningen ger felet "Minst en sal måste vara vald." */
export const NO_ROOMS_DRAFT = "__ingen_sal__"

const EDITABLE: ReadonlySet<ParamValueType> = new Set([
  "integer", "number", "boolean", "choice", "date", "time", "time_list", "integer_list", "string_list", "room_id_list",
  "staffing_ladder", "date_range_list", "time_range_list",
])
/** Typer som har en redigerare i gränssnittet. Övriga (matris, regeluppsättning m.fl.) visas skrivskyddat. Salslistan kräver dessutom alternativ ur underlaget (se paramOptions.ts). */
export const hasEditor = (valueType: ParamValueType): boolean => EDITABLE.has(valueType)

export const WEEKDAYS = [
  { value: 1, label: "Måndag", short: "mån" }, { value: 2, label: "Tisdag", short: "tis" }, { value: 3, label: "Onsdag", short: "ons" },
  { value: 4, label: "Torsdag", short: "tors" }, { value: 5, label: "Fredag", short: "fre" }, { value: 6, label: "Lördag", short: "lör" },
  { value: 7, label: "Söndag", short: "sön" },
] as const

/** Heltalslistan med ISO-veckodagar (1 = måndag … 7 = söndag) får markerbara knappar i stället för fri inmatning. */
export const isWeekdayParam = (param: Pick<ParameterInfo, "id" | "value_type" | "choices">): boolean =>
  param.value_type === "integer_list" && !param.choices && /(^|\.)weekdays$/.test(param.id)

const isMoney = (param: Pick<ParameterInfo, "unit">) => unitInfo(param.unit).money
const asArray = (value: unknown): unknown[] => Array.isArray(value) ? value : []
const asRecord = (value: unknown): Record<string, unknown> => value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {}
const text = (value: unknown): string => value === null || value === undefined ? "" : String(value)

/** Värdet från API:et som redigerbart utkast. */
export function toDraft(param: ParameterInfo, value: unknown = param.value): unknown {
  switch (param.value_type) {
    case "integer": case "number":
      if (typeof value !== "number") return text(value)
      return isMoney(param) ? oreToKrText(value) : String(value).replace(".", ",")
    case "boolean": return value === true
    case "choice": return value
    case "date": case "time": return text(value)
    case "time_list": case "integer_list": case "string_list": case "room_id_list": return asArray(value).map(text)
    case "staffing_ladder": return asArray(value).map((row): LadderRow => ({ max: text(asRecord(row).max_participants), staff: text(asRecord(row).required_staff) }))
    case "date_range_list": case "time_range_list": return asArray(value).map((row): RangeRow => ({ start: text(asRecord(row).start), end: text(asRecord(row).end) }))
    default: return value
  }
}

// ---- Enskilda värden -----------------------------------------------------------------------------------------------

const ok = (value: unknown): ParseResult => ({ ok: true, value })
const fail = (error: string): ParseResult => ({ ok: false, error })

export function parseInteger(input: string): ParseResult {
  const clean = input.replace(/[\s  ]/g, "")
  if (!/^-?\d+$/.test(clean)) return fail("Ange ett heltal utan decimaler.")
  const value = Number(clean)
  return Number.isSafeInteger(value) ? ok(value) : fail("Talet är för stort.")
}

export function parseNumber(input: string): ParseResult {
  const clean = input.replace(/[\s  ]/g, "").replace(",", ".")
  if (!/^-?\d+(\.\d+)?$/.test(clean)) return fail("Ange ett tal, till exempel 0,5.")
  const value = Number(clean)
  return Number.isFinite(value) ? ok(value) : fail("Talet är för stort.")
}

export function isValidTime(value: string): boolean { return /^([01]\d|2[0-3]):[0-5]\d$/.test(value) }

export function isValidDate(value: string): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) return false
  const [year, month, day] = [Number(match[1]), Number(match[2]), Number(match[3])]
  const date = new Date(Date.UTC(year, month - 1, day))
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day
}

// ---- Bemanningstrappan ---------------------------------------------------------------------------------------------

export type LadderCheck = { rowErrors: (string | null)[]; error: string | null }

/** Trappan: "upp till X deltagare kräver Y vakter". Trösklarna måste vara positiva heltal som stiger för varje rad. */
export function validateLadder(rows: LadderRow[]): LadderCheck {
  if (!rows.length) return { rowErrors: [], error: "Trappan måste ha minst en rad." }
  let previous = 0
  const rowErrors = rows.map((row): string | null => {
    const max = parseInteger(row.max)
    const staff = parseInteger(row.staff)
    if (!max.ok || (max.value as number) < 1) return "Antal deltagare måste vara ett heltal som är minst 1."
    if (!staff.ok || (staff.value as number) < 1) return "Antal vakter måste vara ett heltal som är minst 1."
    const threshold = max.value as number
    if (threshold <= previous) return `Tröskeln måste vara högre än föregående rad (${previous}).`
    previous = threshold
    return null
  })
  const first = rowErrors.findIndex(item => item !== null)
  return { rowErrors, error: first < 0 ? null : `Rad ${first + 1}: ${rowErrors[first]}` }
}

// ---- Tolkning av ett helt utkast -----------------------------------------------------------------------------------

function parseList(param: ParameterInfo, draft: unknown): ParseResult {
  const items = asArray(draft).map(text)
  const kind = param.value_type
  if (kind === "time_list") {
    const bad = items.find(item => !isValidTime(item))
    if (bad !== undefined) return fail(`"${bad || "tomt fält"}" är ingen giltig tid. Skriv klockslag som 08:00.`)
    if (new Set(items).size !== items.length) return fail("Samma tid finns flera gånger.")
    if (!items.length) return fail("Ange minst en tid.")
    return ok([...items].sort())
  }
  if (kind === "integer_list") {
    const numbers: number[] = []
    for (const item of items) {
      const parsed = parseInteger(item)
      if (!parsed.ok) return fail(`"${item || "tomt fält"}" är inget heltal.`)
      numbers.push(parsed.value as number)
    }
    if (new Set(numbers).size !== numbers.length) return fail("Samma värde finns flera gånger.")
    if (isWeekdayParam(param)) {
      if (!numbers.length) return fail("Välj minst en veckodag.")
      if (numbers.some(n => n < 1 || n > 7)) return fail("Veckodagar anges som 1 (måndag) till 7 (söndag).")
    }
    return ok(numbers.sort((a, b) => a - b))
  }
  const cleaned = items.map(item => item.trim())
  if (cleaned.some(item => item === "")) return fail("Ta bort tomma rader i listan.")
  if (new Set(cleaned).size !== cleaned.length) return fail("Samma värde finns flera gånger.")
  const allowed = param.choices?.map(choice => String(choice.value))
  const unknown = allowed ? cleaned.find(item => !allowed.includes(item)) : undefined
  return unknown !== undefined ? fail(`"${unknown}" är inget tillåtet alternativ.`) : ok(cleaned)
}

/** Sal-id:n. Tom lista betyder alla salar. Id:n sorteras så att ordningen inte spelar roll. */
function parseRoomIds(draft: unknown, context: ParseContext): ParseResult {
  const items = asArray(draft).map(item => text(item).trim())
  if (items.includes(NO_ROOMS_DRAFT)) return fail("Minst en sal måste vara vald.")
  if (items.some(item => item === "")) return fail("Ta bort tomma rader i listan.")
  if (new Set(items).size !== items.length) return fail("Samma sal finns flera gånger.")
  const unknown = context.roomIds ? items.find(item => !context.roomIds!.includes(item)) : undefined
  return unknown !== undefined ? fail(`Salen "${unknown}" finns inte bland salarna i underlaget.`) : ok([...items].sort())
}

function parseRanges(param: ParameterInfo, draft: unknown): ParseResult {
  const rows = asArray(draft).map(row => ({ start: text(asRecord(row).start), end: text(asRecord(row).end) }))
  const valid = param.value_type === "date_range_list" ? isValidDate : isValidTime
  const noun = param.value_type === "date_range_list" ? "datum (ÅÅÅÅ-MM-DD)" : "klockslag (TT:MM)"
  for (const [index, row] of rows.entries()) {
    if (!valid(row.start) || !valid(row.end)) return fail(`Rad ${index + 1}: ange ett giltigt ${noun} för både start och slut.`)
    if (row.start > row.end) return fail(`Rad ${index + 1}: slutet ligger före början.`)
  }
  return ok(rows)
}

/** Tolkar utkastet till det värde som API:et förväntar sig. */
export function parseDraft(param: ParameterInfo, draft: unknown, context: ParseContext = {}): ParseResult {
  const allowEmpty = param.default === "" || param.default === null || param.value === ""
  switch (param.value_type) {
    case "integer": {
      const input = text(draft)
      if (isMoney(param)) { const kr = parseKrToOre(input); return kr.ok ? ok(kr.ore) : fail(kr.error) }
      return parseInteger(input)
    }
    case "number": {
      const input = text(draft)
      if (isMoney(param)) { const kr = parseKrToOre(input); return kr.ok ? ok(kr.ore) : fail(kr.error) }
      return parseNumber(input)
    }
    case "boolean": return ok(draft === true)
    case "choice": {
      if (!param.choices) return ok(draft)
      return param.choices.some(choice => choice.value === draft) ? ok(draft) : fail("Välj ett av alternativen.")
    }
    case "date": {
      const input = text(draft).trim()
      if (input === "") return allowEmpty ? ok("") : fail("Ange ett datum (ÅÅÅÅ-MM-DD).")
      return isValidDate(input) ? ok(input) : fail("Ange ett giltigt datum, till exempel 2027-01-11.")
    }
    case "time": {
      const input = text(draft).trim()
      if (input === "") return allowEmpty ? ok("") : fail("Ange ett klockslag (TT:MM).")
      return isValidTime(input) ? ok(input) : fail("Ange ett giltigt klockslag, till exempel 08:00.")
    }
    case "time_list": case "integer_list": case "string_list": return parseList(param, draft)
    case "room_id_list": return parseRoomIds(draft, context)
    case "staffing_ladder": {
      const rows = asArray(draft) as LadderRow[]
      const check = validateLadder(rows)
      if (check.error) return fail(check.error)
      return ok(rows.map(row => ({ max_participants: Number(row.max.trim()), required_staff: Number(row.staff.trim()) })))
    }
    case "date_range_list": case "time_range_list": return parseRanges(param, draft)
    default: return fail("Det här värdet kan inte redigeras i gränssnittet.")
  }
}

/** Likhet för tolkade värden. Objektnycklarnas ordning spelar ingen roll. */
export function sameValue(a: unknown, b: unknown): boolean { return stable(a) === stable(b) }

function stable(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>
    return `{${Object.keys(record).sort().map(key => `${JSON.stringify(key)}:${stable(record[key])}`).join(",")}}`
  }
  return JSON.stringify(value) ?? "null"
}

/** Utgångsvärdet i jämförbar form: samma tolkning som ett utkast går igenom, så att "08:00, 14:00" och "14:00, 08:00" är lika. */
export function baselineValue(param: ParameterInfo): unknown {
  if (!hasEditor(param.value_type)) return param.value
  const parsed = parseDraft(param, toDraft(param))
  return parsed.ok ? parsed.value : param.value
}
