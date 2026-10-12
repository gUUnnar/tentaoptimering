import { OctagonX, TriangleAlert } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { formatDuration, outcomeLabel } from "@/lib/jointFormat"
import type { JointState } from "@/lib/jointState"
import type { JointJob } from "@/lib/useJointJob"
import { RunPanels } from "./run-panels"
import { JobStatusChip } from "./status-chip"

export function LiveView({ job, state, nowT, mock, onCancel, onShowResult }: {
  job: JointJob; state: JointState; nowT: number; mock: boolean; onCancel: () => void; onShowResult: (runId: string) => void
}) {
  if (job.status === "idle") return <Card><CardContent className="pt-4 text-sm text-slate-700">Ingen körning pågår. Starta en körning under fliken Start.</CardContent></Card>
  const running = job.status === "running"
  const starting = job.status === "starting"
  return <div className="space-y-4">
    <Card><CardContent className="space-y-3 pt-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          {starting ? <span className="text-sm">Startar körningen …</span> : <JobStatusChip status={job.status}/>}
          <span className="text-sm text-slate-700">Förbrukad tid: <strong className="tabular-nums text-slate-900">{formatDuration(nowT)}</strong></span>
          {job.jobId && <span className="font-mono text-[11px] text-slate-700">jobb {job.jobId}</span>}
        </div>
        <div className="flex flex-col items-end gap-1">
          <Button variant="destructive" disabled={!running || job.cancelRequested} onClick={onCancel} aria-describedby="joint-stop-help"><OctagonX size={15} className="mr-1" aria-hidden="true"/>{job.cancelRequested ? "Stoppar …" : "Stoppa körningen"}</Button>
          <span id="joint-stop-help" className="text-xs text-slate-700">Sparar bästa verifierade lösning.</span>
        </div>
      </div>
      <div role="status" aria-live="polite" className="space-y-1 text-sm">
        {running && job.cancelRequested && <p className="text-amber-900">Stoppbegäran är skickad. Lösaren avslutar pågående steg och sparar bästa verifierade lösning.</p>}
        {state.finished && <p><strong>{state.finished.cancelled ? "Körningen stoppades" : "Körningen är klar"}:</strong> {outcomeLabel(state.finished.outcome)}.{state.finished.cancelled && state.finished.cost_ore === null && " Ingen verifierad lösning fanns att spara."}</p>}
        {job.status === "failed" && <p className="text-red-800"><strong>Körningen misslyckades.</strong> {job.error ?? ""}</p>}
      </div>
      {job.connectionLost && <p className="flex items-start gap-1.5 rounded-md bg-amber-50 p-2 text-xs text-amber-900" role="alert"><TriangleAlert size={14} className="mt-0.5 shrink-0" aria-hidden="true"/>Kontakten med servern är bruten ({job.error}). Gränssnittet försöker igen varje sekund; körningen kan fortsätta på servern.</p>}
      {!running && !starting && job.runId && <Button variant="outline" onClick={() => onShowResult(job.runId!)}>Visa resultat och varmstartsbeslut</Button>}
      {!running && !starting && !job.runId && job.status !== "failed" && <p className="text-xs text-slate-700">Körningen har ingen sparad körning att visa resultat för.</p>}
      {mock && <p className="text-xs text-slate-700">Mockläge: händelserna spelas upp från exempeldata i snabbare takt.</p>}
    </CardContent></Card>
    <RunPanels state={state} nowT={nowT}/>
  </div>
}
