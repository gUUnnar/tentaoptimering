import { request } from "./jointApi"

export type SavingsFacts = { cost_ore: number; bound_ore: number | null; staff_pool_size: number | null; changed_exams: number | null; exams_total: number | null }
export type SavingsComponent = { key: string; label: string; baseline_ore: number | null; run_ore: number | null }
export type SavingsJob = { job_id: string; status: string; error: string | null }
export type SavingsReady = {
  state: "ready"; baseline: SavingsFacts; run: SavingsFacts; potential_ore: number; potential_low_ore: number; potential_high_ore: number
  components: SavingsComponent[]; job: SavingsJob | null
}
export type SavingsState =
  | { state: "unavailable"; reason: string; job: SavingsJob | null }
  | { state: "missing"; job: SavingsJob | null }
  | SavingsReady

const enc = encodeURIComponent

/** Besparingspotential mot en referensoptimering med låsta datum (samma scenario där ingen tentamen flyttas; inte den faktiska bokningen). */
export const savingsApi = {
  state: (runId: string) => request<SavingsState>(`/api/joint-runs/${enc(runId)}/savings`),
  start: (runId: string) => request<{ job_id: string }>(`/api/joint-runs/${enc(runId)}/savings`, { method: "POST" }),
}
