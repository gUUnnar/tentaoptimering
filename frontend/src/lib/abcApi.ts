import { request } from "./jointApi.ts"
import type { AbcCompare, AbcProfile, AbcRun, AbcWishes } from "./abcTypes.ts"

const enc = encodeURIComponent

/** Referensen för den faktiska bokningen i anropen. */
export const ACTUAL_REF = "actual"

export const abcApi = {
  runs: async (): Promise<AbcRun[]> => (await request<{ runs: AbcRun[] }>("/api/abc/runs")).runs,
  wishes: () => request<AbcWishes>("/api/abc/wishes"),
  /** A (`actual`) eller en körning. Utan tentor: bara sammanfattningen. `scopeRun` begränsar A till en körnings tentor. */
  profile: (ref: string, scopeRun?: string | null) =>
    request<AbcProfile>(`/api/abc/profile?ref=${enc(ref)}&include_exams=false${scopeRun ? `&scope_run=${enc(scopeRun)}` : ""}`),
  compare: (left: string, right: string) => request<AbcCompare>(`/api/abc/compare?left=${enc(left)}&right=${enc(right)}`),
}
