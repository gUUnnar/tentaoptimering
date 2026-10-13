import { Plus, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { ParameterInfo } from "@/lib/jointTypes"
import { WEEKDAYS, isWeekdayParam, type RangeRow } from "@/lib/paramValues"
import { cn } from "@/lib/utils"

type ListProps = { param: ParameterInfo; draft: unknown; onChange: (draft: unknown) => void; disabled: boolean; label: string; describedBy?: string }

const asStrings = (draft: unknown): string[] => Array.isArray(draft) ? draft.map(String) : []
const asRanges = (draft: unknown): RangeRow[] => Array.isArray(draft) ? draft as RangeRow[] : []

function ToggleButtons({ options, selected, onToggle, disabled, label, describedBy }: {
  options: { value: string; label: string }[]; selected: string[]; onToggle: (value: string) => void; disabled: boolean; label: string; describedBy?: string
}) {
  return <div role="group" aria-label={label} aria-describedby={describedBy} className="flex flex-wrap gap-1.5">
    {options.map(option => {
      const on = selected.includes(option.value)
      return <button key={option.value} type="button" aria-pressed={on} disabled={disabled} onClick={() => onToggle(option.value)}
        className={cn("min-w-[4.5rem] rounded-md border-2 px-2.5 py-1.5 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700 disabled:cursor-not-allowed disabled:opacity-60",
          on ? "border-sky-800 bg-sky-800 text-white" : "border-slate-500 bg-white text-slate-900 hover:bg-slate-50")}>
        <span aria-hidden="true">{on ? "✓ " : ""}</span>{option.label}
      </button>
    })}
  </div>
}

function toggled(list: string[], value: string): string[] { return list.includes(value) ? list.filter(item => item !== value) : [...list, value] }

/** Listor med fasta alternativ (veckodagar eller alternativ från katalogen) som markerbara knappar. */
export function ChoiceListInput({ param, draft, onChange, disabled, label, describedBy }: ListProps) {
  const options = param.choices
    ? param.choices.map(choice => ({ value: String(choice.value), label: choice.label }))
    : WEEKDAYS.map(day => ({ value: String(day.value), label: day.label }))
  return <ToggleButtons options={options} selected={asStrings(draft)} disabled={disabled} label={label} describedBy={describedBy}
    onToggle={value => onChange(toggled(asStrings(draft), value))}/>
}

export const usesToggleButtons = (param: ParameterInfo): boolean =>
  (param.value_type === "integer_list" || param.value_type === "string_list") && (isWeekdayParam(param) || !!param.choices)

/** Lätt listinmatning: en rad per värde med ta bort-knapp och en knapp för att lägga till. Starttider väljs med tidsfält. */
export function ValueListInput({ param, draft, onChange, disabled, label, describedBy }: ListProps) {
  const items = asStrings(draft)
  const isTime = param.value_type === "time_list"
  const noun = isTime ? "tid" : "värde"
  const set = (next: string[]) => onChange(next)
  return <div className="space-y-1.5" role="group" aria-label={label} aria-describedby={describedBy}>
    {items.length === 0 && <p className="text-sm text-slate-800">Listan är tom.</p>}
    {items.map((item, index) => <div key={index} className="flex items-center gap-2">
      <input className="field max-w-[10rem]" type={isTime ? "time" : "text"} aria-label={`${label}, ${noun} ${index + 1}`} value={item} disabled={disabled}
        onChange={event => set(items.map((existing, i) => i === index ? event.target.value : existing))}/>
      <Button type="button" size="sm" variant="outline" disabled={disabled} aria-label={`Ta bort ${noun} ${index + 1}: ${item || "tomt"}`} onClick={() => set(items.filter((_, i) => i !== index))}><X size={14} aria-hidden="true"/><span className="ml-1">Ta bort</span></Button>
    </div>)}
    <Button type="button" size="sm" variant="outline" disabled={disabled} onClick={() => set([...items, ""])}><Plus size={14} className="mr-1" aria-hidden="true"/>Lägg till {noun}</Button>
  </div>
}

/** Perioder (datum eller klockslag): en rad med från och till per period. */
export function RangeListInput({ param, draft, onChange, disabled, label, describedBy }: ListProps) {
  const rows = asRanges(draft)
  const type = param.value_type === "date_range_list" ? "date" : "time"
  const set = (next: RangeRow[]) => onChange(next)
  const update = (index: number, patch: Partial<RangeRow>) => set(rows.map((row, i) => i === index ? { ...row, ...patch } : row))
  return <div className="space-y-1.5" role="group" aria-label={label} aria-describedby={describedBy}>
    {rows.length === 0 && <p className="text-sm text-slate-800">Inga perioder.</p>}
    {rows.map((row, index) => <div key={index} className="flex flex-wrap items-center gap-2">
      <input className="field max-w-[10rem]" type={type} aria-label={`${label}, period ${index + 1}, från`} value={row.start} disabled={disabled} onChange={event => update(index, { start: event.target.value })}/>
      <span aria-hidden="true">–</span>
      <input className="field max-w-[10rem]" type={type} aria-label={`${label}, period ${index + 1}, till`} value={row.end} disabled={disabled} onChange={event => update(index, { end: event.target.value })}/>
      <Button type="button" size="sm" variant="outline" disabled={disabled} aria-label={`Ta bort period ${index + 1}`} onClick={() => set(rows.filter((_, i) => i !== index))}><X size={14} aria-hidden="true"/><span className="ml-1">Ta bort</span></Button>
    </div>)}
    <Button type="button" size="sm" variant="outline" disabled={disabled} onClick={() => set([...rows, { start: "", end: "" }])}><Plus size={14} className="mr-1" aria-hidden="true"/>Lägg till period</Button>
  </div>
}
