import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import type { JointApi } from "./jointApi"
import { emptyJointState, foldEvents, mergeEvents, type JointState } from "./jointState"
import type { JointEvent, JointJobStatus, StartJointRunBody } from "./jointTypes"

const POLL_MS = 1000
const STORAGE_KEY = "tentaoptimering.joint.job"
const EXTRAPOLATION_CAP_S = 5

export type JointJob = {
  jobId: string | null
  status: JointJobStatus | "idle" | "starting"
  events: JointEvent[]
  runId: string | null
  error: string | null
  connectionLost: boolean
  cancelRequested: boolean
}

const idle: JointJob = { jobId: null, status: "idle", events: [], runId: null, error: null, connectionLost: false, cancelRequested: false }

const keyFor = (mock: boolean) => `${STORAGE_KEY}.${mock ? "mock" : "live"}`
const remember = (mock: boolean, jobId: string | null) => {
  try { if (jobId) window.sessionStorage.setItem(keyFor(mock), jobId); else window.sessionStorage.removeItem(keyFor(mock)) } catch { /* lagring kan saknas */ }
}
const recall = (mock: boolean): string | null => { try { return window.sessionStorage.getItem(keyFor(mock)) } catch { return null } }

/** Startar, pollar (var sekund) och stoppar en gemensam körning. Pågående jobb återupptas efter navigering i samma flik. */
export function useJointJob(api: JointApi | null) {
  const [job, setJob] = useState<JointJob>(idle)
  const afterRef = useRef(0)
  const receivedAt = useRef(Date.now())
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (!api) return
    const saved = recall(api.mock)
    if (saved) { afterRef.current = 0; setJob({ ...idle, jobId: saved, status: "running" }) }
  }, [api])

  useEffect(() => {
    if (!api || !job.jobId || job.status !== "running") return
    let stopped = false
    let timer: number | undefined
    let failures = 0
    const jobId = job.jobId
    const poll = async () => {
      try {
        const answer = await api.events(jobId, afterRef.current)
        if (stopped) return
        failures = 0
        afterRef.current = Math.max(afterRef.current, answer.last_seq)
        receivedAt.current = Date.now()
        setJob(current => ({ ...current, events: mergeEvents(current.events, answer.events), status: answer.status, runId: answer.run_id ?? current.runId, connectionLost: false }))
        if (answer.status !== "running") { remember(api!.mock, null); return }
      } catch (error) {
        if (stopped) return
        failures += 1
        const gone = (error as { status?: number }).status === 404
        if (gone) { remember(api!.mock, null); setJob(current => ({ ...current, status: "failed", error: "Jobbet finns inte kvar på servern.", connectionLost: false })); return }
        if (failures >= 3) setJob(current => ({ ...current, connectionLost: true, error: (error as Error).message }))
      }
      timer = window.setTimeout(poll, POLL_MS)
    }
    timer = window.setTimeout(poll, 0)
    return () => { stopped = true; if (timer !== undefined) window.clearTimeout(timer) }
  }, [api, job.jobId, job.status === "running"])

  const running = job.status === "running"
  useEffect(() => {
    if (!running) return
    const id = window.setInterval(() => setTick(value => value + 1), 500)
    return () => window.clearInterval(id)
  }, [running])

  const start = useCallback(async (body: StartJointRunBody) => {
    if (!api) return
    afterRef.current = 0
    setJob({ ...idle, status: "starting" })
    try {
      const { job_id } = await api.startRun(body)
      remember(api.mock, job_id)
      receivedAt.current = Date.now()
      setJob({ ...idle, jobId: job_id, status: "running" })
    } catch (error) { setJob({ ...idle, status: "failed", error: (error as Error).message }) }
  }, [api])

  const cancel = useCallback(async () => {
    if (!api || !job.jobId) return
    setJob(current => ({ ...current, cancelRequested: true }))
    try { await api.cancel(job.jobId) } catch (error) { setJob(current => ({ ...current, cancelRequested: false, error: (error as Error).message })) }
  }, [api, job.jobId])

  const reset = useCallback(() => { if (api) remember(api.mock, null); afterRef.current = 0; setJob(idle) }, [api])

  const state: JointState = useMemo(() => foldEvents(job.events), [job.events])
  // Aktuell körtid: senast kända händelsetid plus tiden sedan senaste svar (högst några sekunder), så att fasernas klocka går mellan pollningarna.
  const nowT = useMemo(() => {
    if (!running) return state.lastT
    return state.lastT + Math.min(EXTRAPOLATION_CAP_S, (Date.now() - receivedAt.current) / 1000)
  }, [state.lastT, running, tick])

  return { job, state, nowT, start, cancel, reset }
}
