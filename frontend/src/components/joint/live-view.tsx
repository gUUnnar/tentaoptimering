import { ArrowRight, OctagonX, TriangleAlert } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { formatDuration, outcomeLabel } from "@/lib/jointFormat"
import type { JointState } from "@/lib/jointState"
import { isMissingUnderlayMessage } from "@/lib/underlay"
import type { JointJob } from "@/lib/useJointJob"
import { RunPanels } from "./run-panels"
import { JobStatusChip } from "./status-chip"
import { UnderlayNotice } from "./underlay-notice"

export function LiveView({ job, state, nowT, onCancel, onShowResult, onOpenUnderlay }: {
  job: JointJob; state: JointState; nowT: number; onCancel: () => void; onShowResult: (runId: string) => void; onOpenUnderlay: () => void
}) {
  if (job.status === "idle") return <Card><CardContent className="pt-4 text-sm text-slate-900">Ingen körning pågår. Starta en körning under "1. Ställ in och kör".</CardContent></Card>
  const running = job.status === "running"
  const starting = job.status === "starting"
  const failure = job.error ?? state.finished?.error ?? null
  const missingUnderlay = isMissingUnderlayMessage(failure)
  return <div className="space-y-4">
    <Card><CardContent className="space-y-3 pt-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          {starting ? <span className="text-sm" role="status">Startar körningen …</span> : <JobStatusChip status={job.status}/>}
          <span className="text-sm text-slate-900">Förbrukad tid: <strong className="tabular-nums">{formatDuration(nowT)}</strong></span>
          {job.scenarioId && <span className="text-sm text-slate-900">Scenario: <strong>{job.scenarioId}</strong></span>}
          {job.jobId && <span className="font-mono text-[11px] text-slate-700">körning {job.jobId}</span>}
        </div>
        <div className="flex flex-col items-end gap-1">
          <Button variant="destructive" disabled={!running || job.cancelRequested} onClick={onCancel} aria-describedby="joint-stop-help"><OctagonX size={15} className="mr-1" aria-hidden="true"/>{job.cancelRequested ? "Stoppar …" : "Stoppa körningen"}</Button>
          <span id="joint-stop-help" className="text-xs text-slate-800">Den bästa kontrollerade lösningen hittills sparas.</span>
        </div>
      </div>
      <div role="status" aria-live="polite" className="space-y-1 text-sm">
        {running && job.cancelRequested && <p className="text-amber-900">Stoppbegäran är skickad. Modellen avslutar det den håller på med och sparar den bästa kontrollerade lösningen.</p>}
        {running && !job.cancelRequested && <p className="text-slate-900">Körningen pågår. Du kan lämna sidan och komma tillbaka; körningen fortsätter.</p>}
        {state.finished && <p><strong>{state.finished.cancelled ? "Körningen stoppades" : state.finished.outcome === "failed" ? "Körningen misslyckades" : "Körningen är klar"}:</strong> {outcomeLabel(state.finished.outcome)}.{state.finished.cancelled && state.finished.cost_ore === null && " Ingen kontrollerad lösning fanns att spara."}</p>}
        {(job.status === "failed" || state.finished?.outcome === "failed") && (missingUnderlay
          ? <UnderlayNotice onOpen={onOpenUnderlay} detail="Körningen kunde inte läsa det förberedda underlaget. Förbered underlaget under Underlag och starta sedan om körningen."/>
          : <p className="text-red-900"><strong>Körningen misslyckades.</strong> {failure ?? ""}</p>)}
      </div>
      {job.connectionLost && <p className="flex items-start gap-1.5 rounded-md bg-amber-50 p-2 text-xs text-amber-900" role="alert"><TriangleAlert size={14} className="mt-0.5 shrink-0" aria-hidden="true"/>Kontakten med servern är bruten ({job.error}). Gränssnittet försöker igen varje sekund; körningen kan fortsätta på servern.</p>}
      {!running && !starting && job.runId && <Button variant="outline" onClick={() => onShowResult(job.runId!)}>Visa resultat och jämförelse</Button>}
      {!running && !starting && !job.runId && job.status !== "failed" && <p className="text-xs text-slate-800">Körningen har ingen sparad lösning att visa resultat för.</p>}
    </CardContent></Card>

    <Card><CardContent className="pt-4">
      <h3 className="text-sm font-semibold">Parametrar som den här körningen har ändrat</h3>
      {job.changes.length === 0
        ? <p className="mt-1 text-sm text-slate-900">Inga. Körningen använder scenariots egna värden.</p>
        : <ul className="mt-2 space-y-1 text-sm" aria-label="Ändrade parametrar i körningen">
          {job.changes.map(change => <li key={change.id} className="flex flex-wrap items-center gap-x-2"><strong>{change.label}:</strong><span>{change.oldText}</span><ArrowRight size={13} aria-hidden="true"/><span className="sr-only">till</span><strong>{change.newText}</strong></li>)}
        </ul>}
    </CardContent></Card>
    <RunPanels state={state} nowT={nowT}/>
  </div>
}
