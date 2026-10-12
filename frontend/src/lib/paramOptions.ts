import type { DigitalSupport, ExamTypeOption, JointOptions, ParameterInfo, RoomOption } from "./jointTypes.ts"
import { NO_ROOMS_DRAFT, type ParseContext } from "./paramValues.ts"

// Parametrar vars värden väljs bland det som finns i underlaget: salar (rooms.selection) och flyttbara tentamenstyper
// (flex.movable_types). Här ligger den rena logiken; kryssrutorna ligger i components/joint/params/.

export type OptionsLoad = { status: "idle" | "loading" | "ready" | "error"; error: string; data: JointOptions | null }

/** Alternativen som går att välja bland, eller null när de saknas (laddar, fel eller underlaget inte förberett). */
export const availableOptions = (load: OptionsLoad): JointOptions | null => load.data?.data_available ? load.data : null

export const MOVABLE_TYPES_ID = "flex.movable_types"

export type OptionKind = "rooms" | "types"

export const optionKind = (param: Pick<ParameterInfo, "id" | "value_type">): OptionKind | null =>
  param.value_type === "room_id_list" ? "rooms" : param.id === MOVABLE_TYPES_ID ? "types" : null

/** Parametrar som bara går att ändra när alternativen finns. */
export const needsOptions = (param: Pick<ParameterInfo, "id" | "value_type">): boolean => optionKind(param) !== null

export const parseContext = (options: JointOptions | null | undefined): ParseContext => options ? { roomIds: options.rooms.map(room => room.room_id) } : {}

const strings = (draft: unknown): string[] => Array.isArray(draft) ? draft.map(String) : []
const sameSet = (a: readonly string[], b: readonly string[]): boolean => a.length === b.length && a.every(item => b.includes(item))

// ---- Salar -----------------------------------------------------------------------------------------------------------

/** Vilka salar som är markerade, i alternativens ordning. Tom lista betyder alla; "ingen sal" ger en tom markering. */
export function selectedRoomIds(draft: unknown, rooms: readonly RoomOption[]): string[] {
  const list = strings(draft)
  if (list.includes(NO_ROOMS_DRAFT)) return []
  if (list.length === 0) return rooms.map(room => room.room_id)
  return rooms.filter(room => list.includes(room.room_id)).map(room => room.room_id)
}

/**
 * Utkastet för en ny markering. Alla markerade ger tom lista (alla salar), ingen markerad ger "ingen sal" (ett fel), annars listan.
 * Är markeringen samma som den ursprungliga returneras det ursprungliga utkastet oförändrat.
 */
export function roomsDraft(rooms: readonly RoomOption[], chosen: readonly string[], original: unknown): string[] {
  const picked = rooms.filter(room => chosen.includes(room.room_id)).map(room => room.room_id)
  if (sameSet(picked, selectedRoomIds(original, rooms))) return strings(original)
  if (picked.length === 0) return [NO_ROOMS_DRAFT]
  return picked.length === rooms.length ? [] : picked
}

/** Sal-id:n i utkastet som inte finns i underlaget. */
export const unknownRoomIds = (draft: unknown, rooms: readonly RoomOption[]): string[] =>
  strings(draft).filter(id => id !== NO_ROOMS_DRAFT && !rooms.some(room => room.room_id === id))

export type RoomGroup = { key: string; title: string; rooms: RoomOption[] }

/** Salarna per byggnad, i den ordning byggnaderna först förekommer. */
export function groupRooms(rooms: readonly RoomOption[]): RoomGroup[] {
  const groups = new Map<string, RoomGroup>()
  for (const room of rooms) {
    const key = `${room.building_id ?? ""}|${room.address ?? ""}`
    let group = groups.get(key)
    if (!group) {
      const title = room.address ?? room.building_id ?? "Byggnad saknas i underlaget"
      group = { key, title, rooms: [] }
      groups.set(key, group)
    }
    group.rooms.push(room)
  }
  return [...groups.values()]
}

const seats = (rooms: readonly RoomOption[]): number => rooms.reduce((sum, room) => sum + (room.capacity ?? 0), 0)

export type RoomSummary = { count: number; total: number; seats: number; all: boolean; none: boolean; text: string }

export function roomSummary(rooms: readonly RoomOption[], selected: readonly string[]): RoomSummary {
  const chosen = rooms.filter(room => selected.includes(room.room_id))
  const all = rooms.length > 0 && chosen.length === rooms.length
  const platser = seats(chosen)
  const text = all ? `Alla salar (${rooms.length} salar, ${platser} platser)` : `${chosen.length} av ${rooms.length} salar valda, ${platser} platser`
  return { count: chosen.length, total: rooms.length, seats: platser, all, none: chosen.length === 0, text }
}

export const groupSummary = (group: RoomGroup, selected: readonly string[]): string =>
  `${group.rooms.filter(room => selected.includes(room.room_id)).length} av ${group.rooms.length} valda`

const DIGITAL_TEXT: Record<DigitalSupport, string> = { all: "alla platser", partial: "delvis", none: "nej", unknown: "okänt" }
export const digitalText = (digital: DigitalSupport): string => `Digital: ${DIGITAL_TEXT[digital] ?? DIGITAL_TEXT.unknown}`

// ---- Flyttbara tentamenstyper ----------------------------------------------------------------------------------------

/** Orden i parameterns värde, i gemener. Backend matchar dem som delsträng mot tentans typ. */
export const typeWords = (draft: unknown): string[] => strings(draft).map(word => word.trim().toLowerCase()).filter(Boolean)

const matches = (type: ExamTypeOption, words: readonly string[]): boolean => words.some(word => type.value.includes(word))

/** Typerna (deras `value`) som något ord i värdet träffar. */
export const selectedTypeValues = (draft: unknown, types: readonly ExamTypeOption[]): string[] =>
  types.filter(type => matches(type, typeWords(draft))).map(type => type.value)

/** Ord i värdet som inte träffar någon typ i underlaget. De försvinner om användaren ändrar valet. */
export const unmatchedWords = (draft: unknown, types: readonly ExamTypeOption[]): string[] =>
  typeWords(draft).filter(word => !types.some(type => type.value.includes(word)))

/** Utkastet för en ny markering: `value` för varje markerad typ. Är markeringen samma som den ursprungliga behålls det ursprungliga värdet oförändrat. */
export function typesDraft(types: readonly ExamTypeOption[], chosen: readonly string[], original: unknown): string[] {
  const picked = types.filter(type => chosen.includes(type.value)).map(type => type.value)
  return sameSet(picked, selectedTypeValues(original, types)) ? strings(original) : picked
}

export const typeLabel = (type: ExamTypeOption): string => `${type.label} (${type.count})`

/** Typerna som är flyttbara i standardläget (parameterns standardvärde), som etiketter. */
export const defaultMovableLabels = (param: Pick<ParameterInfo, "default">, types: readonly ExamTypeOption[]): string[] =>
  types.filter(type => matches(type, typeWords(param.default))).map(type => type.label)
