import { Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { InfoTip } from "@/components/ui/info-tip"
import { conclusion } from "@/lib/diagnosisView"
import { useDiagnosis } from "@/lib/useDiagnosis"
import { ConstraintList, useScenarioParams } from "./constraint-list"

/** "Vad gick fel?" för en körning utan lösning: begränsningarna som gällde, och vilken av dina ändringar som gör problemet omöjligt. */
export function DiagnosisCard({ runId }: { runId: string }) {
  const { state, error, running, start } = useDiagnosis(runId)
  const { labels, show } = useScenarioParams(state?.scenario_id)

  if (error && !state) return <Card><CardContent className="pt-4 text-sm text-slate-900" role="status">Begränsningarna i körningen kan inte läsas: {error}</CardContent></Card>
  if (!state) return null
  const result = conclusion(state, labels)
  const progress = state.job?.progress
  return <Card>
    <CardHeader><CardTitle className="flex items-center gap-1.5">Vad gick fel?<InfoTip label="Så fungerar utredningen">Listan visar begränsningarna som gällde: det du själv ändrade och det scenariot "{state.scenario_name}" redan bär på. Utredningen löser scenariot om med bara en av dina ändringar i taget, högst {state.saved?.probe_seconds ?? 30} sekunder per prov. "Omöjlig ensam" är bevisat. "Oklart" betyder att varken lösning eller bevis hann hittas. Begränsningar som scenariot redan har provas inte, och ändringar som bara fungerar tillsammans hittas inte.</InfoTip></CardTitle></CardHeader>
    <CardContent className="space-y-3 text-sm text-slate-900">
      {result && !running && <p role="status" className={`rounded-md border p-3 font-semibold ${result.tone === "cause" ? "border-red-700 bg-red-50 text-red-950" : "border-slate-500 bg-slate-50"}`}>{result.text}</p>}
      <ConstraintList state={state} labels={labels} show={show}/>
      {state.changes.length > 0 && <div className="flex flex-wrap items-center gap-3">
        <Button type="button" disabled={running} onClick={() => void start()}>{running ? "Utreder …" : state.saved ? "Utred igen" : "Utred vilken ändring som orsakade det"}</Button>
      </div>}
      {running && <p className="flex items-center gap-2" role="status"><Loader2 size={15} className="animate-spin" aria-hidden="true"/>{progress ? `Prov ${Math.min(progress.done + 1, progress.total)} av ${progress.total}${progress.current ? `: ${progress.current}` : ""}` : "Startar utredningen …"}</p>}
      {state.job?.status === "failed" && !running && <p className="text-red-900" role="alert">Utredningen misslyckades: {state.job.error}</p>}
      {error && state && <p className="text-red-900" role="alert">{error}</p>}
    </CardContent>
  </Card>
}

/** För en körning med lösning: samma begränsningar, hopfällda. */
export function ConstraintsFold({ runId }: { runId: string }) {
  const { state } = useDiagnosis(runId)
  const { labels, show } = useScenarioParams(state?.scenario_id)
  if (!state || state.constraints.length === 0) return null
  return <details className="rounded-lg border bg-white">
    <summary className="cursor-pointer p-3 text-base font-bold">Begränsningar i körningen</summary>
    <div className="space-y-2 p-3 pt-0 text-sm"><ConstraintList state={state} labels={labels} show={show}/></div>
  </details>
}
