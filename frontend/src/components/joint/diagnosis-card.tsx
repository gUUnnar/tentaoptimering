import { useEffect, useState } from "react"
import { CircleCheck, CircleHelp, CircleX, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { jointApi } from "@/lib/jointApi"
import type { ParameterInfo } from "@/lib/jointTypes"
import type { ProbeKind } from "@/lib/diagnosisApi"
import { PROBE_HINT, PROBE_TEXT, changeLabel, conclusion, probeFor } from "@/lib/diagnosisView"
import { formatLooseValue, formatParamValue } from "@/lib/paramFormat"
import { useDiagnosis } from "@/lib/useDiagnosis"
import { InfoTip } from "@/components/ui/info-tip"

const CHIP: Record<ProbeKind, string> = {
  infeasible: "border-red-700 bg-red-50 text-red-900",
  solution: "border-emerald-700 bg-emerald-50 text-emerald-900",
  inconclusive: "border-amber-700 bg-amber-50 text-amber-900",
}
const CHIP_ICON: Record<ProbeKind, typeof CircleX> = { infeasible: CircleX, solution: CircleCheck, inconclusive: CircleHelp }

/** "Vad gick fel?" för en körning utan lösning: dina ändringar, och vilken av dem som gör problemet omöjligt. */
export function DiagnosisCard({ runId }: { runId: string }) {
  const { state, error, running, start } = useDiagnosis(runId)
  const [params, setParams] = useState<Record<string, ParameterInfo>>({})
  const scenarioId = state?.scenario_id
  useEffect(() => {
    if (!scenarioId) return
    jointApi.parameters(scenarioId).then(answer => setParams(Object.fromEntries(answer.parameters.map(param => [param.id, param])))).catch(() => setParams({}))
  }, [scenarioId])
  const labels = Object.fromEntries(Object.values(params).map(param => [param.id, param.label]))
  const show = (id: string, value: unknown) => params[id] ? formatParamValue(params[id], value) : formatLooseValue({ id, unit: null }, value)

  if (error && !state) return <Card><CardContent className="pt-4 text-sm text-slate-900" role="status">Ändringarna i körningen kan inte utredas: {error}</CardContent></Card>
  if (!state) return null
  const result = conclusion(state, labels)
  const progress = state.job?.progress
  return <Card>
    <CardHeader><CardTitle className="flex items-center gap-1.5">Vad gick fel?<InfoTip label="Så fungerar utredningen">Utredningen löser scenariot om med bara en av dina ändringar i taget, högst {state?.saved?.probe_seconds ?? 30} sekunder per prov. "Omöjlig ensam" är bevisat. "Oklart" betyder att varken lösning eller bevis hann hittas.</InfoTip></CardTitle></CardHeader>
    <CardContent className="space-y-3 text-sm text-slate-900">
      {result && !running && <p role="status" className={`rounded-md border p-3 font-semibold ${result.tone === "cause" ? "border-red-700 bg-red-50 text-red-950" : "border-slate-500 bg-slate-50"}`}>{result.text}</p>}
      {state.changes.length === 0
        ? <p>Du ändrade inga parametrar. Scenariot "{state.scenario_name}" saknar lösning med de här tentorna och reglerna.</p>
        : <>
          <p>Det här ändrade du jämfört med scenariot "{state.scenario_name}":</p>
          <ul className="divide-y rounded-md border" aria-label="Dina ändringar">
            {state.changes.map(change => {
              const probe = probeFor(state, change.id)
              const Icon = probe ? CHIP_ICON[probe.kind] : null
              return <li key={change.id} className="flex flex-wrap items-center justify-between gap-2 p-2.5">
                <div><div className="font-medium">{changeLabel(change, labels)}</div>
                  <div className="text-xs text-slate-800">{show(change.id, change.baseline)} → <strong>{show(change.id, change.run)}</strong></div></div>
                {probe && Icon && <span title={PROBE_HINT[probe.kind]} className={`flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${CHIP[probe.kind]}`}><Icon size={13} aria-hidden="true"/>{PROBE_TEXT[probe.kind]}</span>}
              </li>
            })}
          </ul>
          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" disabled={running} onClick={() => void start()}>{running ? "Utreder …" : state.saved ? "Utred igen" : "Utred vilken ändring som orsakade det"}</Button>
          </div>
          {running && <p className="flex items-center gap-2" role="status"><Loader2 size={15} className="animate-spin" aria-hidden="true"/>{progress ? `Prov ${Math.min(progress.done + 1, progress.total)} av ${progress.total}${progress.current ? `: ${progress.current}` : ""}` : "Startar utredningen …"}</p>}
          {state.job?.status === "failed" && !running && <p className="text-red-900" role="alert">Utredningen misslyckades: {state.job.error}</p>}
        </>}
      {error && state && <p className="text-red-900" role="alert">{error}</p>}
    </CardContent>
  </Card>
}
