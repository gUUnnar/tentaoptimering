import { useEffect, useId, useMemo, useState } from "react"
import { ArrowDown, ArrowRight, ArrowUp, Ban, CircleCheck, CircleHelp, Info, Minus, TriangleAlert } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { InfoTip } from "@/components/ui/info-tip"
import { Notice } from "@/components/ui/notice"
import { jointApi } from "@/lib/jointApi"
import { NO_PREVIOUS_RUN_TEXT, assumptionView, changeRows, interpretationView, metricRows, type InterpretationView, type MetricRow } from "@/lib/jointCompare"
import { formatKr } from "@/lib/jointFormat"
import type { CompareResult, CompareRunRef, JointScenario, SavedRun } from "@/lib/jointTypes"
import { runLabel } from "@/lib/runLabel"

type Load = { status: "loading" | "ready" | "error"; result: CompareResult | null; error: string }

const MISSING = "–"
const stamp = (ref: CompareRunRef) => `${ref.run_id}${ref.created_at ? ` (${ref.created_at.slice(0, 16).replace("T", " ")})` : ""}`

const TONE: Record<InterpretationView["tone"], { box: string; icon: JSX.Element; label: string }> = {
  interpretable: { box: "border-slate-300 bg-white text-slate-900", icon: <CircleCheck size={18} className="text-emerald-700" aria-hidden="true"/>, label: "Tolkningsbar" },
  not_interpretable: { box: "border-slate-300 bg-slate-50 text-slate-900", icon: <Info size={18} aria-hidden="true"/>, label: "Går inte att tolka" },
  unknown: { box: "border-slate-300 bg-slate-50 text-slate-900", icon: <CircleHelp size={18} aria-hidden="true"/>, label: "Kan inte bedömas" },
}

/** Jämförelse av en körning mot föregående körning av samma scenario, eller mot en vald körning. */
export function CompareSection({ runId, runs, scenarios }: { runId: string; runs: SavedRun[]; scenarios: JointScenario[] }) {
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
          {others.map(run => <option key={run.run_id} value={run.run_id} title={run.run_id}>{runLabel(run, scenarios)}</option>)}
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

export function Comparison({ result }: { result: CompareResult }) {
  const view = interpretationView(result)
  const tone = TONE[view.tone]
  const changes = useMemo(() => changeRows(result.parameter_changes), [result.parameter_changes])
  const allRows = useMemo(() => metricRows(result), [result])
  const rows = allRows.filter(row => !(row.old === MISSING && row.new === MISSING))
  const assumptions = useMemo(() => assumptionView(result), [result])
  const detail = !result.comparable && result.reason && result.reason !== view.text ? result.reason : null
  return <div className="space-y-4">
    <div className={`flex items-start gap-2 rounded-md border p-2.5 text-sm ${tone.box}`} role="status">
      <span className="mt-0.5 shrink-0">{tone.icon}</span>
      <p className="min-w-0 flex-1 font-medium">{view.text || view.title}</p>
      <InfoTip label="Om jämförelsen" align="right">
        <span className="block">{view.title}.{detail ? ` ${detail}` : ""}</span>
        <span className="block">Körning <span className="font-mono">{stamp(result.run)}</span> jämförd med <span className="font-mono">{result.base ? stamp(result.base) : ""}</span>.</span>
      </InfoTip>
    </div>

    {assumptions && <Notice tone="warning" title={assumptions.title}>
      {assumptions.groups.map(group => <div key={group.label}><p className="font-semibold">{group.label}:</p>
        <ul className="list-disc pl-5">{group.items.map(item => <li key={item}>{item}</li>)}</ul></div>)}
      <p>{assumptions.text}</p>
    </Notice>}

    <div>
      <h4 className="text-base font-bold">Vad ändrades</h4>
      {changes.length === 0
        ? <p className="mt-1 text-sm text-slate-900">Inga parametrar. Skillnader i måtten kommer från sökningen, inte från reglerna.</p>
        : <ul className="mt-1 divide-y rounded-md border text-sm" aria-label="Ändrade parametrar">{changes.map(row => <li key={row.id} className="flex flex-wrap items-center gap-x-2 px-2.5 py-1.5">
          <span className="font-medium">{row.label}</span><span className="text-slate-800">{row.oldText}</span><ArrowRight size={13} aria-hidden="true"/><span className="sr-only">till</span><strong>{row.newText}</strong></li>)}</ul>}
    </div>

    {rows.length > 0 && <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <caption className="sr-only">Mått för de två körningarna och skillnaden mellan dem</caption>
        <thead><tr className="border-b text-left text-xs text-slate-900"><th scope="col" className="p-2">Mått</th><th scope="col" className="p-2 text-right">Tidigare</th><th scope="col" className="p-2 text-right">Denna</th><th scope="col" className="p-2 text-right">Skillnad</th></tr></thead>
        <tbody>
          {rows.map(row => <tr key={row.key} className="border-b">
            <th scope="row" className="p-2 text-left font-medium">
              <span className="inline-flex items-center gap-1.5">{row.label}
                {row.physical && <span className="rounded border px-1 text-[11px] font-semibold">Fysiskt mått</span>}
                {row.hint && <InfoTip label={`Om måttet ${row.label}`}>{row.hint}</InfoTip>}</span></th>
            <td className="p-2 text-right tabular-nums">{row.old}</td>
            <td className="p-2 text-right tabular-nums">{row.new}</td>
            <td className="p-2 text-right font-semibold tabular-nums"><DeltaCell row={row}/></td>
          </tr>)}
          {result.uncertainty_ore !== null && <tr className="border-b bg-slate-50">
            <th scope="row" className="p-2 text-left font-medium"><span className="inline-flex items-center gap-1.5">Osäkerhet<InfoTip label="Om osäkerheten">Kostnadsskillnader som är mindre än så här kan inte tolkas som verkliga förbättringar.</InfoTip></span></th>
            <td className="p-2 text-right text-slate-700">–</td><td className="p-2 text-right tabular-nums">{formatKr(result.uncertainty_ore)}</td><td className="p-2 text-right text-slate-700">–</td>
          </tr>}
        </tbody>
      </table>
      {allRows.length > rows.length && <p className="p-2 text-xs text-slate-800">{allRows.length - rows.length} mått utan värde i båda körningarna visas inte.</p>}
    </div>}
    {allRows.length === 0 && <p className="p-2 text-sm text-slate-900">Backend skickade inga mått för jämförelsen.</p>}
  </div>
}

function DeltaCell({ row }: { row: MetricRow }) {
  if (row.notCompared) return <span className="inline-flex items-center justify-end gap-1 text-xs font-medium text-amber-950"><Ban size={14} aria-hidden="true"/>{row.delta}</span>
  const icon = row.direction === "up" ? <ArrowUp size={14} aria-hidden="true"/> : row.direction === "down" ? <ArrowDown size={14} aria-hidden="true"/> : <Minus size={14} aria-hidden="true"/>
  return <span className="inline-flex items-center justify-end gap-1">{icon}{row.delta}</span>
}
