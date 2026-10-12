import { request } from "./jointApi"

export type SettingsResponse = { settings: { source_dir: string | null }; app_data_dir?: string }
export type JobStatus = { job_id?: string; status: string; error?: { message?: string } | string | null }

const enc = encodeURIComponent

/** Anrop för sidan Underlag: källdatakatalog, förberedelsejobb och jobbstatus. */
export const underlayApi = {
  settings: () => request<SettingsResponse>("/api/settings"),
  saveSourceDir: (sourceDir: string | null) => request<{ settings: { source_dir: string | null } }>("/api/settings", { method: "PUT", body: JSON.stringify({ source_dir: sourceDir }) }),
  startPreparation: () => request<{ job_id: string }>("/api/preparation", { method: "POST" }),
  job: (jobId: string) => request<JobStatus>(`/api/jobs/${enc(jobId)}`),
}

export function jobErrorText(error: JobStatus["error"]): string {
  if (typeof error === "string") return error
  return error?.message || "Förberedelsen misslyckades."
}
