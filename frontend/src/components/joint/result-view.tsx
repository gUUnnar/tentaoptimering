import { useEffect, useId, useState } from "react"
import { TriangleAlert } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { JointApi } from "@/lib/jointApi"
import { costStatement, describeVerdict, formatCount, formatDuration, formatGap, formatKr, outcomeLabel } from "@/lib/jointFormat"
import { gapFraction } from "@/lib/jointState"
import type { JointEvent, JointSummary, SavedRun, WarmStartRecord } from "@/lib/jointTypes"
import { Replay } from "./replay"
import { VerdictChip } from "./status-chip"
import { WarmStartCard } from "./warm-start-card"

type Loaded = { summary: JointSummary | null; warm: WarmStartRecord | null; events: JointEvent[]; errors: string[] }

export function ResultView({ api, runId, runs, onSelectRun }: { api: JointApi; runId: string | null; runs: SavedRun[]; onSelectRun: (runId: string) => void }) {
  const id = useId()
  const [data, setData] = useState<Loaded | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!runId) { setData(null); return }
    let cancelled = false
    setLoading(true)
    Promise.allSettled([api.summary(runId), api.warmStart(runId), api.runEvents(runId)]).then(([summary, warm, events]) => {
      if (cancelled) return
      const errors: string[] = []
      const unwrap = <T,>(result: PromiseSettledResult<T>, label: string, fallback: T): T => {
        if (result.status === "fulfilled") return result.value
        errors.push(`${label}: ${(result.reason as Error).message}`); return fallback
      }
      setData({ summary: unwrap(summary, "Sammanfattning", null), warm: unwrap(warm, "Varmstartsbeslut", null), events: unwrap(events, "Händelser", [] as JointEvent[]), errors })
      setLoading(false)
    })
    return () => { cancelled = true }
  }, [api, runId])

  return <div className="space-y-4">
    <Card><CardContent className="flex flex-wrap items-end gap-3 pt-4">
      <div><label className="label" htmlFor={`${id}-run`}>Körning</label>
        <select id={`${id}-run`} className="field min-w-[22rem]" value={runId ?? ""} onChange={e => e.target.value && onSelectRun(e.target.value)}>
          <option value="">Välj en sparad körning</option>
          {runs.map(run => <option key={run.run_id} value={run.run_id}>{run.run_id} · {run.scenario_id}{run.created_at ? ` · ${run.created_at.slice(0, 16).replace("T", " ")}` : ""}</option>)}
          {runId && !runs.some(run => run.run_id === runId) && <option value={runId}>{runId}</option>}
        </select></div>
      {loading && <span className="text-xs text-slate-700" role="status">Hämtar resultat …</span>}
    </CardContent></Card>

    {!runId && <Card><CardContent className="pt-4 text-sm text-slate-700">Välj en avslutad körning för sammanfattning, varmstartsbeslut och uppspelning. En körning som stoppats utan verifierad lösning har inget resultat att visa.</CardContent></Card>}
    {data?.errors.map(error => <p key={error} className="flex items-start gap-1.5 rounded-md bg-red-50 p-2 text-xs text-red-900" role="alert"><TriangleAlert size={14} className="mt-0.5 shrink-0" aria-hidden="true"/>{error}</p>)}

    {data?.summary && <Summary summary={data.summary}/>}
    {data && runId && <WarmStartCard record={data.warm}/>}
    {data && runId && <Replay events={data.events}/>}
  </div>
}

function Summary({ summary }: { summary: JointSummary }) {
  const gap = summary.gap ?? gapFraction(summary.cost_ore, summary.bound_ore)
  const statement = costStatement(summary.cost_ore, summary.bound_ore, summary.outcome)
  const technical = describeVerdict(summary.technical_validation)
  const business = describeVerdict(summary.business_verification)
  const provenance = describeVerdict(summary.provenance)
  return <section className="space-y-4" aria-label="Sammanfattning av körningen">
    <Card>
      <CardHeader><CardTitle>Sammanfattning</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <div className={statement.proven ? "rounded-md bg-emerald-50 p-3 text-emerald-900" : "rounded-md bg-amber-50 p-3 text-amber-900"}>
          <div className="text-xs">{statement.proven ? "Verifierad kostnad (bevisat optimum)" : "Kostnadsintervall: undre gräns–verifierad kostnad"}</div>
          <div className="mt-0.5 text-2xl font-semibold tabular-nums">{statement.headline}</div>
          <div className="mt-1 text-xs">{statement.note}</div>
          <div className="mt-1 text-xs">Det är en modellerad kostnad. Faktisk kostnad, teoretisk årlig potential och verifierad realiserbar besparing redovisas separat och framgår inte av denna siffra.</div>
        </div>
        <dl className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <Stat label="Verifierad kostnad" value={formatKr(summary.cost_ore)}/>
          <Stat label="Bevisad undre gräns" value={formatKr(summary.bound_ore)}/>
          <Stat label="Gap" value={formatGap(gap)}/>
          <Stat label="Flyttade tentor" value={formatCount(summary.changed_exams)}/>
          <Stat label="Tid till första lösning" value={formatDuration(summary.first_solution_seconds)}/>
          <Stat label="Total tid" value={formatDuration(summary.wall_seconds)}/>
        </dl>
        <p className="text-xs text-slate-700">Utfall: <strong>{outcomeLabel(summary.outcome)}</strong></p>
      </CardContent>
    </Card>

    <div className="flex items-start gap-2 rounded-md border-2 border-amber-700 bg-amber-50 p-3 text-sm text-amber-950" role="note">
      <TriangleAlert size={18} className="mt-0.5 shrink-0" aria-hidden="true"/>
      <p><strong>Teknisk korrekthet är inte verksamhetsmässig genomförbarhet.</strong> Den tekniska eftervalideringen visar att placeringen följer de regler modellen kan uttrycka. Den visar inte att schemat går att genomföra i verksamheten. Data eller modellstöd som saknas räknas aldrig som godkänt.</p>
    </div>

    <div className="grid gap-4 lg:grid-cols-3">
      <Card><CardHeader><CardTitle>Teknisk eftervalidering</CardTitle></CardHeader><CardContent className="space-y-2 text-xs">
        <VerdictChip status={technical.status}/>
        <p className="text-slate-700">Fristående kontroll av placeringens fullständighet och hårda villkor.</p>
        {technical.reason && <p>{technical.reason}</p>}
        <Details items={technical.details}/>
      </CardContent></Card>
      <Card><CardHeader><CardTitle>Verksamhetsmässig verifiering</CardTitle></CardHeader><CardContent className="space-y-2 text-xs">
        <VerdictChip status={business.status}/>
        <p className="text-slate-700">Om schemat är genomförbart med faktiska avtal, lagar och arbetstidsvillkor. Normalt <code>not_evaluated</code> i nuläget.</p>
        {business.reason && <p>{business.reason}</p>}
        <Details items={business.details}/>
      </CardContent></Card>
      <Card><CardHeader><CardTitle>Ursprung</CardTitle></CardHeader><CardContent className="space-y-2 text-xs">
        {typeof summary.provenance === "string" ? <p>{summary.provenance}</p> : <>
          {provenance.status && <p>Status: {provenance.status}</p>}
          {provenance.reason && <p>{provenance.reason}</p>}
          <Details items={provenance.details}/>
          {!provenance.status && !provenance.reason && !provenance.details.length && <p className="text-slate-700">Ursprung är inte redovisat.</p>}
        </>}
        <p className="text-slate-700">Visar vilka data och antaganden resultatet vilar på.</p>
      </CardContent></Card>
    </div>
  </section>
}

function Stat({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md border p-2.5"><dt className="text-xs text-slate-700">{label}</dt><dd className="mt-0.5 text-base font-semibold tabular-nums">{value}</dd></div>
}

function Details({ items }: { items: [string, string][] }) {
  if (!items.length) return null
  return <dl className="space-y-0.5">{items.map(([key, value]) => <div key={key} className="flex justify-between gap-2 border-t border-slate-100 pt-0.5"><dt className="text-slate-700">{key}</dt><dd className="text-right font-medium">{value}</dd></div>)}</dl>
}
