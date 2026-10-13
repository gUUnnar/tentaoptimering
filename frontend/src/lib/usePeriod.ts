import { useEffect, useState } from "react"
import { jointApi } from "./jointApi"
import type { PeriodCheck, PeriodCoverage } from "./jointTypes"
import { periodInputError, type PeriodChoice } from "./period"

export type PeriodState = {
  coverage: PeriodCoverage | null
  /** Servern har kontrollerat det valda datumintervallet; null medan kontrollen pågår eller när inget är valt. */
  check: PeriodCheck | null
  loadError: string
  checking: boolean
}

/**
 * Datatäckning för scenariot och kontroll av vald period. Kontrollen görs av servern så att antalet tentor och
 * varningarna är samma som körningen får; ett fel i valet (till exempel omvända datum) fångas innan anropet.
 */
export function usePeriod(scenarioId: string, choice: PeriodChoice | null, refreshKey?: unknown): PeriodState {
  const [coverage, setCoverage] = useState<PeriodCoverage | null>(null)
  const [loadError, setLoadError] = useState("")
  const [checked, setChecked] = useState<{ key: string; check: PeriodCheck } | null>(null)

  useEffect(() => {
    setCoverage(null); setLoadError(""); setChecked(null)
    if (!scenarioId) return
    let cancelled = false
    jointApi.period(scenarioId)
      .then(data => { if (!cancelled) setCoverage(data) })
      .catch(error => { if (!cancelled) setLoadError((error as Error).message) })
    return () => { cancelled = true }
  }, [scenarioId, refreshKey])

  const valid = choice && !periodInputError(choice) ? choice : null
  const key = valid ? `${scenarioId}|${valid.from}|${valid.to}` : ""
  useEffect(() => {
    if (!valid || !scenarioId) return
    let cancelled = false
    jointApi.period(scenarioId, valid.from, valid.to)
      .then(data => { if (!cancelled && data.check) setChecked({ key, check: data.check }) })
      .catch(error => { if (!cancelled) setLoadError((error as Error).message) })
    return () => { cancelled = true }
  }, [key])  // eslint-disable-line react-hooks/exhaustive-deps

  const check = checked && checked.key === key ? checked.check : null
  return { coverage, check, loadError, checking: !!valid && !check }
}
