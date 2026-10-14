import type { ParameterInfo } from "./jointTypes.ts"

/**
 * De parametrar som visas överst och direkt går att ändra, i den ordning de visas. Övriga ligger under "Fler parametrar".
 * Det är en rent visuell prioritering: alla parametrar är oförändrat tillgängliga, och bara sådana som finns i katalogen visas.
 */
export const FEATURED_PARAM_IDS: readonly string[] = [
  "wish.candidate_policy",
  "wish.tiebreak",
  "window.earlier_days",
  "window.later_days",
  "flex.movable_types",
  "calendar.weekdays",
  "calendar.start_times",
  "rooms.selection",
  "rooms.include_observed_unregistered",
  "demand.variation_pct",
  "cost.room_annual_per_seat_ore",
  "cost.staff_annual_ore",
  "solver.time_limit_seconds",
]

const FEATURED = new Set(FEATURED_PARAM_IDS)

export const isFeatured = (id: string): boolean => FEATURED.has(id)

/** De utvalda parametrarna som finns i listan, i fast ordning. */
export function featuredParameters(params: ParameterInfo[]): ParameterInfo[] {
  const byId = new Map(params.map(param => [param.id, param]))
  return FEATURED_PARAM_IDS.flatMap(id => byId.has(id) ? [byId.get(id) as ParameterInfo] : [])
}

/** Parametrarna som inte är utvalda, i sin ursprungliga ordning. */
export const otherParameters = (params: ParameterInfo[]): ParameterInfo[] => params.filter(param => !FEATURED.has(param.id))
