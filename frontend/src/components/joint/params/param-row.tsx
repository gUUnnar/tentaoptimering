import { useId } from "react"
import { ArrowRight, CircleAlert, Lock, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { ParameterInfo } from "@/lib/jointTypes"
import type { ParamChange } from "@/lib/paramDiff"
import { formatParamValue } from "@/lib/paramFormat"
import { hasEditor } from "@/lib/paramValues"
import { cn } from "@/lib/utils"
import { ChoiceListInput, RangeListInput, ValueListInput, usesToggleButtons } from "./list-inputs"
import { ScalarInput } from "./param-inputs"
import { StaffingLadderInput } from "./staffing-ladder"

const BASIS_TEXT: Record<string, string> = {
  verified: "Verifierat underlag", source_data: "Från källdata", assumption: "Antagande", experiment: "Experimentvärde",
}
const SCALAR_TYPES: ReadonlySet<string> = new Set(["integer", "number", "boolean", "choice", "date", "time"])
export const LOCKED_TEXT = "Finns i modellen men påverkar inget än"

type RowProps = {
  param: ParameterInfo
  draft: unknown
  change: ParamChange | undefined
  error: string | undefined
  onChange: (draft: unknown) => void
  onReset: () => void
}

function Editor({ param, draft, onChange, disabled, label, inputId, describedBy, invalid }: {
  param: ParameterInfo; draft: unknown; onChange: (draft: unknown) => void; disabled: boolean; label: string; inputId: string; describedBy: string; invalid: boolean
}) {
  switch (param.value_type) {
    case "staffing_ladder": return <StaffingLadderInput draft={draft} onChange={onChange} disabled={disabled} label={label} describedBy={describedBy}/>
    case "date_range_list": case "time_range_list": return <RangeListInput param={param} draft={draft} onChange={onChange} disabled={disabled} label={label} describedBy={describedBy}/>
    case "time_list": case "integer_list": case "string_list":
      return usesToggleButtons(param)
        ? <ChoiceListInput param={param} draft={draft} onChange={onChange} disabled={disabled} label={label} describedBy={describedBy}/>
        : <ValueListInput param={param} draft={draft} onChange={onChange} disabled={disabled} label={label} describedBy={describedBy}/>
    default: return <ScalarInput param={param} draft={draft} onChange={onChange} disabled={disabled} inputId={inputId} describedBy={describedBy} invalid={invalid}/>
  }
}

/** En parameterrad: etikett, hjälptext (alltid synlig), inmatning efter typ, ändringsmarkering och fel. */
export function ParamRow({ param, draft, change, error, onChange, onReset }: RowProps) {
  const id = useId()
  const locked = !param.editable
  const editable = hasEditor(param.value_type)
  const scalar = editable && SCALAR_TYPES.has(param.value_type)
  const helpId = `${id}-help`
  const msgId = `${id}-msg`
  const describedBy = [helpId, error ? msgId : "", change ? `${id}-change` : ""].filter(Boolean).join(" ")
  const defaultText = param.differs_from_default ? formatParamValue(param, param.default) : null
  return <div className={cn("grid gap-x-6 gap-y-2 border-l-4 py-3 pl-3 pr-2 md:grid-cols-[minmax(0,1fr)_minmax(0,26rem)]",
    error ? "border-red-700 bg-red-50" : change ? "border-amber-600 bg-amber-50" : "border-transparent", locked && "bg-slate-50")} data-param-id={param.id}>
    <div>
      <div className="flex flex-wrap items-center gap-2">
        {scalar ? <label htmlFor={id} className="text-sm font-semibold text-slate-900">{param.label}</label>
          : <span className="text-sm font-semibold text-slate-900">{param.label}</span>}
        {BASIS_TEXT[param.basis] && <span className="rounded border border-slate-400 px-1.5 py-0.5 text-[11px] text-slate-800">{BASIS_TEXT[param.basis]}</span>}
        {param.advanced && <span className="rounded border border-slate-400 px-1.5 py-0.5 text-[11px] text-slate-800">Avancerad</span>}
        {locked && <span className="inline-flex items-center gap-1 rounded bg-slate-200 px-1.5 py-0.5 text-[11px] font-medium text-slate-900"><Lock size={11} aria-hidden="true"/>{LOCKED_TEXT}</span>}
      </div>
      <p id={helpId} className="mt-1 text-xs text-slate-800">{param.help_text}</p>
      {defaultText && <p className="mt-1 text-xs text-slate-800">Standardvärde: {defaultText}. Scenariot avviker från det.</p>}
      <p className="mt-1 font-mono text-[11px] text-slate-700">{param.id}</p>
    </div>
    <div className="space-y-2">
      {editable
        ? <Editor param={param} draft={draft} onChange={onChange} disabled={locked} label={param.label} inputId={id} describedBy={describedBy} invalid={!!error}/>
        : <div role="group" aria-label={param.label} aria-describedby={helpId} className="rounded-md border border-slate-300 bg-white p-2 text-sm">
          <div className="whitespace-pre-wrap break-words">{formatParamValue(param, param.value)}</div>
          <p className="mt-1 text-xs text-slate-800">Visas bara. Den här typen av värde ({param.value_type}) kan inte ändras i gränssnittet än.</p>
        </div>}
      {error && <p id={msgId} role="alert" className="flex items-start gap-1.5 text-sm text-red-800"><CircleAlert size={16} className="mt-0.5 shrink-0" aria-hidden="true"/>{error}</p>}
      {change && <div id={`${id}-change`} className="flex flex-wrap items-center gap-2 text-xs text-slate-900">
        <strong>Ändrad:</strong>
        <span>{change.oldText}</span><ArrowRight size={13} aria-hidden="true"/><span className="sr-only">till</span><strong>{change.newText}</strong>
        <Button type="button" size="sm" variant="outline" onClick={onReset} aria-label={`Återställ ${param.label} till scenariots värde`}><RotateCcw size={13} className="mr-1" aria-hidden="true"/>Återställ</Button>
      </div>}
    </div>
  </div>
}
