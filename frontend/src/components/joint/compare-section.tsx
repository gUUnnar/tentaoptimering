import { useEffect, useId, useMemo, useState } from "react"
import { ArrowDown, ArrowRight, ArrowUp, CircleCheck, CircleHelp, Info, Minus, TriangleAlert } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { jointApi } from "@/lib/jointApi"
import { NO_PREVIOUS_RUN_TEXT, changeRows, interpretationView, metricRows, type InterpretationView, type MetricRow } from "@/lib/jointCompare"
import { formatKr } from "@/lib/jointFormat"
import type { CompareResult, CompareRunRef, SavedRun } from "@/lib/jointTypes"

type Load = { status: "loading" | "ready" | "error"; result: CompareResult | null; error: string }

const stamp = (ref: CompareRunRef) => `${ref.run_id}${ref.created_at ? ` (${ref.created_at.slice(0, 16).replace("T", " ")})` : ""}`

const TONE: Record<InterpretationView["tone"], { box: string; icon: JSX.Element; label: string }> = {
  interpretable: { box: "border-emerald-700 bg-emerald-50 text-emerald-950", icon: <CircleCheck size={20} aria-hidden="true"/>, label: "Tolkningsbar" },
  not_interpretable: { box: "border-amber-700 bg-amber-50 text-amber-950", icon: <TriangleAlert size={20} aria-hidden="true"/>, label: "Går inte att tolka" },
  unknown: { box: "border-slate-500 bg-slate-100 text-slate-950", icon: <CircleHelp size={20} aria-hidden="true"/>, label: "Kan inte bedömas" },
}

/** Jämförelse av en körning mot föregående körning av samma scenario, eller mot en vald körning. */
export function CompareSection({ runId, runs }: { runId: string; runs: SavedRun[] }) {
  const id = useId()
  const [base, setBase] = useState("previous")
  const [load, setLoad] = useState<Load>({ status: "loading", result: null, error: "" })
  useEffect(() => { setBase("previous") }, [runId])
  useEffect(() => {
    let cancelled = false
    setLoad({ status: "loading", result: null, error: "" })
    jointApi.compare(runId, base)
      .then(result => { if (!cancelled) setLoad({ status: "ready", result, error: "" }) })
      .catch(error => { if (!cancelled) setLoad({ status: "error", result: null, error: (error as Error).message }) })
    return () => { cancelled = true }
  }, [runId, base])

  const others = runs.filter(run => run.run_id !== runId)
  return <Card>
    <CardHeader><CardTitle>Jämförelse med en tidigare körning</CardTitle></CardHeader>
    <CardContent className="space-y-4">
      <div>
        <label className="label" htmlFor={`${id}-base`}>Jämför med</label>
        <select id={`${id}-base`} className="field max-w-xl" value={base} onChange={event => setBase(event.target.value)}>
          <option value="previous">Föregående körning av samma scenario</option>
          {others.map(run => <option key={run.run_id} value={run.run_id}>{run.run_id} · {run.scenario_id}</option>)}
        </select>
      </div>
      <div aria-live="polite">
        {load.status === "loading" && <p className="text-sm text-slate-900" role="status">Hämtar jämförelsen …</p>}
        {load.status === "error" && <p className="flex items-start gap-1.5 rounded-md bg-red-50 p-2 text-sm text-red-900" role="alert"><TriangleAlert size={16} className="mt-0.5 shrink-0" aria-hidden="true"/>Kunde inte hämta jämförelsen: {load.error}</p>}
        {load.status === "ready" && load.result && (load.result.base === null
          ? <p className="flex items-start gap-2 rounded-md bg-slate-100 p-3 text-sm text-slate-900" role="status"><Info size={18} className="mt-0.5 shrink-0" aria-hidden="true"/>{load.result.reason ?? NO_PREVIOUS_RUN_TEXT}</p>
          : <Comparison result={load.result}/>)}
      </div>
    </CardContent>
  </Card>
}

function Comparison({ result }: { result: CompareResult }) {
  const view = interpretationView(result)
  const tone = TONE[view.tone]
  const changes = useMemo(() => changeRows(result.parameter_changes), [result.parameter_changes])
  const rows = useMemo(() => metricRows(result), [result])
  return <div className="space-y-4">
    <p className="text-xs text-slate-900">Körning <span className="font-mono">{stamp(result.run)}</span> jämförd med <span className="font-mono">{result.base ? stamp(result.base) : ""}</span>.</p>

    <div className={`rounded-md border-2 p-3 ${tone.box}`} role="status">
      <div className="flex items-start gap-2">
        <span className="mt-0.5 shrink-0">{tone.icon}</span>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide">{tone.label}</p>
          <p className="text-base font-semibold">{view.text || view.title}</p>
          <p className="mt-1 text-xs">{view.title}.{!result.comparable && result.reason && result.reason !== view.text ? ` ${result.reason}` : ""}</p>
        </div>
      </div>
    </div>

    <div>
      <h4 className="text-sm font-semibold">Vad ändrades mellan körningarna</h4>
      {changes.length === 0
        ? <p className="mt-1 text-sm text-slate-900">Inga parametrar ändrades. Skillnader i måtten kommer då från sökningen, inte från reglerna.</p>
        : <ul className="mt-1 space-y-1 text-sm" aria-label="Ändrade parametrar">{changes.map(row => <li key={row.id} className="flex flex-wrap items-center gap-x-2 border-t border-slate-200 pt-1">
          <strong>{row.label}:</strong><span>{row.oldText}</span><ArrowRight size={13} aria-hidden="true"/><span className="sr-only">till</span><strong>{row.newText}</strong></li>)}</ul>}
    </div>

    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <caption className="sr-only">Mått för de två körningarna och skillnaden mellan dem</caption>
        <thead><tr className="border-b text-left text-xs text-slate-900"><th scope="col" className="p-2">Mått</th><th scope="col" className="p-2 text-right">Tidigare körning</th><th scope="col" className="p-2 text-right">Denna körning</th><th scope="col" className="p-2 text-right">Skillnad</th></tr></thead>
        <tbody>
          {rows.map(row => <tr key={row.key} className="border-b">
            <th scope="row" className="p-2 text-left font-medium">{row.label}{row.hint && <span className="block text-[11px] font-normal text-slate-800">{row.hint}</span>}</th>
            <td className="p-2 text-right tabular-nums">{row.old}</td>
            <td className="p-2 text-right tabular-nums">{row.new}</td>
            <td className="p-2 text-right font-semibold tabular-nums"><DeltaCell row={row}/></td>
          </tr>)}
          {result.uncertainty_ore !== null && <tr className="border-b bg-slate-50">
            <th scope="row" className="p-2 text-left font-medium">Osäkerhet<span className="block text-[11px] font-normal text-slate-800">Kostnadsskillnader som är mindre än så här kan inte tolkas som verkliga förbättringar.</span></th>
            <td className="p-2 text-right text-slate-700">–</td><td className="p-2 text-right tabular-nums">{formatKr(result.uncertainty_ore)}</td><td className="p-2 text-right text-slate-700">–</td>
          </tr>}
        </tbody>
      </table>
      {rows.length === 0 && <p className="p-2 text-sm text-slate-900">Backend skickade inga mått för jämförelsen.</p>}
    </div>
  </div>
}

function DeltaCell({ row }: { row: MetricRow }) {
  const icon = row.direction === "up" ? <ArrowUp size={14} aria-hidden="true"/> : row.direction === "down" ? <ArrowDown size={14} aria-hidden="true"/> : <Minus size={14} aria-hidden="true"/>
  return <span className="inline-flex items-center justify-end gap-1">{icon}{row.delta}</span>
}
