import { useCallback, useEffect, useState } from "react"
import { diagnosisApi, type DiagnosisState } from "./diagnosisApi"
import { jobProgress } from "./underlay"

const POLL_MS = 1000

/** Utredningen av en körning: ändringarna, ett eventuellt sparat resultat och ett pågående jobb (som överlever omladdning). */
export function useDiagnosis(runId: string) {
  const [state, setState] = useState<DiagnosisState | null>(null)
  const [error, setError] = useState("")
  const [starting, setStarting] = useState(false)

  const refresh = useCallback(async () => {
    try { setState(await diagnosisApi.state(runId)); setError("") } catch (failure) { setError((failure as Error).message) }
  }, [runId])
  useEffect(() => { setState(null); void refresh() }, [refresh])

  const running = !!state?.job && jobProgress(state.job.status) === "running"
  useEffect(() => {
    if (!running) return
    const timer = window.setInterval(() => void refresh(), POLL_MS)
    return () => window.clearInterval(timer)
  }, [running, refresh])

  const start = async () => {
    setStarting(true); setError("")
    try { await diagnosisApi.start(runId); await refresh() } catch (failure) { setError((failure as Error).message) } finally { setStarting(false) }
  }
  return { state, error, running: running || starting, start }
}
