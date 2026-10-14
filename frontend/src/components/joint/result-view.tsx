import { useEffect, useId, useState, type ReactNode } from "react"
import { TriangleAlert } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { jointApi } from "@/lib/jointApi"
import type { JointEvent, JointScenario, JointSummary, SavedRun, WarmStartRecord } from "@/lib/jointTypes"
import type { JointJob } from "@/lib/useJointJob"
import type { JointState } from "@/lib/jointState"
import { runLabel } from "@/lib/runLabel"
import { InfoTip } from "@/components/ui/info-tip"
import { foldEvents } from "@/lib/jointState"
import { Button } from "@/components/ui/button"
import { SavingsCard } from "./savings-card"
import { ConstraintsFold, DiagnosisCard } from "./diagnosis-card"
import { LiveRun } from "./live-run"
import { Replay } from "./replay"
import { TimelineCard } from "./run-panels"
import { SummaryCard } from "./summary-card"
import { VerdictCards } from "./verdict-cards"
import { WarmStartCard } from "./warm-start-card"

type Loaded = { summary: JointSummary | null; warm: WarmStartRecord | null; events: JointEvent[]; errors: string[]; labels: Record<string, string> }

type Live = { job: JointJob; state: JointState; nowT: number; onCancel: () => void; onOpenUnderlay: () => void }

export function ResultView({ runId: chosen, runs, scenarios, onSelectRun, onCompare, live }: { runId: string | null; runs: SavedRun[]; scenarios: JointScenario[]; onSelectRun: (runId: string) => void; onCompare: (runId: string) => void; live: Live }) {
  // Utan val visas den senaste körningen, men inte medan en körning pågår (då är det den som är aktuell).
  const running = live.job.status === "running" || live.job.status === "starting"
  const runId = chosen ?? (running ? null : runs[0]?.run_id ?? null)
  const id = useId()
  const [data, setData] = useState<Loaded | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!runId) { setData(null); return }
    let cancelled = false
    setLoading(true)
    Promise.allSettled([jointApi.summary(runId), jointApi.warmStart(runId), jointApi.runEvents(runId)]).then(async ([summary, warm, events]) => {
      if (cancelled) return
      const errors: string[] = []
      const unwrap = <T,>(result: PromiseSettledResult<T>, label: string, fallback: T): T => {
        if (result.status === "fulfilled") return result.value
        errors.push(`${label}: ${(result.reason as Error).message}`); return fallback
      }
      const loadedSummary = unwrap(summary, "Sammanfattning", null)
      // Etiketter för parametrar som avviker från standard, om scenariot går att hämta. Annars visas id:n.
      const labels: Record<string, string> = {}
      if (loadedSummary?.scenario_id && loadedSummary.parameters_changed_from_default.length) {
        try { for (const param of (await jointApi.parameters(loadedSummary.scenario_id)).parameters) labels[param.id] = param.label } catch { /* id:n räcker */ }
      }
      if (cancelled) return
      setData({ summary: loadedSummary, warm: unwrap(warm, "Start från förra körningen", null), events: unwrap(events, "Händelser", [] as JointEvent[]), errors, labels })
      setLoading(false)
    })
    return () => { cancelled = true }
  }, [runId])

  return <div className="space-y-4">
    <LiveRun job={live.job} state={live.state} nowT={live.nowT} scenarios={scenarios} onCancel={live.onCancel} onOpenUnderlay={live.onOpenUnderlay}/>
    <Card><CardContent className="flex flex-wrap items-end gap-3 pt-4">
      <div><label className="label flex items-center gap-1" htmlFor={`${id}-run`}>Körning{runId && <InfoTip label="Körningens tekniska id">Tekniskt id: <span className="font-mono">{runId}</span></InfoTip>}</label>
        <select id={`${id}-run`} className="field min-w-[22rem]" value={runId ?? ""} onChange={event => event.target.value && onSelectRun(event.target.value)}>
          <option value="">Välj en körning</option>
          {runs.map(run => <option key={run.run_id} value={run.run_id} title={run.run_id}>{runLabel(run, scenarios)}</option>)}
          {runId && !runs.some(run => run.run_id === runId) && <option value={runId}>{runLabel({ run_id: runId, scenario_id: "" }, scenarios)}</option>}
        </select></div>
      {loading && <span className="text-xs text-slate-900" role="status">Hämtar resultat …</span>}
    </CardContent></Card>

    {!runId && !running && <Card><CardContent className="pt-4 text-sm text-slate-900">Det finns inga körningar än. Starta en under "1. Ställ in och kör".</CardContent></Card>}
    {data?.errors.map(error => <p key={error} className="flex items-start gap-1.5 rounded-md bg-red-50 p-2 text-xs text-red-900" role="alert"><TriangleAlert size={14} className="mt-0.5 shrink-0" aria-hidden="true"/>{error}</p>)}

    {runId && data?.summary?.has_verified_solution && <SavingsCard runId={runId}/>}
    {data?.summary && <SummaryCard summary={data.summary} labels={data.labels}/>}
    {runId && data?.summary?.has_verified_solution && <ConstraintsFold runId={runId}/>}
    {runId && data?.summary && !data.summary.has_verified_solution && !data.summary.cancelled && <DiagnosisCard runId={runId}/>}
    {data && runId && <Fold title={data.summary?.has_verified_solution ? "Jämförelse, domar, förlopp och uppspelning" : "Fler detaljer: jämförelse, förlopp och uppspelning"} open={data.summary?.has_verified_solution === true}>
      <Card><CardContent className="flex flex-wrap items-center gap-3 pt-4">
        <p className="text-sm">Jämför den här körningen med A (faktisk bokning), B eller en annan körning: nyckeltal, önskemål, salar, kostnad och vilka parametrar som skiljer.</p>
        <Button type="button" size="sm" onClick={() => onCompare(runId)}>Öppna jämförelsen</Button></CardContent></Card>
      {data.summary && <VerdictCards summary={data.summary}/>}
      {data.events.length > 0 && <TimelineCard state={foldEvents(data.events)} events={data.events} nowT={Math.max(...data.events.map(event => event.t))}/>}
      <WarmStartCard record={data.warm}/>
      <Replay events={data.events} costVisible={data.summary?.has_verified_solution === true}/>
    </Fold>}
  </div>
}

/** Det som inte behövs för att förstå utfallet ligger hopfällt; vid ett fel öppnas det inte av sig självt. */
function Fold({ title, open, children }: { title: string; open: boolean; children: ReactNode }) {
  return <details open={open} className="rounded-lg border bg-white">
    <summary className="cursor-pointer p-3 text-sm font-semibold">{title}</summary>
    <div className="space-y-4 p-3 pt-0">{children}</div>
  </details>
}
