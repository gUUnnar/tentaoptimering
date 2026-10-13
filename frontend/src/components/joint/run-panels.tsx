import { Info } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { warmStartBadge, warmStartSentence } from "@/lib/jointFormat"
import type { JointState } from "@/lib/jointState"
import type { JointEvent } from "@/lib/jointTypes"
import { CostPanel } from "./cost-panel"
import { DayGrids } from "./day-grid"
import { ResourceBox } from "./resource-box"
import { RunTimeline } from "./run-timeline"

/** Körningens steg som tidslinje, med startbeskedet från förra körningen i en rad (rubrik och en mening). */
export function TimelineCard({ state, events, nowT }: { state: JointState; events: JointEvent[]; nowT: number }) {
  const warm = state.warmStart
  const badge = warm ? warmStartBadge(warm.decision) : null
  return <Card><CardHeader><CardTitle>Körningens steg</CardTitle></CardHeader><CardContent className="space-y-3">
    <RunTimeline events={events} nowT={nowT}/>
    {warm && <p className="flex items-start gap-1.5 rounded-md bg-slate-50 p-2 text-xs text-slate-900"><Info size={14} className="mt-0.5 shrink-0" aria-hidden="true"/>
      <span><strong>Start från förra körningen</strong>{badge ? <> ({badge.toLowerCase()})</> : null}. {warmStartSentence(warm.decision, warm.explanation)}{warm.source_run_id ? ` Förra körningen: ${warm.source_run_id}.` : ""}</span></p>}
  </CardContent></Card>
}

/** Gemensamma paneler för livevy och uppspelning: samma tillstånd, samma presentation. */
export function RunPanels({ state, events, nowT, costVisible = true }: { state: JointState; events: JointEvent[]; nowT: number; costVisible?: boolean }) {
  return <div className="space-y-4">
    <TimelineCard state={state} events={events} nowT={nowT}/>
    <div className="grid gap-4 xl:grid-cols-[1fr_280px]">
      {costVisible ? <CostPanel state={state} nowT={nowT}/> : <Card><CardHeader><CardTitle>Kostnad över tid</CardTitle></CardHeader>
        <CardContent className="text-sm text-slate-900">Kostnadsgrafen visas inte, eftersom körningen saknar en verifierad lösning. Ingen kostnad ska läsas som en lösning.</CardContent></Card>}
      <ResourceBox state={state} elapsedT={nowT}/>
    </div>
    <DayGrids state={state}/>
  </div>
}
