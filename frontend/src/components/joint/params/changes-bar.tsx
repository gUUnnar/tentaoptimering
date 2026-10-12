import { ArrowRight, CircleAlert, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { ParamChange } from "@/lib/paramDiff"

type Props = { changes: ParamChange[]; errors: Record<string, string>; onReset: (id: string) => void; onResetAll: () => void; onJump: (id: string) => void }

/** Fast fält högst upp: hur många ändringar som gjorts jämfört med scenariot, och vilka. */
export function ChangesBar({ changes, errors, onReset, onResetAll, onJump }: Props) {
  const errorCount = Object.keys(errors).length
  const count = changes.length
  return <section aria-label="Ändringar jämfört med scenariot" className="sticky top-0 z-10 rounded-lg border-2 border-slate-300 bg-white p-3 shadow-md">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <p role="status" aria-live="polite" className="text-sm font-semibold text-slate-900">
        {count === 0 ? "Inga ändringar jämfört med scenariot" : `${count} ${count === 1 ? "ändring" : "ändringar"} jämfört med scenariot`}
        {errorCount > 0 && <span className="ml-3 inline-flex items-center gap-1 font-medium text-red-800"><CircleAlert size={15} aria-hidden="true"/>{errorCount} fel att rätta</span>}
      </p>
      {count > 0 && <Button type="button" size="sm" variant="outline" onClick={onResetAll}><RotateCcw size={13} className="mr-1" aria-hidden="true"/>Återställ alla</Button>}
    </div>
    {count > 0 && <ul className="mt-2 max-h-40 space-y-1 overflow-auto text-xs text-slate-900" aria-label="Ändrade parametrar">
      {changes.map(change => <li key={change.id} className="flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-slate-200 pt-1">
        <button type="button" onClick={() => onJump(change.id)} className="rounded font-semibold text-sky-900 underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-700">{change.label}</button>
        <span>{change.oldText}</span><ArrowRight size={12} aria-hidden="true"/><span className="sr-only">till</span>
        <strong className={errors[change.id] ? "text-red-800" : undefined}>{change.newText}</strong>
        <button type="button" onClick={() => onReset(change.id)} aria-label={`Återställ ${change.label}`} className="ml-auto rounded px-1 text-sky-900 underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-700">Återställ</button>
      </li>)}
    </ul>}
  </section>
}
