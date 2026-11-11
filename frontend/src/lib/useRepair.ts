import { useEffect, useRef, useState } from "react"
import { repairApi, type RepairBody, type RepairResult } from "./repairApi"

const POLL_MS = 1000

export type RepairState = { status: "idle" | "running" | "done" | "error"; result: RepairResult | null; error: string; current: string | null }

const IDLE: RepairState = { status: "idle", result: null, error: "", current: null }

const errorText = (error: unknown): string =>
  typeof error === "string" ? error : error && typeof error === "object" && "message" in error ? String((error as { message?: string }).message ?? "") : ""

/**
 * Sök efter den minsta ändring som gör en körning möjlig. Ett svar gäller bara de inställningar det söktes för: ändras `key` försvinner det,
 * så att ett gammalt förslag aldrig står kvar bredvid nya värden.
 */
export function useRepair(key: string) {
  const [state, setState] = useState<RepairState>(IDLE)
  const forKey = useRef(key)
  useEffect(() => { forKey.current = key; setState(current => current.status === "running" ? current : IDLE) }, [key])

  const run = async (body: RepairBody) => {
    const startedFor = key
    setState({ ...IDLE, status: "running" })
    try {
      const { job_id } = await repairApi.start(body)
      for (;;) {
        await new Promise(resolve => window.setTimeout(resolve, POLL_MS))
        const job = await repairApi.job(job_id)
        if (job.status === "failed") throw new Error(errorText(job.error) || "Sökningen misslyckades.")
        if (job.status === "completed" && job.result) {
          setState(forKey.current === startedFor ? { status: "done", result: job.result, error: "", current: null } : IDLE)
          return
        }
        const progress = await repairApi.progress(job_id).catch(() => null)
        if (progress) setState(current => current.status === "running" ? { ...current, current: progress.progress.current } : current)
      }
    } catch (error) { setState({ status: "error", result: null, error: (error as Error).message, current: null }) }
  }
  return { ...state, run }
}
