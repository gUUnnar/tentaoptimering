import { request } from "./jointApi"
import type { StartJointRunBody } from "./jointTypes"

export type RepairStatus = "found" | "nothing_needed" | "not_found" | "incomplete" | "unproven"
export type RepairStep = { id: string; label: string; side_effect: string | null }
export type RepairResult = {
  kind: "joint_repair"; status: RepairStatus; summary: string
  /** Parametervärden som förslaget sätter (bara kalender, datum och fasta bokningar). */
  parameters: Record<string, unknown>
  steps: RepairStep[]
  /** Fasta bokningar har tagits bort: resultatet blir explorativt. */
  explorative: boolean
  /** Satt bara när solvern hittade en lösning med förslaget. */
  verified: { outcome: string; seconds: number | null } | null
  exams_without_occasion: { before: number; after: number }
  searched: string[]
  note: string
  attempts: { label: string; exams_without_occasion: number; outcome: string | null; seconds: number | null }[]
  seconds: number
}
export type RepairProgress = { job_id: string; progress: { done: number; current: string | null } }
export type RepairJob = { job_id: string; status: string; result: RepairResult | null; error: { message?: string } | string | null }
export type RepairBody = Pick<StartJointRunBody, "scenario"> & Partial<StartJointRunBody>

const enc = encodeURIComponent

/** Förslag på minsta ändring som gör en körning möjlig. Samma kropp som en körning; inget sparas. */
export const repairApi = {
  start: (body: RepairBody) => request<{ job_id: string }>("/api/joint-runs/suggest-fix", { method: "POST", body: JSON.stringify(body) }),
  job: (jobId: string) => request<RepairJob>(`/api/jobs/${enc(jobId)}`),
  progress: (jobId: string) => request<RepairProgress>(`/api/joint-runs/suggest-fix/${enc(jobId)}/progress`),
}
