import { useMemo, useState } from "react"
import { Search } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { ParameterInfo } from "@/lib/jointTypes"
import { filterParameters, groupParameters, lockedParameters, type ParamChange } from "@/lib/paramDiff"
import type { ParameterEditor } from "@/lib/useParameterEditor"
import { ParamRow, type OptionsContext } from "./param-row"

type Props = { editor: ParameterEditor; optionsContext: OptionsContext; changeById: Map<string, ParamChange>; exclude?: ParameterInfo[] }

/** De övriga parametrarna grupperade, med sökning och avancerade parametrar bakom en knapp. `exclude` är de som redan visas överst. */
export function ParamList({ editor, optionsContext, changeById, exclude = [] }: Props) {
  const [query, setQuery] = useState("")
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [showLocked, setShowLocked] = useState(false)
  const skip = useMemo(() => new Set(exclude.map(param => param.id)), [exclude])
  const params = useMemo(() => editor.params.filter(param => !skip.has(param.id)), [editor.params, skip])
  const changed = useMemo(() => new Set(editor.changes.map(change => change.id)), [editor.changes])
  const visible = useMemo(() => filterParameters(params, { query, showAdvanced, showLocked, keep: changed, groupLabels: editor.groupMeta.labels, options: editor.options }), [params, editor.options, query, showAdvanced, showLocked, changed, editor.groupMeta])
  const groups = useMemo(() => groupParameters(visible, editor.groupMeta), [visible, editor.groupMeta])
  const advancedCount = params.filter(param => param.advanced && param.editable).length
  const lockedCount = lockedParameters(params, editor.options).length

  return <div className="space-y-3">
    <div className="flex flex-wrap items-end gap-4">
      <div className="min-w-[16rem] flex-1">
        <label htmlFor="param-search" className="label">Sök parameter</label>
        <div className="relative"><Search size={15} className="pointer-events-none absolute left-2.5 top-2.5 text-slate-700" aria-hidden="true"/>
          <input id="param-search" type="search" className="field !pl-8" placeholder="Namn, id eller del av hjälptexten" value={query} onChange={event => setQuery(event.target.value)}/></div>
      </div>
      <label className="flex items-center gap-2 pb-2 text-sm"><input type="checkbox" checked={showAdvanced} onChange={event => setShowAdvanced(event.target.checked)}/>Visa avancerade{advancedCount ? ` (${advancedCount})` : ""}</label>
      <label className="flex items-center gap-2 pb-2 text-sm"><input type="checkbox" checked={showLocked} onChange={event => setShowLocked(event.target.checked)}/>Visa parametrar som inte kan ändras ({lockedCount})</label>
    </div>
    {groups.length === 0 && <p className="rounded-md bg-slate-100 p-3 text-sm text-slate-900">Ingen parameter matchar sökningen.</p>}
    {groups.map(({ group, label, items }) => <Card key={group}>
      <CardHeader><CardTitle>{label}</CardTitle></CardHeader>
      <CardContent><div className="divide-y divide-slate-200">
        {items.map(param => <ParamRow key={param.id} param={param} draft={editor.draftFor(param)} change={changeById.get(param.id)} error={editor.errors[param.id]}
          onChange={draft => editor.setDraft(param, draft)} onReset={() => editor.reset(param.id)} optionsContext={optionsContext}/>)}
      </div></CardContent>
    </Card>)}
  </div>
}
