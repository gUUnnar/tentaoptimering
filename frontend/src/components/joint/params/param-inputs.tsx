import type { ParameterInfo } from "@/lib/jointTypes"
import { unitInfo } from "@/lib/paramUnits"
import { cn } from "@/lib/utils"

type InputProps = {
  param: ParameterInfo
  draft: unknown
  onChange: (draft: unknown) => void
  disabled: boolean
  inputId: string
  describedBy?: string
  invalid: boolean
}

/** Enkla värden: tal, ja/nej, val, datum och klockslag. Belopp skrivs i kronor. */
export function ScalarInput({ param, draft, onChange, disabled, inputId, describedBy, invalid }: InputProps) {
  const unit = unitInfo(param.unit)
  switch (param.value_type) {
    case "boolean": {
      const on = draft === true
      return <button type="button" role="switch" id={inputId} aria-checked={on} aria-describedby={describedBy} disabled={disabled} onClick={() => onChange(!on)}
        className={cn("inline-flex h-8 items-center gap-2 rounded-full border-2 px-1 pr-3 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700 disabled:cursor-not-allowed disabled:opacity-60",
          on ? "border-sky-800 bg-sky-800 text-white" : "border-slate-500 bg-white text-slate-900")}>
        <span aria-hidden="true" className={cn("h-5 w-5 rounded-full", on ? "bg-white" : "bg-slate-500")}/>
        {on ? "På" : "Av"}
      </button>
    }
    case "choice": {
      const choices = param.choices ?? []
      const index = choices.findIndex(choice => choice.value === draft)
      return <select id={inputId} className="field" value={index < 0 ? "" : String(index)} disabled={disabled} aria-invalid={invalid} aria-describedby={describedBy}
        onChange={event => onChange(choices[Number(event.target.value)]?.value)}>
        {index < 0 && <option value="">Välj …</option>}
        {choices.map((choice, i) => <option key={i} value={String(i)}>{choice.label}</option>)}
      </select>
    }
    case "date": case "time":
      return <input id={inputId} className="field" type={param.value_type} value={typeof draft === "string" ? draft : ""} disabled={disabled}
        aria-invalid={invalid} aria-describedby={describedBy} onChange={event => onChange(event.target.value)}/>
    default: {
      const decimals = param.value_type === "number" || unit.money
      return <div className="flex items-center gap-2">
        <input id={inputId} className="field max-w-[12rem] text-right tabular-nums" type="text" inputMode={decimals ? "decimal" : "numeric"} autoComplete="off"
          value={typeof draft === "string" ? draft : ""} disabled={disabled} aria-invalid={invalid} aria-describedby={describedBy} onChange={event => onChange(event.target.value)}/>
        {unit.label && <span className="text-sm text-slate-800">{unit.label}</span>}
      </div>
    }
  }
}
