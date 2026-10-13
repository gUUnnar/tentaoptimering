import type { JointScenario } from "./jointTypes.ts"

/** Om det förberedda underlaget finns. "unknown" när det inte går att avgöra ur scenariolistan. */
export type UnderlayStatus = "unknown" | "present" | "missing"

/** Regelbaserade urval (till exempel alla tentor i underlaget under en period) får antalet tentor ur det förberedda underlaget; saknas antalet saknas underlaget. */
export function scenarioNeedsUnderlay(scenario: JointScenario | undefined): boolean {
  return scenario?.subset?.selection === "rule" && (scenario.subset.exam_count === null || scenario.subset.exam_count === undefined)
}

export function underlayStatus(scenarios: JointScenario[]): UnderlayStatus {
  const ruleBased = scenarios.filter(item => item.subset?.selection === "rule")
  if (!ruleBased.length) return "unknown"
  return ruleBased.some(item => !scenarioNeedsUnderlay(item)) ? "present" : "missing"
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
