import { useEffect, useRef, useState } from "react"
import { jointApi } from "./jointApi"
import type { JointOptions } from "./jointTypes"
import { availableOptions, type OptionsLoad } from "./paramOptions"

export type OptionsSource = { load: OptionsLoad; available: JointOptions | null; reload(): void }

/**
 * Salar och tentamenstyper i underlaget för ett scenario. Hämtas när scenariot väljs och igen när `refreshKey` ändras (till exempel när
 * underlaget har förberetts); under en förnyad hämtning behålls det som redan finns så att pågående val inte försvinner.
 */
export function useJointOptions(scenarioId: string, refreshKey?: unknown): OptionsSource {
  const [load, setLoad] = useState<OptionsLoad>({ status: "idle", error: "", data: null })
  const [attempt, setAttempt] = useState(0)
  const lastScenario = useRef("")

  useEffect(() => {
    const sameScenario = lastScenario.current === scenarioId
    lastScenario.current = scenarioId
    if (!scenarioId) { setLoad({ status: "idle", error: "", data: null }); return }
    let cancelled = false
    setLoad(current => ({ status: "loading", error: "", data: sameScenario ? current.data : null }))
    jointApi.options(scenarioId)
      .then(data => { if (!cancelled) setLoad({ status: "ready", error: "", data }) })
      .catch(error => { if (!cancelled) setLoad({ status: "error", error: (error as Error).message, data: null }) })
    return () => { cancelled = true }
  }, [scenarioId, attempt, refreshKey])

  return { load, available: availableOptions(load), reload: () => setAttempt(value => value + 1) }
}
