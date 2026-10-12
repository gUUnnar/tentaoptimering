import { useEffect, useMemo, useState } from "react"
import { CircleAlert, Clock, Info, Play } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ApiError } from "@/lib/jointApi"
import { runtimeEstimate } from "@/lib/jointScenarioInfo"
import type { RunChangeText } from "@/lib/jointJobMemory"
import type { JointScenario, StartJointRunBody } from "@/lib/jointTypes"
import { DEFAULT_RUN_OPTIONS, runOptionsValid, toStartBody, type RunOptions } from "@/lib/runOptions"
import { useParameterEditor } from "@/lib/useParameterEditor"
import { ParamList } from "./params/param-list"
import { RunOptionsPanel } from "./run-options"
import { SaveScenario } from "./save-scenario"
import { ScenarioPicker } from "./scenario-picker"

type Props = {
  scenarios: JointScenario[]
  loadError: string
  busy: boolean
  onStart: (body: StartJointRunBody, changes: RunChangeText[]) => Promise<void>
  onSaved: (scenario: JointScenario) => Promise<void>
}

export function StartPanel({ scenarios, loadError, busy, onStart, onSaved }: Props) {
  const [scenarioId, setScenarioId] = useState("")
  const [options, setOptions] = useState<RunOptions>(DEFAULT_RUN_OPTIONS)
  const [submitting, setSubmitting] = useState(false)
  const [startError, setStartError] = useState("")
  const editor = useParameterEditor(scenarioId)

  useEffect(() => {
    if (!scenarios.length) return
    setScenarioId(current => current && scenarios.some(item => item.id === current) ? current : scenarios[0].id)
  }, [scenarios])
  useEffect(() => { setOptions(current => ({ ...current, specific: "" })); setStartError("") }, [scenarioId])

  const scenario = scenarios.find(item => item.id === scenarioId)
  const estimate = runtimeEstimate(scenario?.subset?.exam_count)
  const ready = editor.load.status === "ready"
  const optionsOk = runOptionsValid(options)
  const problems = useMemo(() => editor.params.filter(param => editor.errors[param.id]).map(param => ({ id: param.id, label: param.label, message: editor.errors[param.id] })), [editor.params, editor.errors])
  const canStart = !busy && !submitting && !!scenarioId && ready && !editor.hasErrors && optionsOk
  const why = busy ? "En körning pågår redan." : !ready ? "Parametrarna har inte hämtats än." : editor.hasErrors ? "Rätta felen i parametrarna först." : !optionsOk ? "Rätta valen för start och resurser först." : null

  const changeScenario = (id: string) => {
    if (id === scenarioId) return
    if (editor.changes.length && !window.confirm(`Dina ${editor.changes.length} ändringar går förlorade om du byter scenario. Vill du byta ändå?`)) return
    setScenarioId(id)
  }

  const submit = async () => {
    if (!canStart) return
    setSubmitting(true); setStartError("")
    const texts = editor.changes.filter(change => !change.error).map(({ id, label, oldText, newText }) => ({ id, label, oldText, newText }))
    try { await onStart(toStartBody(scenarioId, options, editor.request), texts) }
    catch (error) {
      if (error instanceof ApiError && error.errors.length) { editor.applyServerErrors(error.errors); setStartError("Servern avvisade några parametervärden. Se markeringarna vid raderna ovan.") }
      else setStartError((error as Error).message)
    } finally { setSubmitting(false) }
  }

  const saveDisabled = !ready ? "Parametrarna har inte hämtats än." : editor.changes.length === 0 ? "Gör minst en ändring först." : editor.hasErrors ? "Rätta felen i parametrarna först." : null

  return <div className="space-y-4">
    <Card>
      <CardHeader><CardTitle>1. Välj scenario</CardTitle></CardHeader>
      <CardContent><ScenarioPicker scenarios={scenarios} value={scenarioId} onChange={changeScenario} loadError={loadError}/></CardContent>
    </Card>

    <section aria-label="Parametrar" className="space-y-3">
      <div>
        <h2 className="text-sm font-semibold">2. Ändra parametrar (valfritt)</h2>
        <p className="mt-0.5 text-xs text-slate-800">Det du ändrar gäller bara den här körningen och ändrar aldrig originalscenariot. Du kan spara dina ändringar som ett nytt scenario längst ner.</p>
      </div>
      {editor.load.status === "loading" && <p className="text-sm text-slate-800" role="status">Hämtar parametrar …</p>}
      {editor.load.status === "error" && <div className="flex items-start gap-2 rounded-md border border-red-700 bg-red-50 p-3 text-sm text-red-900" role="alert">
        <CircleAlert size={18} className="mt-0.5 shrink-0" aria-hidden="true"/>
        <div><p>Kunde inte hämta parametrarna: {editor.load.error}</p><Button type="button" size="sm" variant="outline" className="mt-2" onClick={editor.reload}>Försök igen</Button></div>
      </div>}
      {ready && <ParamList editor={editor}/>}
    </section>

    <Card>
      <CardHeader><CardTitle>3. Starta</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <RunOptionsPanel problemId={scenario?.problem_id ?? ""} options={options} onChange={setOptions} hasChanges={editor.changes.length > 0}/>
        {estimate && <p className="flex items-start gap-2 rounded-md bg-slate-100 p-2.5 text-sm text-slate-900"><Clock size={16} className="mt-0.5 shrink-0" aria-hidden="true"/>{estimate.text}</p>}
        {problems.length > 0 && <div role="alert" className="rounded-md border-2 border-red-700 bg-red-50 p-3 text-sm text-red-900">
          <p className="font-semibold">{problems.length} {problems.length === 1 ? "parameter behöver rättas" : "parametrar behöver rättas"}:</p>
          <ul className="mt-1 list-disc pl-5">{problems.map(item => <li key={item.id}><strong>{item.label}:</strong> {item.message}</li>)}</ul>
        </div>}
        {startError && <p role="alert" className="flex items-start gap-1.5 text-sm text-red-900"><CircleAlert size={16} className="mt-0.5 shrink-0" aria-hidden="true"/>{startError}</p>}
        <div className="flex flex-wrap items-start gap-4">
          <div>
            <Button type="button" size="lg" disabled={!canStart} onClick={() => void submit()} aria-describedby="start-why"><Play size={15} className="mr-1" aria-hidden="true"/>{submitting ? "Startar …" : "Kör"}</Button>
            <p id="start-why" className="mt-1 text-xs text-slate-800">{why ?? (editor.changes.length ? (editor.changes.length === 1 ? "Körs med din ändring." : `Körs med dina ${editor.changes.length} ändringar.`) : "Körs med scenariots egna värden.")}</p>
          </div>
          <SaveScenario baseId={scenarioId} baseName={scenario?.name ?? ""} parameters={editor.request} changeCount={editor.changes.length} disabledReason={saveDisabled}
            onSaved={async saved => { await onSaved(saved); setScenarioId(saved.id) }}/>
        </div>
        <p className="flex items-start gap-1.5 text-xs text-slate-800"><Info size={14} className="mt-0.5 shrink-0" aria-hidden="true"/>Resultatet är en modellkostnad, inte faktisk kostnad. Parametrar som är märkta "Antagande" saknar verifierat underlag.</p>
      </CardContent>
    </Card>
  </div>
}
