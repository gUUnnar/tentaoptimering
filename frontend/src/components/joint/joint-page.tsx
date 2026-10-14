import { useCallback, useEffect, useState } from "react"
import * as Tabs from "@radix-ui/react-tabs"
import { jointApi } from "@/lib/jointApi"
import type { RunChangeText } from "@/lib/jointJobMemory"
import type { JointScenario, SavedRun, StartJointRunBody } from "@/lib/jointTypes"
import { useJointJob } from "@/lib/useJointJob"
import { ResultView } from "./result-view"
import { StartPanel } from "./start-panel"
import { InfoTip } from "@/components/ui/info-tip"

type Tab = "start" | "result"
const TRIGGER = "rounded-t-md border-b-2 border-transparent px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-700 data-[state=active]:border-sky-800 data-[state=active]:text-sky-900"

/** Sidan "Optimering": ställ in och kör, följ körningen, läs och jämför resultatet. */
export default function JointPage({ onOpenUnderlay, reloadKey }: { onOpenUnderlay: () => void; reloadKey: number }) {
  const [scenarios, setScenarios] = useState<JointScenario[]>([])
  const [runs, setRuns] = useState<SavedRun[]>([])
  const [loadError, setLoadError] = useState("")
  const [tab, setTab] = useState<Tab>("start")
  const [resultRunId, setResultRunId] = useState<string | null>(null)
  const { job, state, nowT, start, cancel } = useJointJob()

  const loadScenarios = useCallback(async () => {
    try { setScenarios(await jointApi.listScenarios()); setLoadError("") } catch (error) { setLoadError((error as Error).message) }
  }, [])
  const refreshRuns = useCallback(() => { jointApi.listRuns().then(setRuns).catch(() => setRuns([])) }, [])
  useEffect(() => { void loadScenarios(); refreshRuns() }, [loadScenarios, refreshRuns, reloadKey])

  // En körning som återupptas efter navigering visas direkt.
  useEffect(() => { if (job.status === "running" && job.events.length === 0 && job.jobId) setTab("result") }, [job.status, job.jobId])
  // En avslutad körning med resultat väljs automatiskt i Resultat.
  useEffect(() => { if ((job.status === "completed" || job.status === "cancelled") && job.runId) setResultRunId(job.runId) }, [job.status, job.runId])
  useEffect(() => { if (job.status !== "running" && job.runId) refreshRuns() }, [job.status, job.runId, refreshRuns])

  const begin = async (body: StartJointRunBody, changes: RunChangeText[]) => { await start(body, changes); setTab("result") }
  const busy = job.status === "running" || job.status === "starting"

  return <div className="max-w-6xl space-y-4">
    <p className="flex items-center gap-1.5 text-sm font-medium text-slate-900">Vad händer med kostnaden om jag ändrar det här?
      <InfoTip label="Så använder du sidan"><span className="block">Välj ett scenario, ändra de parametrar du vill, kör och jämför med förra körningen.</span><span className="block">Allt som visas är modellens kostnad, inte faktisk kostnad.</span></InfoTip></p>
    <Tabs.Root value={tab} onValueChange={value => setTab(value as Tab)}>
      <Tabs.List className="mb-4 flex gap-1 border-b" aria-label="Optimering">
        <Tabs.Trigger className={TRIGGER} value="start">1. Ställ in och kör</Tabs.Trigger>
        <Tabs.Trigger className={TRIGGER} value="result">2. Resultat{busy ? " (körning pågår)" : ""}</Tabs.Trigger>
      </Tabs.List>
      <Tabs.Content value="start" forceMount className="data-[state=inactive]:hidden">
        <StartPanel scenarios={scenarios} loadError={loadError} busy={busy} onStart={begin} onOpenUnderlay={onOpenUnderlay} onSaved={async () => { await loadScenarios() }}/>
      </Tabs.Content>
      <Tabs.Content value="result"><ResultView runId={resultRunId} runs={runs} scenarios={scenarios} onSelectRun={setResultRunId} live={{ job, state, nowT, onCancel: () => void cancel(), onOpenUnderlay }}/></Tabs.Content>
    </Tabs.Root>
  </div>
}
