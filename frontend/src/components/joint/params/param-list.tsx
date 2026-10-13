import { useMemo, useState } from "react"
import { Search } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { filterParameters, groupParameters, lockedParameters } from "@/lib/paramDiff"
import type { ParameterEditor } from "@/lib/useParameterEditor"
import { ChangesBar } from "./changes-bar"
import { ParamRow, type OptionsContext } from "./param-row"

/** Parametrarna grupperade, med sökning, avancerade parametrar bakom en knapp och ändringsfältet överst. */
export function ParamList({ editor, onOpenUnderlay }: { editor: ParameterEditor; onOpenUnderlay: () => void }) {
  const [query, setQuery] = useState("")
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [showLocked, setShowLocked] = useState(false)
  const changed = useMemo(() => new Set(editor.changes.map(change => change.id)), [editor.changes])
  const visible = useMemo(() => filterParameters(editor.params, { query, showAdvanced, showLocked, keep: changed, groupLabels: editor.groupMeta.labels, options: editor.options }), [editor.params, editor.options, query, showAdvanced, showLocked, changed, editor.groupMeta])
  const groups = useMemo(() => groupParameters(visible, editor.groupMeta), [visible, editor.groupMeta])
  const advancedCount = editor.params.filter(param => param.advanced && param.editable).length
  const lockedCount = lockedParameters(editor.params, editor.options).length
  const changeById = useMemo(() => new Map(editor.changes.map(change => [change.id, change])), [editor.changes])

  const optionsContext = useMemo<OptionsContext>(() => ({ load: editor.optionsLoad, options: editor.options, onOpenUnderlay, onRetry: editor.reloadOptions }),
    [editor.optionsLoad, editor.options, onOpenUnderlay, editor.reloadOptions])

  const jump = (id: string) => {
    const target = document.querySelector<HTMLElement>(`[data-param-id="${CSS.escape(id)}"]`)
    if (!target) { setQuery(""); setShowAdvanced(true); return }
    target.scrollIntoView({ block: "center" })
    target.querySelector<HTMLElement>("input, select, button")?.focus({ preventScroll: true })
  }

  return <div className="space-y-3">
    <div id="changes-bar"><ChangesBar changes={editor.changes} errors={editor.errors} onReset={editor.reset} onResetAll={editor.resetAll} onJump={jump}/></div>
    {editor.generalErrors.length > 0 && <div role="alert" className="rounded-md border-2 border-red-700 bg-red-50 p-3 text-sm text-red-900">
      <strong>Servern avvisade körningen:</strong>
      <ul className="mt-1 list-disc pl-5">{editor.generalErrors.map(message => <li key={message}>{message}</li>)}</ul>
    </div>}
    <div className="flex flex-wrap items-end gap-4">
      <div className="min-w-[16rem] flex-1">
        <label htmlFor="param-search" className="label">Sök parameter</label>
        <div className="relative"><Search size={15} className="pointer-events-none absolute left-2.5 top-2.5 text-slate-700" aria-hidden="true"/>
          <input id="param-search" type="search" className="field !pl-8" placeholder="Namn, id eller del av hjälptexten" value={query} onChange={event => setQuery(event.target.value)}/></div>
      </div>
      <label className="flex items-center gap-2 pb-2 text-sm"><input type="checkbox" checked={showAdvanced} onChange={event => setShowAdvanced(event.target.checked)}/>Visa avancerade{advancedCount ? ` (${advancedCount})` : ""}</label>
      <label className="flex items-center gap-2 pb-2 text-sm"><input type="checkbox" checked={showLocked} onChange={event => setShowLocked(event.target.checked)}/>Visa parametrar som inte kan ändras ({lockedCount})</label>
    </div>
    <p className="text-xs text-slate-800" role="status" aria-live="polite">{visible.length} av {editor.params.length} parametrar visas.</p>
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
