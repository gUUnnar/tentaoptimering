import { useCallback, useEffect, useMemo, useState } from "react"
import * as Tabs from "@radix-ui/react-tabs"
import { abcApi } from "@/lib/abcApi"
import type { AbcRun } from "@/lib/abcTypes"
import { BASE_SCENARIO_ID, runsAsScenarios, scenarioIdForRun } from "@/lib/abcView"
import { jointApi } from "@/lib/jointApi"
import type { RunChangeText } from "@/lib/jointJobMemory"
import type { JointScenario, SavedRun, StartJointRunBody } from "@/lib/jointTypes"
import { useJointJob } from "@/lib/useJointJob"
import { AbcPage } from "@/components/abc/abc-page"
import { ResultView } from "./result-view"
import { StartPanel } from "./start-panel"
import { InfoTip } from "@/components/ui/info-tip"

type Tab = "overview" | "start" | "result"
const TRIGGER = "rounded-t-md border-b-2 border-transparent px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-700 data-[state=active]:border-sky-800 data-[state=active]:text-sky-900"

/** Sidan "Optimering": A (faktisk bokning), B (grundoptimering) och C (egna körningar): översikt och jämförelse, ställ in och kör, resultat. */
export default function JointPage({ onOpenUnderlay, reloadKey }: { onOpenUnderlay: () => void; reloadKey: number }) {
  const [scenarios, setScenarios] = useState<JointScenario[]>([])
  const [runs, setRuns] = useState<SavedRun[]>([])
  const [abcRuns, setAbcRuns] = useState<AbcRun[]>([])
  const [runsVersion, setRunsVersion] = useState(0)
  const [loadError, setLoadError] = useState("")
  const [startError, setStartError] = useState("")
  const [tab, setTab] = useState<Tab>("overview")
  const [resultRunId, setResultRunId] = useState<string | null>(null)
  const [baseRequest, setBaseRequest] = useState<{ id: string; nonce: number } | null>(null)
  const [compareRequest, setCompareRequest] = useState<{ ref: string; nonce: number } | null>(null)
  const { job, state, nowT, start, cancel } = useJointJob()

  const loadScenarios = useCallback(async () => {
    try { setScenarios(await jointApi.listScenarios()); setLoadError("") } catch (error) { setLoadError((error as Error).message) }
  }, [])
  const refreshRuns = useCallback(() => {
    jointApi.listRuns().then(setRuns).catch(() => setRuns([]))
    abcApi.runs().then(setAbcRuns).catch(() => setAbcRuns([]))
    setRunsVersion(version => version + 1)
  }, [])
  useEffect(() => { void loadScenarios(); refreshRuns() }, [loadScenarios, refreshRuns, reloadKey])

  // En körning som återupptas efter navigering visas direkt.
  useEffect(() => { if (job.status === "running" && job.events.length === 0 && job.jobId) setTab("result") }, [job.status, job.jobId])
  // En avslutad körning med resultat väljs automatiskt i Resultat.
  useEffect(() => { if ((job.status === "completed" || job.status === "cancelled") && job.runId) setResultRunId(job.runId) }, [job.status, job.runId])
  useEffect(() => { if (job.status !== "running" && job.runId) refreshRuns() }, [job.status, job.runId, refreshRuns])

  const begin = async (body: StartJointRunBody, changes: RunChangeText[]) => { await start(body, changes); setTab("result") }
  const busy = job.status === "running" || job.status === "starting"
  // Utgångspunkter: B och egna sparade uppsättningar från servern, och tidigare körningar som egna poster. Utvecklingsscenarier visas inte.
  const startScenarios = useMemo(() => [...scenarios.filter(item => !item.hidden), ...runsAsScenarios(abcRuns, scenarios)], [scenarios, abcRuns])

  const runBase = async () => {
    setStartError("")
    try { await begin({ scenario: BASE_SCENARIO_ID, warm_start: "auto", threads: 0, memory_mb: null, parallel_day_checks: true }, []) }
    catch (error) { setStartError((error as Error).message) }
  }
  const newRun = (basedOn: string | null) => { setBaseRequest({ id: basedOn ? scenarioIdForRun(basedOn) : BASE_SCENARIO_ID, nonce: Date.now() }); setTab("start") }
  const openResult = (runId: string) => { setResultRunId(runId); setTab("result") }
  const openCompare = (runId: string) => { setCompareRequest({ ref: runId, nonce: Date.now() }); setTab("overview") }

  return <div className="max-w-6xl space-y-4">
    <p className="flex items-center gap-1.5 text-sm font-medium text-slate-900">Vad händer med lokaler och kostnad om jag ändrar ett villkor?
      <InfoTip label="Så använder du sidan"><span className="block">A är den faktiska bokningen, B är grundoptimeringen utifrån verksamhetens önskemål, C är dina egna körningar.</span><span className="block">Ändra ett villkor, kör, och jämför med A, B och tidigare körningar. Tidigare körningar sparas och skrivs aldrig över.</span><span className="block">Allt som visas är modellens kostnad, inte faktisk kostnad.</span></InfoTip></p>
    <Tabs.Root value={tab} onValueChange={value => setTab(value as Tab)}>
      <Tabs.List className="mb-4 flex gap-1 border-b" aria-label="Optimering">
        <Tabs.Trigger className={TRIGGER} value="overview">1. A, B, C och jämförelse</Tabs.Trigger>
        <Tabs.Trigger className={TRIGGER} value="start">2. Ställ in och kör</Tabs.Trigger>
        <Tabs.Trigger className={TRIGGER} value="result">3. Resultat{busy ? " (körning pågår)" : ""}</Tabs.Trigger>
      </Tabs.List>
      <Tabs.Content value="overview">
        {startError && <p role="alert" className="mb-3 rounded-md bg-red-50 p-2 text-sm text-red-900">{startError}</p>}
        <AbcPage reloadKey={runsVersion + reloadKey} busy={busy} onRunBase={() => void runBase()} onNewRun={newRun} onOpenResult={openResult} compareRequest={compareRequest}/>
      </Tabs.Content>
      <Tabs.Content value="start" forceMount className="data-[state=inactive]:hidden">
        <StartPanel scenarios={startScenarios} loadError={loadError} busy={busy} onStart={begin} onOpenUnderlay={onOpenUnderlay} onSaved={async () => { await loadScenarios() }} baseRequest={baseRequest}/>
      </Tabs.Content>
      <Tabs.Content value="result"><ResultView runId={resultRunId} runs={runs} scenarios={scenarios} onSelectRun={setResultRunId} onCompare={openCompare} live={{ job, state, nowT, onCancel: () => void cancel(), onOpenUnderlay }}/></Tabs.Content>
    </Tabs.Root>
  </div>
}
