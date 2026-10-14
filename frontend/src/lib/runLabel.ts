import type { JointScenario, SavedRun } from "./jointTypes.ts"

const RUN_STAMP = /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z/
const MONTHS = ["jan", "feb", "mars", "apr", "maj", "juni", "juli", "aug", "sep", "okt", "nov", "dec"]
const pad = (value: number) => String(value).padStart(2, "0")

/** Starttiden som lokal tid: ur created_at, annars ur tidsstämpeln i körnings-id:t (UTC). Null om ingen av dem går att läsa. */
export function runStart(runId: string, createdAt?: string | null): Date | null {
  const fromCreated = createdAt ? new Date(createdAt) : null
  if (fromCreated && !Number.isNaN(fromCreated.getTime())) return fromCreated
  const match = RUN_STAMP.exec(runId)
  if (!match) return null
  const [, y, mo, d, h, mi, s] = match
  return new Date(Date.UTC(Number(y), Number(mo) - 1, Number(d), Number(h), Number(mi), Number(s)))
}

/** "14:12" för en körning i dag, annars "13 okt 14:12". */
export function startText(start: Date, now: Date = new Date()): string {
  const clock = `${pad(start.getHours())}:${pad(start.getMinutes())}`
  const sameDay = start.getFullYear() === now.getFullYear() && start.getMonth() === now.getMonth() && start.getDate() === now.getDate()
  return sameDay ? clock : `${start.getDate()} ${MONTHS[start.getMonth()]} ${clock}`
}

/** Scenariots namn för ett körnings-scenario-id (som är problem-id:t); id:t självt om scenariot inte längre finns. */
export function scenarioName(scenarios: JointScenario[], problemId: string): string {
  return scenarios.find(item => item.problem_id === problemId || item.id === problemId)?.name ?? problemId
}

/** Hur en körning benämns för användaren: scenario och klockslag. Det tekniska id:t visas bara bakom en ikon. */
export function runLabel(run: Pick<SavedRun, "run_id" | "scenario_id" | "created_at"> & { name?: string }, scenarios: JointScenario[], now: Date = new Date()): string {
  if (run.name) return run.name
  const start = runStart(run.run_id, run.created_at)
  const name = scenarioName(scenarios, run.scenario_id)
  return start ? `${name}, ${startText(start, now)}` : name
}
