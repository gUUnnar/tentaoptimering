import { useEffect, useMemo, useState } from "react"
import { CircleCheck, CircleHelp, CircleX, PencilLine } from "lucide-react"
import type { DiagnosisChange, DiagnosisState, ProbeKind } from "@/lib/diagnosisApi"
import { PROBE_HINT, PROBE_TEXT, changeLabel, constraintRows, probeFor } from "@/lib/diagnosisView"
import { jointApi } from "@/lib/jointApi"
import type { ParameterInfo } from "@/lib/jointTypes"
import { formatLooseValue, formatParamValue } from "@/lib/paramFormat"

const CHIP: Record<ProbeKind, string> = {
  infeasible: "border-red-700 bg-red-50 text-red-900",
  solution: "border-emerald-700 bg-emerald-50 text-emerald-900",
  inconclusive: "border-amber-700 bg-amber-50 text-amber-900",
}
const CHIP_ICON: Record<ProbeKind, typeof CircleX> = { infeasible: CircleX, solution: CircleCheck, inconclusive: CircleHelp }

/** Parametrarnas etiketter och format för ett scenario, för att skriva värden i klartext. */
export function useScenarioParams(scenarioId: string | undefined) {
  const [params, setParams] = useState<Record<string, ParameterInfo>>({})
  useEffect(() => {
    if (!scenarioId) return
    jointApi.parameters(scenarioId).then(answer => setParams(Object.fromEntries(answer.parameters.map(param => [param.id, param])))).catch(() => setParams({}))
  }, [scenarioId])
  const labels = useMemo(() => Object.fromEntries(Object.values(params).map(param => [param.id, param.label])), [params])
  const show = (id: string, value: unknown) => params[id] ? formatParamValue(params[id], value) : formatLooseValue({ id, unit: null }, value)
  return { labels, show }
}

/**
 * Begränsningarna som gällde för körningen: tillåtna dagar och tider, flyttfönster, period, salar och flyttbara typer.
 * Det användaren själv ändrade är markerat med gammalt värde, och en utredning visar vilka som bevisat är omöjliga ensamma.
 */
export function ConstraintList({ state, labels, show }: { state: DiagnosisState; labels: Record<string, string>; show: (id: string, value: unknown) => string }) {
  const rows = constraintRows(state)
  const changeById = new Map<string, DiagnosisChange>(state.changes.map(change => [change.id, change]))
  return <ul className="divide-y rounded-md border" aria-label="Begränsningar i körningen">
    {rows.map(row => {
      const change = changeById.get(row.id)
      const probe = change ? probeFor(state, change.id) : undefined
      const Icon = probe ? CHIP_ICON[probe.kind] : null
      return <li key={row.id} className="flex flex-wrap items-center justify-between gap-2 p-2.5">
        <div>
          <div className="font-medium">{change ? changeLabel(change, labels) : labels[row.id] ?? row.id}</div>
          <div className="text-xs text-slate-800">{change ? <>{show(row.id, change.baseline)} → <strong>{show(row.id, change.run)}</strong></> : show(row.id, row.value)}</div>
        </div>
        <div className="flex items-center gap-2">
          {change && <span className="inline-flex items-center gap-1 text-xs font-medium"><PencilLine size={13} aria-hidden="true"/>Ditt val</span>}
          {probe && Icon && <span title={PROBE_HINT[probe.kind]} className={`flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${CHIP[probe.kind]}`}><Icon size={13} aria-hidden="true"/>{PROBE_TEXT[probe.kind]}</span>}
        </div>
      </li>
    })}
  </ul>
}
