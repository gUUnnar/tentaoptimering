// Minne för pågående körning i webbläsarfliken, så att navigering bort och tillbaka inte tappar körningen.

export type RunChangeText = { id: string; label: string; oldText: string; newText: string }
export type RememberedJob = { jobId: string; scenarioId: string | null; changes: RunChangeText[] }

const KEY = "tentaoptimering.joint.job.v2"

export function remember(job: RememberedJob | null): void {
  try { if (job) window.sessionStorage.setItem(KEY, JSON.stringify(job)); else window.sessionStorage.removeItem(KEY) } catch { /* lagring kan saknas */ }
}

export function loadRemembered(): RememberedJob | null {
  try {
    const raw = window.sessionStorage.getItem(KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<RememberedJob>
    if (typeof parsed.jobId !== "string") return null
    return { jobId: parsed.jobId, scenarioId: typeof parsed.scenarioId === "string" ? parsed.scenarioId : null, changes: Array.isArray(parsed.changes) ? parsed.changes : [] }
  } catch { return null }
}
