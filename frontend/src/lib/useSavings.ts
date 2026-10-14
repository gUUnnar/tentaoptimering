import { useCallback, useEffect, useState } from "react"
import { savingsApi, type SavingsState } from "./savingsApi"
import { jobProgress } from "./underlay"

const POLL_MS = 1000

/** Besparingspotentialen för en körning och det jobb som beräknar referensen med låsta datum (följs även efter omladdning). */
export function useSavings(runId: string) {
  const [state, setState] = useState<SavingsState | null>(null)
  const [error, setError] = useState("")
  const [starting, setStarting] = useState(false)
  const refresh = useCallback(async () => {
    try { setState(await savingsApi.state(runId)); setError("") } catch (failure) { setError((failure as Error).message) }
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
    try { await savingsApi.start(runId); await refresh() } catch (failure) { setError((failure as Error).message) } finally { setStarting(false) }
  }
  return { state, error, running: running || starting, start }
}
