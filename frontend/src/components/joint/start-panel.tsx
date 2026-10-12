import { useEffect, useId, useState, type FormEvent } from "react"
import { Play, ShieldCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { JointApi } from "@/lib/jointApi"
import { formatKr, outcomeLabel } from "@/lib/jointFormat"
import type { JointScenario, StartJointRunBody, WarmStartCandidate } from "@/lib/jointTypes"
import { VerdictChip } from "./status-chip"

type Mode = "auto" | "none" | "specific"

export function StartPanel({ api, scenarios, busy, onStart }: { api: JointApi; scenarios: JointScenario[]; busy: boolean; onStart: (body: StartJointRunBody) => void }) {
  const id = useId()
  const [scenario, setScenario] = useState("")
  const [mode, setMode] = useState<Mode>("auto")
  const [specific, setSpecific] = useState("")
  const [candidates, setCandidates] = useState<WarmStartCandidate[] | null>(null)
  const [candidateError, setCandidateError] = useState("")
  const [threads, setThreads] = useState("0")
  const [memory, setMemory] = useState("")
  const [parallel, setParallel] = useState(true)

  useEffect(() => {
    if (!scenarios.length) return
    setScenario(current => current && scenarios.some(item => item.id === current) ? current : scenarios[0].id)
  }, [scenarios])

  useEffect(() => {
    if (!scenario) return
    let cancelled = false
    setCandidates(null); setCandidateError(""); setSpecific("")
    api.listCandidates(scenario).then(list => { if (!cancelled) setCandidates(list) }).catch(error => { if (!cancelled) { setCandidates([]); setCandidateError((error as Error).message) } })
    return () => { cancelled = true }
  }, [api, scenario])

  const threadsValue = Number(threads)
  const threadsOk = threads.trim() !== "" && Number.isInteger(threadsValue) && threadsValue >= 0
  const memoryValue = memory.trim() === "" ? null : Number(memory)
  const memoryOk = memoryValue === null || (Number.isInteger(memoryValue) && memoryValue > 0)
  const warmOk = mode !== "specific" || specific !== ""
  const canStart = !busy && scenario !== "" && threadsOk && memoryOk && warmOk
  const selected = scenarios.find(item => item.id === scenario)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!canStart) return
    onStart({ scenario, warm_start: mode === "specific" ? specific : mode, threads: threadsValue, memory_mb: memoryValue, parallel_day_checks: parallel })
  }

  return <form onSubmit={submit} aria-label="Starta gemensam körning">
    <Card>
      <CardHeader><CardTitle>Starta gemensam körning</CardTitle></CardHeader>
      <CardContent className="space-y-5">
        <div>
          <label className="label" htmlFor={`${id}-scenario`}>Scenario</label>
          <select id={`${id}-scenario`} className="field max-w-xl" value={scenario} onChange={e => setScenario(e.target.value)} disabled={!scenarios.length}>
            {!scenarios.length && <option value="">Inga scenarier tillgängliga</option>}
            {scenarios.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          {selected && <p className="mt-1 text-xs text-slate-700">{selected.description}</p>}
        </div>

        <fieldset className="space-y-2">
          <legend className="label">Varmstart</legend>
          <div className="flex items-start gap-2 rounded-md bg-sky-50 p-2.5 text-xs text-sky-950" role="note">
            <ShieldCheck size={15} className="mt-0.5 shrink-0" aria-hidden="true"/>
            <span>Varmstarten kontrolleras <strong>alltid på nytt</strong> mot de nya reglerna. Sparad teknisk status används inte som bevis, och en placering som inte längre är tillåten används inte.</span>
          </div>
          <Radio name={`${id}-warm`} checked={mode === "auto"} onChange={() => setMode("auto")} label="Automatiskt" help="Välj bästa tillgängliga tidigare körning för samma problem, om någon finns."/>
          <Radio name={`${id}-warm`} checked={mode === "none"} onChange={() => setMode("none")} label="Ingen varmstart" help="Starta utan tidigare placering."/>
          <Radio name={`${id}-warm`} checked={mode === "specific"} onChange={() => setMode("specific")} label="Specifik körning" help="Välj en tidigare körning ur listan nedan."/>
          {mode === "specific" && <div className="ml-6 space-y-1.5" role="radiogroup" aria-label="Kandidater för varmstart">
            {candidates === null && <p className="text-xs text-slate-700">Hämtar kandidater …</p>}
            {candidateError && <p className="text-xs text-red-800">Kunde inte hämta kandidater: {candidateError}</p>}
            {candidates?.length === 0 && !candidateError && <p className="text-xs text-slate-700">Det finns inga sparade körningar för detta problem.</p>}
            {candidates?.map(item => <label key={item.run_id} className={`flex items-start gap-2 rounded-md border p-2 text-xs ${item.has_placement ? "cursor-pointer hover:border-sky-700" : "opacity-70"} ${specific === item.run_id ? "border-sky-700 bg-sky-50" : ""}`}>
              <input type="radio" name={`${id}-candidate`} className="mt-0.5" disabled={!item.has_placement} checked={specific === item.run_id} onChange={() => setSpecific(item.run_id)}/>
              <span className="space-y-0.5">
                <span className="block font-mono text-[11px]">{item.run_id}</span>
                <span className="block">Kostnad {formatKr(item.cost_ore)} · utfall {outcomeLabel(item.solver_outcome)}</span>
                <span className="flex flex-wrap items-center gap-1.5">Sparad teknisk status: <VerdictChip status={item.stored_technical_validation}/> <span className="text-slate-700">(från sparningstillfället, kontrolleras om)</span></span>
                {!item.has_placement && <span className="block text-amber-900">Saknar sparad placering och kan inte användas som varmstart.</span>}
              </span>
            </label>)}
          </div>}
        </fieldset>

        <details className="rounded-md border p-3">
          <summary className="cursor-pointer rounded text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-700">Avancerat: resurser</summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor={`${id}-threads`}>Trådar (0 = standard)</label>
              <input id={`${id}-threads`} className="field" inputMode="numeric" value={threads} onChange={e => setThreads(e.target.value)} aria-invalid={!threadsOk} aria-describedby={`${id}-threads-help`}/>
              <p id={`${id}-threads-help`} className={`mt-1 text-xs ${threadsOk ? "text-slate-700" : "text-red-800"}`}>{threadsOk ? "Antal CP-SAT-trådar totalt. 0 låter lösaren välja." : "Ange ett heltal som är 0 eller större."}</p>
            </div>
            <div>
              <label className="label" htmlFor={`${id}-memory`}>Minne i MB (tomt = ingen gräns)</label>
              <input id={`${id}-memory`} className="field" inputMode="numeric" value={memory} placeholder="Ingen gräns" onChange={e => setMemory(e.target.value)} aria-invalid={!memoryOk} aria-describedby={`${id}-memory-help`}/>
              <p id={`${id}-memory-help`} className={`mt-1 text-xs ${memoryOk ? "text-slate-700" : "text-red-800"}`}>{memoryOk ? "Övre gräns för lösarens minne." : "Ange ett positivt heltal eller lämna fältet tomt."}</p>
            </div>
          </div>
          <label className="mt-3 flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={parallel} onChange={e => setParallel(e.target.checked)}/><span>Parallella dagkontroller<span className="block text-xs text-slate-700">Flera dagar kontrolleras samtidigt med färre trådar var. Ger oftast kortare tid för små dagmodeller; utfallet per dag ska vara detsamma.</span></span></label>
        </details>

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={!canStart}><Play size={15} className="mr-1" aria-hidden="true"/>Starta gemensam körning</Button>
          {!warmOk && <span className="text-xs text-amber-900">Välj en körning ur listan eller ett annat varmstartsläge.</span>}
          {busy && <span className="text-xs text-slate-700">En körning pågår redan.</span>}
        </div>
      </CardContent>
    </Card>
  </form>
}

function Radio({ name, checked, onChange, label, help }: { name: string; checked: boolean; onChange: () => void; label: string; help: string }) {
  return <label className="flex cursor-pointer items-start gap-2 text-sm"><input type="radio" name={name} className="mt-1" checked={checked} onChange={onChange}/><span>{label}<span className="block text-xs text-slate-700">{help}</span></span></label>
}
