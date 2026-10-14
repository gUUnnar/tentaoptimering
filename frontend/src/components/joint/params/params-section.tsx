import { useCallback, useMemo, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { InfoTip } from "@/components/ui/info-tip"
import { featuredParameters, otherParameters } from "@/lib/featuredParams"
import type { ParameterEditor } from "@/lib/useParameterEditor"
import { ChangesBar } from "./changes-bar"
import { ParamList } from "./param-list"
import { ParamRow, type OptionsContext } from "./param-row"

/**
 * Parametrarna: de vanligaste överst och direkt ändringsbara, resten under "Fler parametrar" (grupperade, med sökning).
 * Ändringarna listas bara när det finns några.
 */
export function ParamsSection({ editor, onOpenUnderlay }: { editor: ParameterEditor; onOpenUnderlay: () => void }) {
  const [moreOpen, setMoreOpen] = useState(false)
  const featured = useMemo(() => featuredParameters(editor.params), [editor.params])
  const rest = useMemo(() => otherParameters(editor.params), [editor.params])
  const changeById = useMemo(() => new Map(editor.changes.map(change => [change.id, change])), [editor.changes])
  const optionsContext = useMemo<OptionsContext>(() => ({ load: editor.optionsLoad, options: editor.options, onOpenUnderlay, onRetry: editor.reloadOptions }),
    [editor.optionsLoad, editor.options, onOpenUnderlay, editor.reloadOptions])

  const focusRow = useCallback((id: string): boolean => {
    const target = document.querySelector<HTMLElement>(`[data-param-id="${CSS.escape(id)}"]`)
    if (!target) return false
    target.scrollIntoView({ block: "center" })
    target.querySelector<HTMLElement>("input, select, button")?.focus({ preventScroll: true })
    return true
  }, [])
  const jump = (id: string) => {
    if (focusRow(id)) return
    setMoreOpen(true)
    window.setTimeout(() => focusRow(id), 50)
  }

  return <div className="space-y-3">
    <div id="changes-bar"><ChangesBar changes={editor.changes} errors={editor.errors} onReset={editor.reset} onResetAll={editor.resetAll} onJump={jump}/></div>
    {editor.generalErrors.length > 0 && <div role="alert" className="rounded-md border border-red-700 bg-red-50 p-3 text-sm text-red-900">
      <strong>Servern avvisade körningen:</strong>
      <ul className="mt-1 list-disc pl-5">{editor.generalErrors.map(message => <li key={message}>{message}</li>)}</ul>
    </div>}
    {featured.length > 0 && <Card><CardContent className="divide-y divide-slate-200 pt-4">
      {featured.map(param => <ParamRow key={param.id} param={param} draft={editor.draftFor(param)} change={changeById.get(param.id)} error={editor.errors[param.id]}
        onChange={draft => editor.setDraft(param, draft)} onReset={() => editor.reset(param.id)} optionsContext={optionsContext}/>)}
    </CardContent></Card>}
    {rest.length > 0 && <details open={moreOpen} onToggle={event => setMoreOpen((event.currentTarget as HTMLDetailsElement).open)} className="rounded-lg border bg-white">
      <summary className="cursor-pointer p-3 text-base font-bold">Fler parametrar ({rest.length})</summary>
      <div className="p-3 pt-0"><ParamList editor={editor} exclude={featured} optionsContext={optionsContext} changeById={changeById}/></div>
    </details>}
  </div>
}

/** Rubriken för parametrarna, med förklaringen bakom en ikon. */
export function ParamsHeading() {
  return <h2 className="flex items-center gap-1.5">Parametrar
    <InfoTip label="Om ändringar">Det du ändrar gäller bara den här körningen och ändrar aldrig originalscenariot. Du kan spara dina ändringar som ett nytt scenario under Körningsinställningar.</InfoTip></h2>
}
