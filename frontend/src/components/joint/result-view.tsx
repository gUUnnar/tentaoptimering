import { useEffect, useId, useState } from "react"
import { TriangleAlert } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { jointApi } from "@/lib/jointApi"
import type { JointEvent, JointSummary, SavedRun, WarmStartRecord } from "@/lib/jointTypes"
import { foldEvents } from "@/lib/jointState"
import { CompareSection } from "./compare-section"
import { HowToRead } from "./how-to-read"
import { Replay } from "./replay"
import { TimelineCard } from "./run-panels"
import { SummaryCard } from "./summary-card"
import { VerdictCards } from "./verdict-cards"
import { WarmStartCard } from "./warm-start-card"

type Loaded = { summary: JointSummary | null; warm: WarmStartRecord | null; events: JointEvent[]; errors: string[]; labels: Record<string, string> }

export function ResultView({ runId, runs, onSelectRun }: { runId: string | null; runs: SavedRun[]; onSelectRun: (runId: string) => void }) {
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
    <Card><CardContent className="flex flex-wrap items-end gap-3 pt-4">
      <div><label className="label" htmlFor={`${id}-run`}>Körning</label>
        <select id={`${id}-run`} className="field min-w-[22rem]" value={runId ?? ""} onChange={event => event.target.value && onSelectRun(event.target.value)}>
          <option value="">Välj en sparad körning</option>
          {runs.map(run => <option key={run.run_id} value={run.run_id}>{run.run_id} · {run.scenario_id}{run.created_at ? ` · ${run.created_at.slice(0, 16).replace("T", " ")}` : ""}</option>)}
          {runId && !runs.some(run => run.run_id === runId) && <option value={runId}>{runId}</option>}
        </select></div>
      {loading && <span className="text-xs text-slate-900" role="status">Hämtar resultat …</span>}
    </CardContent></Card>

    <HowToRead/>
    {!runId && <Card><CardContent className="pt-4 text-sm text-slate-900">Välj en avslutad körning för sammanfattning, jämförelse och förlopp. En körning som stoppats utan kontrollerad lösning har inget resultat att visa.</CardContent></Card>}
    {data?.errors.map(error => <p key={error} className="flex items-start gap-1.5 rounded-md bg-red-50 p-2 text-xs text-red-900" role="alert"><TriangleAlert size={14} className="mt-0.5 shrink-0" aria-hidden="true"/>{error}</p>)}

    {data?.summary && <SummaryCard summary={data.summary} labels={data.labels}/>}
    {runId && data && <CompareSection runId={runId} runs={runs}/>}
    {data?.summary && <VerdictCards summary={data.summary}/>}
    {data && runId && data.events.length > 0 && <TimelineCard state={foldEvents(data.events)} events={data.events} nowT={Math.max(...data.events.map(event => event.t))}/>}
    {data && runId && <WarmStartCard record={data.warm}/>}
    {data && runId && <Replay events={data.events} costVisible={data.summary?.has_verified_solution === true}/>}
  </div>
}
