import { request } from "./jointApi"

export type DiagnosisChange = { id: string; section: "parameters" | "subset"; key: string; baseline: unknown; run: unknown }
export type ProbeKind = "solution" | "infeasible" | "inconclusive"
export type DiagnosisProbe = { id: string; outcome: string; kind: ProbeKind; seconds: number }
export type SavedDiagnosis = {
  run_id: string; scenario_id: string; probe_seconds: number; complete: boolean
  probes: DiagnosisProbe[]; culprits: string[]; baseline_infeasible: boolean
}
export type DiagnosisJob = { job_id: string; status: string; error: string | null; progress: { done: number; total: number; current: string | null } }
export type DiagnosisState = { scenario_id: string; scenario_name: string; changes: DiagnosisChange[]; saved: SavedDiagnosis | null; job: DiagnosisJob | null }

const enc = encodeURIComponent

/** Utredning av en körning utan lösning: vad den ändrade jämfört med sitt scenario och vilken ändring som gör den omöjlig. */
export const diagnosisApi = {
  state: (runId: string) => request<DiagnosisState>(`/api/joint-runs/${enc(runId)}/diagnosis`),
  start: (runId: string) => request<{ job_id: string }>(`/api/joint-runs/${enc(runId)}/diagnosis`, { method: "POST" }),
}
