import type { ParameterInfo } from "./jointTypes.ts"
import { formatWithUnit } from "./paramUnits.ts"
import { WEEKDAYS, isWeekdayParam } from "./paramValues.ts"

type Describable = Pick<ParameterInfo, "id" | "value_type" | "unit" | "choices">

const EMPTY = "(tomt)"
const asArray = (value: unknown): unknown[] => Array.isArray(value) ? value : []
const rec = (value: unknown): Record<string, unknown> => value && typeof value === "object" ? value as Record<string, unknown> : {}

/** Ett parametervärde i klartext för ändringslistor och skrivskyddad visning. */
export function formatParamValue(param: Describable, value: unknown): string {
  if (value === null || value === undefined || value === "") return EMPTY
  switch (param.value_type) {
    case "boolean": return value === true ? "Ja" : "Nej"
    case "choice": return param.choices?.find(choice => choice.value === value)?.label ?? String(value)
    case "integer": case "number": return typeof value === "number" ? formatWithUnit(value, param.unit) : String(value)
    case "integer_list": {
      const items = asArray(value)
      if (isWeekdayParam(param)) {
        if (items.length === 7) return "Alla veckodagar"
        return items.length ? items.map(item => WEEKDAYS.find(day => day.value === item)?.short ?? String(item)).join(", ") : "Inga veckodagar"
      }
      return items.length ? items.join(", ") : "(tom lista)"
    }
    case "time_list": case "string_list": {
      const items = asArray(value)
      if (!items.length) return "(tom lista)"
      return items.map(item => param.choices?.find(choice => choice.value === item)?.label ?? String(item)).join(", ")
    }
    case "staffing_ladder": {
      const rows = asArray(value).map(rec)
      return rows.length ? rows.map(row => `upp till ${row.max_participants} deltagare: ${row.required_staff} ${row.required_staff === 1 ? "vakt" : "vakter"}`).join("; ") : "(tom trappa)"
    }
    case "date_range_list": case "time_range_list": {
      const rows = asArray(value).map(rec)
      return rows.length ? rows.map(row => `${row.start}–${row.end}`).join("; ") : "(inga perioder)"
    }
    default: {
      if (typeof value === "string") return value
      const json = JSON.stringify(value)
      return json.length > 120 ? `${json.slice(0, 117)}…` : json
    }
  }
}

type Loose = Pick<ParameterInfo, "id" | "unit">

/** För värden där typen inte följer med (jämförelsens ändringslista): typen avläses av värdet. */
export function formatLooseValue(param: Loose, value: unknown): string {
  const first = Array.isArray(value) ? rec(value[0]) : {}
  const valueType: ParameterInfo["value_type"] =
    typeof value === "boolean" ? "boolean"
      : typeof value === "number" ? "number"
        : Array.isArray(value) && "max_participants" in first ? "staffing_ladder"
          : Array.isArray(value) && "start" in first ? "date_range_list"
            : Array.isArray(value) && value.length && value.every(item => typeof item === "number") ? "integer_list"
              : Array.isArray(value) ? "string_list" : "string"
  return formatParamValue({ id: param.id, unit: param.unit, value_type: valueType, choices: null }, value)
}
