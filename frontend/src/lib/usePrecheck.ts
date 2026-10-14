import { useEffect, useRef, useState } from "react"
import type { StartJointRunBody } from "./jointTypes"
import { precheckApi, type PrecheckResult } from "./precheckApi"
import { precheckError } from "./precheckView"

const POLL_MS = 500

export type PrecheckState = { status: "idle" | "running" | "done" | "error"; result: PrecheckResult | null; error: string }

/**
 * Förkontroll av inställningarna. Utfallet gäller bara de inställningar det gjordes för: ändras något (`key`) försvinner det,
 * så att ett gammalt svar aldrig står kvar bredvid nya värden.
 */
export function usePrecheck(key: string) {
  const [state, setState] = useState<PrecheckState>({ status: "idle", result: null, error: "" })
  const forKey = useRef(key)
  useEffect(() => { forKey.current = key; setState(current => current.status === "running" ? current : { status: "idle", result: null, error: "" }) }, [key])

  const run = async (body: StartJointRunBody) => {
    const startedFor = key
    setState({ status: "running", result: null, error: "" })
    try {
      const { job_id } = await precheckApi.start(body)
      for (;;) {
        await new Promise(resolve => window.setTimeout(resolve, POLL_MS))
        const job = await precheckApi.job(job_id)
        if (job.status === "failed") throw new Error(precheckError(job.error))
        if (job.status === "completed" && job.result) {
          if (forKey.current === startedFor) setState({ status: "done", result: job.result, error: "" })
          else setState({ status: "idle", result: null, error: "" })
          return
        }
      }
    } catch (error) { setState({ status: "error", result: null, error: (error as Error).message }) }
  }
  return { ...state, run }
}
