import { useCallback, useEffect, useRef, useState } from "react"
import { jobIsActive, jobProgress } from "./underlay"
import { underlayApi, type PreparationState, type SourceCheck } from "./underlayApi"

const POLL_MS = 1000
const CHECK_DELAY_MS = 400

export type Notice = { kind: "ok" | "error"; text: string }

/** Tillstånd och åtgärder för sidan Underlag. Serverns svar på /api/preparation är sanningen: det visar även ett jobb som startades före en omladdning. */
export function useUnderlay(active: boolean, onPrepared: () => void) {
  const [sourceDir, setSourceDir] = useState("")
  const [savedDir, setSavedDir] = useState("")
  const [appDataDir, setAppDataDir] = useState("")
  const [loaded, setLoaded] = useState(false)
  const [notice, setNotice] = useState<Notice | null>(null)
  const [state, setState] = useState<PreparationState | null>(null)
  const [stateError, setStateError] = useState("")
  const [check, setCheck] = useState<SourceCheck | null>(null)
  const [starting, setStarting] = useState(false)
  const [choosing, setChoosing] = useState(false)
  const [startError, setStartError] = useState("")
  const seenJob = useRef<string | null>(null)

  const refresh = useCallback(async () => {
    try { const next = await underlayApi.preparation(); setState(next); setStateError(""); return next }
    catch (error) { setStateError((error as Error).message); return null }
  }, [])

  useEffect(() => {
    underlayApi.settings()
      .then(answer => { const dir = answer.settings.source_dir ?? ""; setSourceDir(dir); setSavedDir(dir); setAppDataDir(answer.app_data_dir ?? "") })
      .catch(error => setNotice({ kind: "error", text: `Kunde inte läsa inställningarna: ${(error as Error).message}` }))
      .finally(() => setLoaded(true))
  }, [])
  useEffect(() => { if (active) void refresh() }, [active, refresh])

  const running = jobIsActive(state?.job)
  const jobId = state?.job?.job_id ?? null
  const jobStatus = jobProgress(state?.job?.status)
  useEffect(() => {
    if (!running) return
    const timer = window.setInterval(() => void refresh(), POLL_MS)
    return () => window.clearInterval(timer)
  }, [running, refresh])
  // Berätta för övriga sidor när ett jobb som vi sett pågå har blivit klart, men inte för ett gammalt färdigt jobb vid sidladdning.
  useEffect(() => {
    if (running && jobId) seenJob.current = jobId
    if (!running && jobId && jobStatus === "completed" && seenJob.current === jobId) { seenJob.current = null; onPrepared() }
  }, [running, jobId, jobStatus, onPrepared])

  // Förhandskontroll av den skrivna sökvägen, så att saknade filer syns innan en förberedelse startas.
  useEffect(() => {
    const path = sourceDir.trim()
    if (!path) { setCheck(null); return }
    let stale = false
    const timer = window.setTimeout(() => {
      underlayApi.checkSource(path).then(answer => { if (!stale) setCheck(answer) }).catch(() => { if (!stale) setCheck(null) })
    }, CHECK_DELAY_MS)
    return () => { stale = true; window.clearTimeout(timer) }
  }, [sourceDir])

  const save = async () => {
    try {
      const answer = await underlayApi.saveSourceDir(sourceDir.trim() || null)
      const dir = answer.settings.source_dir ?? ""
      setSourceDir(dir); setSavedDir(dir)
      setNotice({ kind: "ok", text: dir ? "Källdatakatalogen är sparad i användarprofilen." : "Källdatakatalogen är borttagen." })
      void refresh()
    } catch (error) { setNotice({ kind: "error", text: (error as Error).message }) }
  }

  const browse = async () => {
    setChoosing(true)
    try {
      const answer = await underlayApi.chooseDirectory()
      if (answer.source_dir) { setSourceDir(answer.source_dir); setCheck(answer.source); setNotice({ kind: "ok", text: "Mappen är vald. Spara sökvägen för att använda den." }) }
    } catch (error) { setNotice({ kind: "error", text: (error as Error).message }) }
    finally { setChoosing(false) }
  }

  const prepare = async () => {
    setStartError(""); setStarting(true)
    try { await underlayApi.startPreparation(); await refresh() }
    catch (error) { setStartError((error as Error).message) }
    finally { setStarting(false) }
  }

  const busy = starting || running
  const dirSaved = !!savedDir && sourceDir.trim() === savedDir
  return { sourceDir, setSourceDir, savedDir, appDataDir, loaded, notice, state, stateError, check, busy, running, starting, choosing, startError, dirSaved, save, browse, prepare }
}
