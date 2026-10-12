import { useCallback, useEffect, useState } from "react"
import * as Tabs from "@radix-ui/react-tabs"
import { FlaskConical, TriangleAlert } from "lucide-react"
import { loadJointApi, type JointApi } from "@/lib/jointApi"
import type { JointScenario, SavedRun, StartJointRunBody } from "@/lib/jointTypes"
import { useJointJob } from "@/lib/useJointJob"
import { LiveView } from "./live-view"
import { ResultView } from "./result-view"
import { StartPanel } from "./start-panel"

type Tab = "start" | "live" | "result"
const TRIGGER = "rounded-t-md border-b-2 border-transparent px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-700 data-[state=active]:border-sky-800 data-[state=active]:text-sky-900"

export default function JointPage() {
  const [api, setApi] = useState<JointApi | null>(null)
  const [scenarios, setScenarios] = useState<JointScenario[]>([])
  const [runs, setRuns] = useState<SavedRun[]>([])
  const [loadError, setLoadError] = useState("")
  const [tab, setTab] = useState<Tab>("start")
  const [resultRunId, setResultRunId] = useState<string | null>(null)
  const { job, state, nowT, start, cancel } = useJointJob(api)

  useEffect(() => { loadJointApi().then(setApi) }, [])

  const refreshRuns = useCallback(() => { api?.listRuns().then(setRuns).catch(() => setRuns([])) }, [api])
  useEffect(() => {
    if (!api) return
    api.listScenarios().then(list => { setScenarios(list); setLoadError("") }).catch(error => setLoadError((error as Error).message))
    refreshRuns()
  }, [api, refreshRuns])

  // Pågående jobb som återupptas efter navigering visas direkt i livevyn.
  useEffect(() => { if (job.status === "running" && tab === "start" && job.events.length === 0 && job.jobId) setTab("live") }, [job.status, job.jobId])
  useEffect(() => { if (job.status !== "running" && job.runId) refreshRuns() }, [job.status, job.runId, refreshRuns])

  const begin = (body: StartJointRunBody) => { setTab("live"); void start(body) }
  const showResult = (runId: string) => { setResultRunId(runId); setTab("result") }
  const busy = job.status === "running" || job.status === "starting"

  if (!api) return <p className="text-sm text-slate-700" role="status">Laddar gränssnittet för gemensam körning …</p>
  return <div className="max-w-6xl space-y-4">
    {api.mock && <div className="flex items-start gap-2 rounded-md border-2 border-sky-700 bg-sky-50 p-3 text-sm text-sky-950" role="note">
      <FlaskConical size={18} className="mt-0.5 shrink-0" aria-hidden="true"/>
      <p><strong>Mockläge (?mock=1).</strong> Allt på sidan är syntetiska exempeldata, inte resultat från en verklig körning. Ingen backend används. Ta bort <code>?mock=1</code> ur adressen för att använda det lokala API:et.</p>
    </div>}
    {loadError && <div className="flex items-start gap-2 rounded-md border border-red-700 bg-red-50 p-3 text-sm text-red-900" role="alert">
      <TriangleAlert size={18} className="mt-0.5 shrink-0" aria-hidden="true"/>
      <p>Kunde inte hämta scenarier för gemensam körning: {loadError}. Om API:et för gemensam körning inte är på plats ännu kan du granska gränssnittet med <code>?mock=1</code> i adressen.</p>
    </div>}
    <Tabs.Root value={tab} onValueChange={value => setTab(value as Tab)}>
      <Tabs.List className="mb-4 flex gap-1 border-b" aria-label="Gemensam körning">
        <Tabs.Trigger className={TRIGGER} value="start">Starta</Tabs.Trigger>
        <Tabs.Trigger className={TRIGGER} value="live">Pågående körning{busy ? " (pågår)" : ""}</Tabs.Trigger>
        <Tabs.Trigger className={TRIGGER} value="result">Resultat och uppspelning</Tabs.Trigger>
      </Tabs.List>
      <Tabs.Content value="start"><StartPanel api={api} scenarios={scenarios} busy={busy} onStart={begin}/></Tabs.Content>
      <Tabs.Content value="live"><LiveView job={job} state={state} nowT={nowT} mock={api.mock} onCancel={() => void cancel()} onShowResult={showResult}/></Tabs.Content>
      <Tabs.Content value="result"><ResultView api={api} runId={resultRunId} runs={runs} onSelectRun={setResultRunId}/></Tabs.Content>
    </Tabs.Root>
  </div>
}
