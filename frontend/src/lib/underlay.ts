import type { JointScenario } from "./jointTypes.ts"
import type { PreparationJob, UnderlayState } from "./underlayApi.ts"

/** Regelbaserade urval (till exempel alla tentor i underlaget under en period) får antalet tentor ur det förberedda underlaget; saknas antalet saknas underlaget. */
export function scenarioNeedsUnderlay(scenario: JointScenario | undefined): boolean {
  return scenario?.subset?.selection === "rule" && (scenario.subset.exam_count === null || scenario.subset.exam_count === undefined)
}

const MISSING_UNDERLAY = /optimization_(demands|rooms)\.csv|demand_scope\.csv|No such file or directory|Errno 2|FileNotFoundError|förberett underlag|underlaget/i

/** Känner igen serverfel som beror på att underlaget inte är förberett, så att sidan kan ge ett begripligt besked. */
export function isMissingUnderlayMessage(message: string | null | undefined): boolean {
  return !!message && MISSING_UNDERLAY.test(message)
}

export type JobProgress = "idle" | "starting" | "running" | "completed" | "failed"

/** Översätter jobbstatus från servern. Okända värden räknas som pågående tills jobbet är klart eller har misslyckats. */
export function jobProgress(status: string | undefined): JobProgress {
  if (status === "completed") return "completed"
  if (status === "failed") return "failed"
  return "running"
}

/** Förberedelsen pågår enligt servern: ett jobb som varken är klart eller har misslyckats. */
export function jobIsActive(job: PreparationJob | null | undefined): boolean {
  return !!job && jobProgress(job.status) === "running"
}

export const STATE_TEXT: Record<UnderlayState, string> = {
  current: "Underlaget är förberett och stämmer med källfilerna. Optimeringen kan köras.",
  stale: "Underlaget är förberett men är inte längre aktuellt. Förbered det på nytt innan du optimerar.",
  incomplete: "Underlaget är ofullständigt. Förbered det på nytt.",
  unverified: "Underlaget saknar manifest och kan inte spåras till sina källfiler. Förbered det på nytt.",
  missing: "Underlaget är inte förberett än. Optimering av tentor ur underlaget kan inte köras förrän förberedelsen är klar.",
}

/** Underlaget går att räkna på (även om det är föråldrat), så att sidan kan varna i stället för att stänga. */
export const stateIsUsable = (state: UnderlayState): boolean => state === "current" || state === "stale"

export function formatBytes(bytes: number | undefined): string {
  if (bytes === undefined) return ""
  if (bytes < 1024) return `${bytes} B`
  return bytes < 1024 * 1024 ? `${Math.round(bytes / 1024)} kB` : `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} MB`
}

/** ISO-tidpunkt som "2026-10-13 14:35"; ogiltiga värden visas som de är. */
export function formatWhen(iso: string | undefined): string {
  const date = iso ? new Date(iso) : null
  if (!date || Number.isNaN(date.getTime())) return iso ?? ""
  const pad = (value: number) => String(value).padStart(2, "0")
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}
