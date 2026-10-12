import type { StartJointRunBody } from "./jointTypes.ts"

// Val som inte är verksamhetsparametrar: start från förra körningen och datorresurser.

export type WarmMode = "auto" | "none" | "specific"

export type RunOptions = { mode: WarmMode; specific: string; threads: string; memory: string; parallel: boolean }

export const DEFAULT_RUN_OPTIONS: RunOptions = { mode: "auto", specific: "", threads: "0", memory: "", parallel: true }

export type RunOptionsCheck = { threads: string | null; memory: string | null; warm: string | null }

/** Fel per fält, eller null när fältet är giltigt. */
export function checkRunOptions(options: RunOptions): RunOptionsCheck {
  const threads = Number(options.threads)
  const memory = Number(options.memory)
  return {
    threads: options.threads.trim() !== "" && Number.isInteger(threads) && threads >= 0 ? null : "Ange ett heltal som är 0 eller större.",
    memory: options.memory.trim() === "" || (Number.isInteger(memory) && memory > 0) ? null : "Ange ett positivt heltal eller lämna fältet tomt.",
    warm: options.mode !== "specific" || options.specific !== "" ? null : "Välj en körning ur listan eller ett annat sätt att starta.",
  }
}

export const runOptionsValid = (options: RunOptions): boolean => Object.values(checkRunOptions(options)).every(item => item === null)

export function toStartBody(scenario: string, options: RunOptions, parameters: Record<string, unknown>): StartJointRunBody {
  const body: StartJointRunBody = {
    scenario,
    warm_start: options.mode === "specific" ? options.specific : options.mode,
    threads: Number(options.threads),
    memory_mb: options.memory.trim() === "" ? null : Number(options.memory),
    parallel_day_checks: options.parallel,
  }
  if (Object.keys(parameters).length) body.parameters = parameters
  return body
}
