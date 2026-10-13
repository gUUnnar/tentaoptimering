import { request } from "./jointApi"

export type SettingsResponse = { settings: { source_dir: string | null }; app_data_dir?: string }

export type SourceFileCheck = { role: string; label: string; filename: string; found: boolean; bytes?: number; modified?: string }
export type SourceCheck = { source_dir: string | null; exists: boolean; ready: boolean; files: SourceFileCheck[] }

export type UnderlayManifest = {
  prepared_id: string; prepared_at: string; source_dir: string
  sources: Record<string, { label: string; filename: string; bytes: number; modified: string; sha256: string | null }>
  counts: Record<string, number | null>
  period: { first: string | null; last: string | null; dated_rows: number }
  quality: { findings: number; critical_findings: number; demand_coverage_percent: number | null; unresolved_activities: number | null; scope_complete: boolean | null }
}
export type UnderlayState = "current" | "stale" | "incomplete" | "unverified" | "missing"
export type UnderlayInfo = { state: UnderlayState; manifest: UnderlayManifest | null; reasons: string[] }

export type PreparationJob = {
  job_id: string; status: string; error: string | null
  progress: { step: string | null; label: string; index: number; total: number }
  steps: { key: string; label: string }[]
}
export type PreparationState = { underlay: UnderlayInfo; source: SourceCheck; job: PreparationJob | null }

const enc = encodeURIComponent

/** Anrop för sidan Underlag: källdatakatalog, förhandskontroll, förberedelsejobb och det förberedda underlagets tillstånd. */
export const underlayApi = {
  settings: () => request<SettingsResponse>("/api/settings"),
  saveSourceDir: (sourceDir: string | null) => request<{ settings: { source_dir: string | null } }>("/api/settings", { method: "PUT", body: JSON.stringify({ source_dir: sourceDir }) }),
  preparation: () => request<PreparationState>("/api/preparation"),
  startPreparation: () => request<{ job_id: string }>("/api/preparation", { method: "POST" }),
  checkSource: (path: string) => request<SourceCheck>(`/api/source-check?path=${enc(path)}`),
  chooseDirectory: () => request<{ source_dir: string | null; source: SourceCheck | null }>("/api/settings/choose-source-directory", { method: "POST" }),
}
