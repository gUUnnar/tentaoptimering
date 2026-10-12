import { useCallback, useEffect, useState } from "react"
import { jointApi } from "./jointApi"
import { jobProgress, underlayStatus, type JobProgress, type UnderlayStatus } from "./underlay"
import { jobErrorText, underlayApi } from "./underlayApi"

const POLL_MS = 1000

export type Notice = { kind: "ok" | "error"; text: string }

/** Tillstånd och åtgärder för sidan Underlag: källdatakatalog, förberedelsejobb och om underlaget finns. */
export function useUnderlay(active: boolean, onPrepared: () => void) {
  const [sourceDir, setSourceDir] = useState("")
  const [savedDir, setSavedDir] = useState("")
  const [appDataDir, setAppDataDir] = useState("")
  const [loaded, setLoaded] = useState(false)
  const [notice, setNotice] = useState<Notice | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [progress, setProgress] = useState<JobProgress>("idle")
  const [prepareError, setPrepareError] = useState("")
  const [status, setStatus] = useState<UnderlayStatus | "error">("unknown")

  const refreshStatus = useCallback(async () => {
    try { setStatus(underlayStatus(await jointApi.listScenarios())) } catch { setStatus("error") }
  }, [])

  useEffect(() => {
    underlayApi.settings()
      .then(answer => { setSourceDir(answer.settings.source_dir ?? ""); setSavedDir(answer.settings.source_dir ?? ""); setAppDataDir(answer.app_data_dir ?? "") })
      .catch(error => setNotice({ kind: "error", text: `Kunde inte läsa inställningarna: ${(error as Error).message}` }))
      .finally(() => setLoaded(true))
  }, [])
  useEffect(() => { if (active) void refreshStatus() }, [active, refreshStatus])

  useEffect(() => {
    if (!jobId || progress !== "running") return
    let stopped = false
    let timer: number | undefined
    let failures = 0
    const poll = async () => {
      try {
        const answer = await underlayApi.job(jobId)
        if (stopped) return
        failures = 0
        const next = jobProgress(answer.status)
        if (next === "completed") { setProgress("completed"); void refreshStatus(); onPrepared(); return }
        if (next === "failed") { setPrepareError(jobErrorText(answer.error)); setProgress("failed"); return }
      } catch (error) {
        if (stopped) return
        failures += 1
        if ((error as { status?: number }).status === 404) { setPrepareError("Förberedelsen finns inte kvar på servern."); setProgress("failed"); return }
        if (failures >= 3) setPrepareError(`Kontakten med servern är bruten: ${(error as Error).message}`)
      }
      timer = window.setTimeout(poll, POLL_MS)
    }
    timer = window.setTimeout(poll, 0)
    return () => { stopped = true; if (timer !== undefined) window.clearTimeout(timer) }
  }, [jobId, progress, refreshStatus, onPrepared])

  const save = async () => {
    try {
      const answer = await underlayApi.saveSourceDir(sourceDir.trim() || null)
      const dir = answer.settings.source_dir ?? ""
      setSourceDir(dir); setSavedDir(dir)
      setNotice({ kind: "ok", text: dir ? "Källdatakatalogen är sparad i användarprofilen." : "Källdatakatalogen är borttagen." })
    } catch (error) { setNotice({ kind: "error", text: (error as Error).message }) }
  }

  const prepare = async () => {
    setPrepareError(""); setProgress("starting")
    try { const job = await underlayApi.startPreparation(); setJobId(job.job_id); setProgress("running") }
    catch (error) { setPrepareError((error as Error).message); setProgress("failed") }
  }

  const busy = progress === "starting" || progress === "running"
  const dirSaved = !!savedDir && sourceDir.trim() === savedDir
  return { sourceDir, setSourceDir, savedDir, appDataDir, loaded, notice, progress, prepareError, status, busy, dirSaved, save, prepare }
}
