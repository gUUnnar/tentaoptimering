import { useEffect, useMemo, useState } from "react"
import { CircleAlert, Play } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ApiError } from "@/lib/jointApi"
import { defaultScenarioId, runtimeEstimate } from "@/lib/jointScenarioInfo"
import { isMissingUnderlayMessage, scenarioNeedsUnderlay } from "@/lib/underlay"
import type { RunChangeText } from "@/lib/jointJobMemory"
import type { JointScenario, StartJointRunBody } from "@/lib/jointTypes"
import { DEFAULT_RUN_OPTIONS, runOptionsValid, toStartBody, type RunOptions } from "@/lib/runOptions"
import { periodRunnable, type PeriodChoice } from "@/lib/period"
import { useParameterEditor } from "@/lib/useParameterEditor"
import { usePrecheck } from "@/lib/usePrecheck"
import { useUnderlayInfo } from "@/lib/useUnderlayInfo"
import { usePeriod } from "@/lib/usePeriod"
import { PeriodPicker } from "./period-picker"
import { PrecheckResult } from "./precheck-result"
import { ParamsHeading, ParamsSection } from "./params/params-section"
import { RunOptionsPanel } from "./run-options"
import { SaveScenario } from "./save-scenario"
import { ScenarioFacts } from "./scenario-facts"
import { ScenarioSelect } from "./scenario-picker"
import { UnderlayNotice } from "./underlay-notice"
import { InfoTip } from "@/components/ui/info-tip"

type Props = {
  scenarios: JointScenario[]
  loadError: string
  busy: boolean
  onStart: (body: StartJointRunBody, changes: RunChangeText[]) => Promise<void>
  onSaved: (scenario: JointScenario) => Promise<void>
  onOpenUnderlay: () => void
}

export function StartPanel({ scenarios, loadError, busy, onStart, onSaved, onOpenUnderlay }: Props) {
  const [scenarioId, setScenarioId] = useState("")
  const [options, setOptions] = useState<RunOptions>(DEFAULT_RUN_OPTIONS)
  const [submitting, setSubmitting] = useState(false)
  const [startError, setStartError] = useState("")
  const [period, setPeriod] = useState<PeriodChoice | null>(null)
  const editor = useParameterEditor(scenarioId, scenarios)
  const periodState = usePeriod(scenarioId, period)
  const underlay = useUnderlayInfo(scenarios)
  const precheck = usePrecheck(JSON.stringify([scenarioId, editor.request, period]))

  useEffect(() => {
    if (!scenarios.length) return
    setScenarioId(current => current && scenarios.some(item => item.id === current) ? current : defaultScenarioId(scenarios))
  }, [scenarios])
  useEffect(() => { setOptions(current => ({ ...current, specific: "" })); setStartError(""); setPeriod(null) }, [scenarioId])

  const scenario = scenarios.find(item => item.id === scenarioId)
  const estimate = runtimeEstimate(scenario?.subset?.exam_count)
  const ready = editor.load.status === "ready"
  const optionsOk = runOptionsValid(options)
  const problems = useMemo(() => editor.params.filter(param => editor.errors[param.id]).map(param => ({ id: param.id, label: param.label, message: editor.errors[param.id] })), [editor.params, editor.errors])
  const missingUnderlay = scenarioNeedsUnderlay(scenario) || isMissingUnderlayMessage(startError) || isMissingUnderlayMessage(loadError)
  const namedExams = scenario?.subset?.selection === "event_list"
  const periodOk = periodRunnable(period, periodState.check)
  const checking = precheck.status === "running"
  const canStart = !busy && !submitting && !checking && !!scenarioId && ready && !editor.hasErrors && optionsOk && periodOk && !scenarioNeedsUnderlay(scenario)
  const why = busy ? "En körning pågår redan." : scenarioNeedsUnderlay(scenario) ? "Förbered underlaget under Underlag först." : !ready ? "Parametrarna har inte hämtats än." : editor.hasErrors ? "Rätta felen i parametrarna först." : !optionsOk ? "Rätta valen för start och resurser först." : !periodOk ? (periodState.check?.partial && !period?.accept ? "Godkänn den kortare perioden först." : "Välj en period som går att planera först.") : null

  const canCheck = !busy && !submitting && !checking && !!scenarioId && ready && !editor.hasErrors && periodOk && !scenarioNeedsUnderlay(scenario)

  const changeScenario = (id: string) => {
    if (id === scenarioId) return
    if (editor.changes.length && !window.confirm(`Dina ${editor.changes.length} ändringar går förlorade om du byter scenario. Vill du byta ändå?`)) return
    setScenarioId(id)
  }

  const submit = async () => {
    if (!canStart) return
    setSubmitting(true); setStartError("")
    const texts = editor.changes.filter(change => !change.error).map(({ id, label, oldText, newText }) => ({ id, label, oldText, newText }))
    if (period) texts.unshift({ id: "period", label: "Planeringsperiod", oldText: "Scenariots egen period", newText: `${period.from} – ${period.to}` })
    try { await onStart(toStartBody(scenarioId, options, editor.request, period), texts) }
    catch (error) {
      if (error instanceof ApiError && error.errors.length) { editor.applyServerErrors(error.errors); setStartError("Servern avvisade några parametervärden. Se markeringarna vid raderna ovan.") }
      else setStartError((error as Error).message)
    } finally { setSubmitting(false) }
  }

  const saveDisabled = !ready ? "Parametrarna har inte hämtats än." : editor.changes.length === 0 ? "Gör minst en ändring först." : editor.hasErrors ? "Rätta felen i parametrarna först." : null

  const showChanges = () => {
    const row = document.querySelector<HTMLElement>('[data-changed="true"]')
    row?.closest("details")?.setAttribute("open", "") // en ändrad parameter under "Fler parametrar" ska synas
    row?.scrollIntoView({ block: "center", behavior: "smooth" })
  }

  return <div className="space-y-4">
    {missingUnderlay && <UnderlayNotice onOpen={onOpenUnderlay}/>}
    {/* Fast rad högst upp: scenariot, vad som körs, antalet ändringar och Kör finns kvar när man bläddrar bland parametrarna. */}
    <Card className="sticky top-0 z-20 shadow-md" aria-label="Scenario och start">
      <CardContent className="space-y-2 pt-4">
        <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
          <div className="min-w-[18rem] flex-1"><ScenarioSelect scenarios={scenarios} value={scenarioId} onChange={changeScenario} loadError={isMissingUnderlayMessage(loadError) ? "" : loadError}/></div>
          <div className="flex flex-col items-end gap-1">
            <div className="flex flex-wrap items-center justify-end gap-3">
              <p className="text-sm font-semibold" role="status" aria-live="polite">
                {editor.changes.length === 0 ? "Inga ändringar" : `${editor.changes.length} ${editor.changes.length === 1 ? "ändring" : "ändringar"}`}
                {editor.changes.length > 0 && <>
                  <button type="button" onClick={showChanges} className="ml-2 rounded text-xs font-medium underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-slate-900">Visa</button>
                  <button type="button" onClick={editor.resetAll} className="ml-2 rounded text-xs font-medium underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-slate-900">Återställ alla</button></>}
              </p>
              {estimate && <InfoTip label="Hur lång tid tar körningen?" align="right">{estimate.text}</InfoTip>}
              <Button type="button" size="lg" variant="outline" disabled={!canCheck} onClick={() => void precheck.run(toStartBody(scenarioId, options, editor.request, period))}>{checking ? "Kontrollerar …" : "Kontrollera"}</Button>
              <Button type="button" size="lg" disabled={!canStart} onClick={() => void submit()} aria-describedby={why ? "start-why" : undefined}><Play size={15} className="mr-1" aria-hidden="true"/>{submitting ? "Startar …" : "Kör"}</Button>
            </div>
            {why && <p id="start-why" className="text-xs text-slate-800">{why}</p>}
          </div>
        </div>
        <ScenarioFacts scenario={scenario} choice={period} check={periodState.check} coverage={periodState.coverage} underlay={underlay}/>
        <PrecheckResult state={precheck}/>
      </CardContent>
    </Card>
    {problems.length > 0 && <div role="alert" className="rounded-md border border-red-700 bg-red-50 p-3 text-sm text-red-900">
      <p className="font-semibold">{problems.length} {problems.length === 1 ? "parameter behöver rättas" : "parametrar behöver rättas"}:</p>
      <ul className="mt-1 list-disc pl-5">{problems.map(item => <li key={item.id}><strong>{item.label}:</strong> {item.message}</li>)}</ul>
    </div>}
    {startError && !isMissingUnderlayMessage(startError) && <p role="alert" className="flex items-start gap-1.5 text-sm text-red-900"><CircleAlert size={16} className="mt-0.5 shrink-0" aria-hidden="true"/>{startError}</p>}

    <Card><CardContent className="pt-4"><PeriodPicker state={periodState} choice={period} onChange={setPeriod} disabledReason={namedExams ? "Det här scenariot anger namngivna tentor och tar inget periodval." : null}/></CardContent></Card>

    <section aria-label="Parametrar" className="space-y-3">
      <ParamsHeading/>
      {editor.load.status === "loading" && <p className="text-sm text-slate-800" role="status">Hämtar parametrar …</p>}
      {editor.load.status === "error" && <div className="flex items-start gap-2 rounded-md border border-red-700 bg-red-50 p-3 text-sm text-red-900" role="alert">
        <CircleAlert size={18} className="mt-0.5 shrink-0" aria-hidden="true"/>
        <div><p>Kunde inte hämta parametrarna: {editor.load.error}</p><Button type="button" size="sm" variant="outline" className="mt-2" onClick={editor.reload}>Försök igen</Button></div>
      </div>}
      {ready && <ParamsSection editor={editor} onOpenUnderlay={onOpenUnderlay}/>}
    </section>

    <details className="rounded-lg border bg-white">
      <summary className="cursor-pointer p-3 text-base font-bold">Körningsinställningar och spara som scenario</summary>
      <div className="space-y-4 p-3 pt-0">
        <RunOptionsPanel problemId={scenario?.problem_id ?? ""} options={options} onChange={setOptions} hasChanges={editor.changes.length > 0}/>
        <SaveScenario baseId={scenarioId} baseName={scenario?.name ?? ""} parameters={editor.request} changeCount={editor.changes.length} disabledReason={saveDisabled}
          onSaved={async saved => { await onSaved(saved); setScenarioId(saved.id) }}/>
      </div>
    </details>
  </div>
}
