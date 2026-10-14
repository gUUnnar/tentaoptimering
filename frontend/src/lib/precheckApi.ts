import { request } from "./jointApi"
import type { StartJointRunBody } from "./jointTypes"

export type PrecheckVerdict = "impossible" | "blocked" | "possible" | "unclear"
export type PrecheckResult = {
  verdict: PrecheckVerdict; exams_total: number; blocked_exams: number; must_move_exams: number
  solver_outcome: string; seconds: number; reasons: string[]
}
export type PrecheckJob = { job_id: string; status: string; result: PrecheckResult | null; error: { message?: string } | string | null }

const enc = encodeURIComponent

/** Förkontroll av en körning: går tentorna överhuvudtaget att placera med de här inställningarna? Samma underlag som en körning, inget sparas. */
export const precheckApi = {
  start: (body: StartJointRunBody) => request<{ job_id: string }>("/api/joint-runs/precheck", { method: "POST", body: JSON.stringify(body) }),
  job: (jobId: string) => request<PrecheckJob>(`/api/jobs/${enc(jobId)}`),
}
