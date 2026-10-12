import { Info } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { DECISION_TEXT } from "@/lib/jointFormat"
import type { JointState } from "@/lib/jointState"
import { CostPanel } from "./cost-panel"
import { DayGrids } from "./day-grid"
import { PhaseBand } from "./phase-band"
import { ResourceBox } from "./resource-box"

/** Gemensamma paneler för livevy och uppspelning: samma tillstånd, samma presentation. */
export function RunPanels({ state, nowT }: { state: JointState; nowT: number }) {
  return <div className="space-y-4">
    <Card><CardHeader><CardTitle>Körningens steg</CardTitle></CardHeader><CardContent className="space-y-2">
      <PhaseBand state={state} nowT={nowT}/>
      {state.warmStart && <p className="flex items-start gap-1.5 rounded-md bg-slate-50 p-2 text-xs text-slate-900"><Info size={14} className="mt-0.5 shrink-0" aria-hidden="true"/><span>Start från förra körningen: <strong>{DECISION_TEXT[state.warmStart.decision]?.label ?? state.warmStart.decision}</strong>. {state.warmStart.explanation}{state.warmStart.source_run_id ? ` (förra körningen: ${state.warmStart.source_run_id})` : ""}</span></p>}
    </CardContent></Card>
    <div className="grid gap-4 xl:grid-cols-[1fr_280px]">
      <CostPanel state={state} nowT={nowT}/>
      <ResourceBox state={state} elapsedT={nowT}/>
    </div>
    <DayGrids state={state}/>
  </div>
}
