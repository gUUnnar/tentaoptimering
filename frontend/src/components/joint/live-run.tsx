import { ArrowRight, Loader2, OctagonX } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { InfoTip } from "@/components/ui/info-tip"
import { Notice } from "@/components/ui/notice"
import { formatDuration } from "@/lib/jointFormat"
import type { JointState } from "@/lib/jointState"
import type { JointScenario } from "@/lib/jointTypes"
import { scenarioName } from "@/lib/runLabel"
import { isMissingUnderlayMessage } from "@/lib/underlay"
import type { JointJob } from "@/lib/useJointJob"
import { RunPanels } from "./run-panels"
import { UnderlayNotice } from "./underlay-notice"

type Props = { job: JointJob; state: JointState; nowT: number; scenarios: JointScenario[]; onCancel: () => void; onOpenUnderlay: () => void }

/** Visas överst i Resultat bara medan en körning pågår, och ett besked om en körning som inte gav något resultat. */
export function LiveRun({ job, state, nowT, scenarios, onCancel, onOpenUnderlay }: Props) {
  const running = job.status === "running"
  const starting = job.status === "starting"
  const failed = job.status === "failed" || state.finished?.outcome === "failed"
  const failure = job.error ?? state.finished?.error ?? null

  if (failed && !job.runId) {
    return isMissingUnderlayMessage(failure)
      ? <UnderlayNotice onOpen={onOpenUnderlay} detail="Körningen kunde inte läsa det förberedda underlaget. Förbered underlaget under Underlag och starta sedan om körningen."/>
      : <Notice tone="error" title="Körningen misslyckades och gav inget resultat." open>{failure && <p className="whitespace-pre-line">{failure}</p>}</Notice>
  }
  if (!running && !starting) return null

  return <div className="space-y-4">
    <Card><CardContent className="space-y-3 pt-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm" role="status" aria-live="polite">
          <Loader2 size={16} className="animate-spin motion-reduce:animate-none" aria-hidden="true"/>
          <strong>{starting ? "Startar körningen …" : job.cancelRequested ? "Stoppar körningen …" : "Körning pågår"}</strong>
          {job.scenarioId && <span>{scenarioName(scenarios, job.scenarioId)}</span>}
          <span className="tabular-nums text-slate-800">{formatDuration(nowT)}</span>
        </p>
        <div className="flex items-center gap-2">
          <InfoTip label="Om körningen" align="right">
            <span className="block">Den bästa kontrollerade lösningen hittills sparas om du stoppar körningen.</span>
            <span className="block">Du kan lämna sidan och komma tillbaka; körningen fortsätter. När den är klar visas resultatet här.</span>
          </InfoTip>
          <Button variant="destructive" disabled={!running || job.cancelRequested} onClick={onCancel}><OctagonX size={15} className="mr-1" aria-hidden="true"/>{job.cancelRequested ? "Stoppar …" : "Stoppa"}</Button>
        </div>
      </div>
      {job.changes.length > 0 && <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm" aria-label="Dina ändringar i körningen">
        {job.changes.map(change => <li key={change.id} className="flex flex-wrap items-center gap-x-1.5"><strong>{change.label}:</strong><span>{change.oldText}</span><ArrowRight size={13} aria-hidden="true"/><span className="sr-only">till</span><strong>{change.newText}</strong></li>)}
      </ul>}
      {job.connectionLost && <Notice tone="warning" title="Kontakten med servern är bruten.">Körningen kan fortfarande pågå. Sidan försöker ansluta igen. {job.error}</Notice>}
    </CardContent></Card>
    <RunPanels state={state} events={job.events} nowT={nowT}/>
  </div>
}
