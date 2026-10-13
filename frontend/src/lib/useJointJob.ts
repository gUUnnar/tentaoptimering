import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { jointApi } from "./jointApi"
import { emptyJointState, foldEvents, mergeEvents, type JointState } from "./jointState"
import type { JointEvent, JointJobStatus, StartJointRunBody } from "./jointTypes"
import { loadRemembered, remember, type RunChangeText } from "./jointJobMemory"
import { RunClock } from "./runClock"

const POLL_MS = 1000

export type JointJob = {
  jobId: string | null
  status: JointJobStatus | "idle" | "starting"
  events: JointEvent[]
  runId: string | null
  error: string | null
  connectionLost: boolean
  cancelRequested: boolean
  /** Parametrar som den här körningen ändrade jämfört med scenariot, i klartext. */
  changes: RunChangeText[]
  scenarioId: string | null
  /** Körningens tid enligt servern vid avslut. Null medan körningen pågår. */
  finalSeconds: number | null
}

const idle: JointJob = { jobId: null, status: "idle", events: [], runId: null, error: null, connectionLost: false, cancelRequested: false, changes: [], scenarioId: null, finalSeconds: null }

/** Startar, pollar (var sekund) och stoppar en optimeringskörning. Pågående körning återupptas efter navigering i samma flik. */
export function useJointJob() {
  const api = jointApi
  const [job, setJob] = useState<JointJob>(idle)
  const afterRef = useRef(0)
  const clock = useRef(new RunClock())
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const saved = loadRemembered()
    if (saved) { afterRef.current = 0; clock.current.reset(Date.now()); setJob({ ...idle, jobId: saved.jobId, status: "running", changes: saved.changes, scenarioId: saved.scenarioId }) }
  }, [])

  useEffect(() => {
    if (!job.jobId || job.status !== "running") return
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
        // Serverns tid är sanningen. Äldre servrar saknar den; då används senaste händelsens tid.
        const elapsed = answer.elapsed_seconds ?? answer.events.reduce((latest, event) => Math.max(latest, event.t), 0)
        if (answer.status === "running") clock.current.observe(elapsed, Date.now())
        else clock.current.finish(answer.elapsed_seconds)
        setJob(current => ({
          ...current, events: mergeEvents(current.events, answer.events), status: answer.status, runId: answer.run_id ?? current.runId,
          error: answer.status === "failed" ? answer.error ?? current.error : current.error, connectionLost: false,
          finalSeconds: answer.status === "running" ? null : answer.elapsed_seconds,
        }))
        if (answer.status !== "running") { remember(null); return }
      } catch (error) {
        if (stopped) return
        failures += 1
        const gone = (error as { status?: number }).status === 404
        if (gone) { remember(null); setJob(current => ({ ...current, status: "failed", error: "Körningen finns inte kvar på servern.", connectionLost: false })); return }
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

  /** Kastar fel vidare (t.ex. 422 med fel per parameter) så att startvyn kan visa dem vid rätt rad. */
  const start = useCallback(async (body: StartJointRunBody, changes: RunChangeText[] = []) => {
    afterRef.current = 0
    clock.current.reset(Date.now())
    setJob({ ...idle, status: "starting", changes, scenarioId: body.scenario })
    try {
      const { job_id } = await api.startRun(body)
      remember({ jobId: job_id, changes, scenarioId: body.scenario })
      clock.current.reset(Date.now())
      setJob({ ...idle, jobId: job_id, status: "running", changes, scenarioId: body.scenario })
    } catch (error) {
      setJob(idle)
      throw error
    }
  }, [api])

  const cancel = useCallback(async () => {
    if (!job.jobId) return
    setJob(current => ({ ...current, cancelRequested: true }))
    try { await api.cancel(job.jobId) } catch (error) { setJob(current => ({ ...current, cancelRequested: false, error: (error as Error).message })) }
  }, [api, job.jobId])

  const state: JointState = useMemo(() => foldEvents(job.events), [job.events])
  // Körtiden som visas: serverns senaste tid plus lokal klocka mellan svaren, aldrig bakåt. Efter avslut visas serverns slutvärde.
  const nowT = useMemo(() => {
    if (!running) return job.finalSeconds ?? state.lastT
    return clock.current.read(Date.now())
  }, [state.lastT, running, job.finalSeconds, tick])

  return { job, state, nowT, start, cancel }
}
