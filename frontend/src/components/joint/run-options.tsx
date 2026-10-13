import { useEffect, useId, useState } from "react"
import { ShieldCheck } from "lucide-react"
import { jointApi } from "@/lib/jointApi"
import { formatKr, outcomeLabel } from "@/lib/jointFormat"
import type { WarmStartCandidate } from "@/lib/jointTypes"
import { checkRunOptions, type RunOptions, type WarmMode } from "@/lib/runOptions"
import { VerdictChip } from "./status-chip"

type Props = { problemId: string; options: RunOptions; onChange: (options: RunOptions) => void; hasChanges: boolean }

/** Start från förra körningen och datorresurser. Inga verksamhetsparametrar. */
export function RunOptionsPanel({ problemId, options, onChange, hasChanges }: Props) {
  const id = useId()
  const [candidates, setCandidates] = useState<WarmStartCandidate[] | null>(null)
  const [candidateError, setCandidateError] = useState("")
  const check = checkRunOptions(options)
  const set = (patch: Partial<RunOptions>) => onChange({ ...options, ...patch })

  useEffect(() => {
    if (!problemId) return
    let cancelled = false
    setCandidates(null); setCandidateError("")
    jointApi.listCandidates(problemId)
      .then(list => { if (!cancelled) setCandidates(list) })
      .catch(error => { if (!cancelled) { setCandidates([]); setCandidateError((error as Error).message) } })
    return () => { cancelled = true }
  }, [problemId])

  return <div className="space-y-4">
    <fieldset className="space-y-2">
      <legend className="text-sm font-semibold">Startar från förra körningen</legend>
      <div className="flex items-start gap-2 rounded-md bg-sky-50 p-2.5 text-xs text-sky-950" role="note">
        <ShieldCheck size={15} className="mt-0.5 shrink-0" aria-hidden="true"/>
        <span>En tidigare placering <strong>kontrolleras alltid på nytt mot de nya reglerna</strong> innan den används. Sparad status räknas inte som bevis, och en placering som inte längre går att genomföra används inte. {hasChanges ? "Du har ändrat parametrar, så kontrollen kan underkänna förra körningens placering helt eller delvis." : ""}</span>
      </div>
      <Radio group={id} value="auto" mode={options.mode} onSelect={mode => set({ mode })} label="Automatiskt" help="Använder den senaste lämpliga körningen av samma scenario, om det finns någon."/>
      <Radio group={id} value="none" mode={options.mode} onSelect={mode => set({ mode })} label="Ingen" help="Modellen börjar från noll. Ger en renare jämförelse men tar längre tid."/>
      <Radio group={id} value="specific" mode={options.mode} onSelect={mode => set({ mode })} label="Specifik körning" help="Välj själv vilken tidigare körning som ska kontrolleras."/>
      {options.mode === "specific" && <div className="ml-6 space-y-1.5" role="radiogroup" aria-label="Tidigare körningar att starta från">
        {candidates === null && <p className="text-xs text-slate-800" role="status">Hämtar tidigare körningar …</p>}
        {candidateError && <p className="text-xs text-red-800" role="alert">Kunde inte hämta tidigare körningar: {candidateError}</p>}
        {candidates?.length === 0 && !candidateError && <p className="text-xs text-slate-800">Det finns inga sparade körningar av det här scenariot.</p>}
        {candidates?.map(item => <label key={item.run_id} className={`flex items-start gap-2 rounded-md border p-2 text-xs ${item.has_placement ? "cursor-pointer hover:border-sky-700" : "opacity-70"} ${options.specific === item.run_id ? "border-sky-700 bg-sky-50" : ""}`}>
          <input type="radio" name={`${id}-candidate`} className="mt-0.5" disabled={!item.has_placement} checked={options.specific === item.run_id} onChange={() => set({ specific: item.run_id })}/>
          <span className="space-y-0.5">
            <span className="block font-mono text-[11px]">{item.run_id}</span>
            <span className="block">Verifierad kostnad {formatKr(item.cost_ore)} · {outcomeLabel(item.solver_outcome)}</span>
            <span className="flex flex-wrap items-center gap-1.5">Teknisk eftervalidering när den sparades: <VerdictChip status={item.stored_technical_validation}/> <span className="text-slate-800">(kontrolleras om nu)</span></span>
            {!item.has_placement && <span className="block text-amber-900">Saknar sparad placering och kan inte användas.</span>}
          </span>
        </label>)}
      </div>}
      {check.warm && <p className="text-xs text-amber-900" role="alert">{check.warm}</p>}
    </fieldset>

    <details className="rounded-md border p-3">
      <summary className="cursor-pointer rounded text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-700">Avancerat: datorns resurser</summary>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div>
          <label className="label" htmlFor={`${id}-threads`}>Beräkningstrådar (0 = automatiskt)</label>
          <input id={`${id}-threads`} className="field" inputMode="numeric" value={options.threads} onChange={event => set({ threads: event.target.value })} aria-invalid={!!check.threads} aria-describedby={`${id}-threads-help`}/>
          <p id={`${id}-threads-help`} className={`mt-1 text-xs ${check.threads ? "text-red-800" : "text-slate-800"}`}>{check.threads ?? "Hur många processorkärnor beräkningen får använda. 0 låter modellen välja."}</p>
        </div>
        <div>
          <label className="label" htmlFor={`${id}-memory`}>Minne i MB (tomt = ingen gräns)</label>
          <input id={`${id}-memory`} className="field" inputMode="numeric" value={options.memory} placeholder="Ingen gräns" onChange={event => set({ memory: event.target.value })} aria-invalid={!!check.memory} aria-describedby={`${id}-memory-help`}/>
          <p id={`${id}-memory-help`} className={`mt-1 text-xs ${check.memory ? "text-red-800" : "text-slate-800"}`}>{check.memory ?? "Övre gräns för hur mycket minne beräkningen får använda."}</p>
        </div>
      </div>
      <label className="mt-3 flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={options.parallel} onChange={event => set({ parallel: event.target.checked })}/>
        <span>Kontrollera flera dagar samtidigt<span className="block text-xs text-slate-800">Ger oftast kortare tid. Resultatet för varje dag ska vara detsamma.</span></span></label>
    </details>
  </div>
}

function Radio({ group, value, mode, onSelect, label, help }: { group: string; value: WarmMode; mode: WarmMode; onSelect: (mode: WarmMode) => void; label: string; help: string }) {
  return <label className="flex cursor-pointer items-start gap-2 text-sm"><input type="radio" name={`${group}-warm`} className="mt-1" checked={mode === value} onChange={() => onSelect(value)}/><span>{label}<span className="block text-xs text-slate-800">{help}</span></span></label>
}
