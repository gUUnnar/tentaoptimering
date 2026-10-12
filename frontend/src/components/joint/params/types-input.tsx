import type { JointOptions, ParameterInfo } from "@/lib/jointTypes"
import { defaultMovableLabels, selectedTypeValues, typeLabel, typesDraft, unmatchedWords } from "@/lib/paramOptions"
import { toDraft } from "@/lib/paramValues"

type Props = { param: ParameterInfo; draft: unknown; onChange: (draft: unknown) => void; disabled: boolean; label: string; describedBy?: string; options: JointOptions }

/** Tentamenstyper som får flyttas, som kryssrutor över de typer som finns i underlaget. */
export function MovableTypesInput({ param, draft, onChange, disabled, label, describedBy, options }: Props) {
  const types = options.exam_types
  const selected = selectedTypeValues(draft, types)
  const unmatched = unmatchedWords(draft, types)
  const defaults = defaultMovableLabels(param, types)
  const toggle = (value: string) => onChange(typesDraft(types, selected.includes(value) ? selected.filter(item => item !== value) : [...selected, value], toDraft(param)))
  return <div role="group" aria-label={label} aria-describedby={describedBy} className="space-y-2">
    <p className="text-sm text-slate-900">Flyttbara tentor får ligga på ett annat pass eller en annan dag. Övriga behåller sin tid.</p>
    <ul className="grid gap-x-4 gap-y-0.5 sm:grid-cols-2">
      {types.map(type => <li key={type.value}>
        <label className="flex items-center gap-2 rounded px-1 py-1 text-sm hover:bg-slate-50">
          <input type="checkbox" checked={selected.includes(type.value)} disabled={disabled} onChange={() => toggle(type.value)}/>{typeLabel(type)}
        </label>
      </li>)}
    </ul>
    {types.length === 0 && <p className="text-sm text-slate-800">Underlaget innehåller inga tentamenstyper.</p>}
    {selected.length === 0 && types.length > 0 && <p className="text-xs text-amber-950">Ingen typ är flyttbar: alla tentor behåller sin tid.</p>}
    <p className="text-xs text-slate-800">I standardläget är {defaults.length ? defaults.join(", ") : "inga typer"} flyttbara.</p>
    {unmatched.length > 0 && <p className="text-xs text-slate-800">Orden {unmatched.map(word => `"${word}"`).join(", ")} träffar ingen typ i underlaget och tas bort om du ändrar valet.</p>}
  </div>
}
