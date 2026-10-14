import { useEffect, useState } from "react"
import type { UnderlayFact } from "./scenarioFacts"
import { underlayApi } from "./underlayApi"

/** När det förberedda underlaget skapades och om det är aktuellt; null medan det hämtas, saknas eller inte går att läsa. */
export function useUnderlayInfo(refreshKey: unknown): UnderlayFact {
  const [info, setInfo] = useState<UnderlayFact>(null)
  useEffect(() => {
    let cancelled = false
    underlayApi.preparation()
      .then(state => { if (!cancelled) setInfo(state.underlay.manifest ? { preparedAt: state.underlay.manifest.prepared_at, state: state.underlay.state } : null) })
      .catch(() => { if (!cancelled) setInfo(null) })
    return () => { cancelled = true }
  }, [refreshKey])
  return info
}
