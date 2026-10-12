import type { FieldError, JointOptions, ParameterInfo } from "./jointTypes.ts"
import { formatParamValue } from "./paramFormat.ts"
import { needsOptions, parseContext } from "./paramOptions.ts"
import { baselineValue, hasEditor, parseDraft, sameValue, toDraft } from "./paramValues.ts"

/** Utkast per parameter-id. Saknas ett id är parametern orörd. */
export type EditMap = Record<string, unknown>

export type ParamChange = {
  id: string; label: string; group: string; unit: string | null
  oldValue: unknown; oldText: string
  /** Det tolkade värdet; undefined när utkastet är ogiltigt. */
  newValue: unknown; newText: string
  error: string | null
}

/**
 * Går parametern att ändra här? Modellen måste använda den och gränssnittet ha redigering för typen. Salar och flyttbara tentamenstyper
 * väljs bland det som finns i underlaget och kräver därför `options` (null eller undefined när underlaget eller svaret saknas).
 */
export const isEditable = (param: ParameterInfo, options?: JointOptions | null): boolean =>
  param.editable && hasEditor(param.value_type) && (!needsOptions(param) || !!options)

/** Ändringar jämfört med scenariot. En parameter som skrivits tillbaka till scenariots värde räknas inte som ändrad. */
export function computeChanges(params: ParameterInfo[], edits: EditMap, options?: JointOptions | null): ParamChange[] {
  const context = parseContext(options)
  const changes: ParamChange[] = []
  for (const param of params) {
    if (!(param.id in edits) || !isEditable(param, options)) continue
    const base = baselineValue(param)
    const oldText = formatParamValue(param, base)
    const parsed = parseDraft(param, edits[param.id], context)
    const common = { id: param.id, label: param.label, group: param.group, unit: param.unit, oldValue: base, oldText }
    if (parsed.ok) {
      if (sameValue(parsed.value, base)) continue
      changes.push({ ...common, newValue: parsed.value, newText: formatParamValue(param, parsed.value), error: null })
    } else if (!sameValue(edits[param.id], toDraft(param))) {
      changes.push({ ...common, newValue: undefined, newText: "ogiltigt värde", error: parsed.error })
    }
  }
  return changes
}

/** Värdena som skickas till API:et: bara giltiga ändringar. */
export function changesToRequest(changes: ParamChange[]): Record<string, unknown> {
  return Object.fromEntries(changes.filter(change => change.error === null).map(change => [change.id, change.newValue]))
}

/** Fel som gäller flera parametrar tillsammans. Nycklen är den parameter där felet visas. */
export function crossErrors(params: ParameterInfo[], edits: EditMap): Record<string, string> {
  const effective = (id: string): unknown => {
    const param = params.find(item => item.id === id)
    if (!param) return undefined
    if (id in edits) { const parsed = parseDraft(param, edits[id]); if (parsed.ok) return parsed.value }
    return baselineValue(param)
  }
  const errors: Record<string, string> = {}
  const start = effective("calendar.start_date")
  const end = effective("calendar.end_date")
  if (typeof start === "string" && typeof end === "string" && start && end && start > end) {
    errors["calendar.end_date"] = "Sista datum ligger före första datum."
  }
  return errors
}

export type ErrorMap = Record<string, string>

/** Samlar fel per parameter: eget formatfel, fel mellan parametrar och fel som servern svarat med. Serverfel visas sist. */
export function collectErrors(changes: ParamChange[], cross: ErrorMap, server: ErrorMap): ErrorMap {
  const local: ErrorMap = { ...cross }
  for (const change of changes) if (change.error) local[change.id] = change.error
  return { ...server, ...local }
}

/** Fel från servern (HTTP 422) som en karta, plus sådana som inte hör till någon parameter i listan. */
export function splitServerErrors(errors: FieldError[], params: ParameterInfo[]): { byId: ErrorMap; general: string[] } {
  const known = new Set(params.map(param => param.id))
  const byId: ErrorMap = {}
  const general: string[] = []
  for (const error of errors) {
    if (known.has(error.id)) byId[error.id] = byId[error.id] ? `${byId[error.id]} ${error.message}` : error.message
    else general.push(error.id ? `${error.id}: ${error.message}` : error.message)
  }
  return { byId, general }
}

export type ParamGroup = { group: string; label: string; items: ParameterInfo[] }

export type GroupMeta = { labels?: Record<string, string>; order?: string[] }

/**
 * Grupperar parametrarna. Grupperna följer group_order när backend skickar den, annars den ordning de först förekommer;
 * inom en grupp gäller parameterns order. Grupp-id:t visas som läsbart namn via group_labels.
 */
export function groupParameters(params: ParameterInfo[], meta: GroupMeta = {}): ParamGroup[] {
  const groups = new Map<string, ParameterInfo[]>()
  for (const param of [...params].sort((a, b) => a.order - b.order)) {
    const list = groups.get(param.group) ?? []
    list.push(param)
    groups.set(param.group, list)
  }
  const rank = (id: string) => { const at = meta.order?.indexOf(id) ?? -1; return at < 0 ? Number.MAX_SAFE_INTEGER : at }
  return [...groups].map(([group, items]) => ({ group, label: meta.labels?.[group] ?? group, items }))
    .sort((a, b) => rank(a.group) - rank(b.group)) // stabil sortering: okända grupper behåller sin inbördes ordning
}

export type ParamFilter = {
  query: string; showAdvanced: boolean; keep: ReadonlySet<string>; groupLabels?: Record<string, string>
  /** Visa parametrar som inte går att ändra här: motorn använder dem inte än, eller gränssnittet saknar redigering för typen. Utan val är de bortfiltrerade. */
  showLocked?: boolean
  /** Alternativen ur underlaget; utan dem är salar och flyttbara tentamenstyper låsta. */
  options?: JointOptions | null
}

/** Parametrar som inte går att ändra i gränssnittet: motorn använder dem inte än, eller redigering saknas för typen. */
export const lockedParameters = (params: ParameterInfo[], options?: JointOptions | null): ParameterInfo[] => params.filter(param => !isEditable(param, options))

/**
 * Sökning på namn, id, hjälptext och grupp. Avancerade parametrar döljs om inte "Visa avancerade" är vald, utom de som ändrats.
 * Parametrar som inte går att sätta döljs om inte `showLocked` är sant.
 */
export function filterParameters(params: ParameterInfo[], filter: ParamFilter): ParameterInfo[] {
  const query = filter.query.trim().toLowerCase()
  return params.filter(param => {
    if (!isEditable(param, filter.options) && !filter.showLocked) return false
    if (param.advanced && !filter.showAdvanced && !filter.keep.has(param.id)) return false
    if (!query) return true
    return [param.label, param.id, param.help_text, param.group, filter.groupLabels?.[param.group] ?? ""].some(field => field.toLowerCase().includes(query))
  })
}
