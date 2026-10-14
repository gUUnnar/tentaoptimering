import type { PrecheckResult, PrecheckVerdict } from "./precheckApi.ts"

/** Hur utfallet kan fortsätta: ett hinder stoppar inte Kör men varnar, medan "possible" och "unclear" bara informerar. */
export type PrecheckTone = "blocker" | "info"

export const precheckTone = (verdict: PrecheckVerdict): PrecheckTone => verdict === "impossible" || verdict === "blocked" ? "blocker" : "info"

/** Rubriken för ett utfall, en mening. Skälen står under rubriken. */
export function precheckTitle(result: PrecheckResult): string {
  switch (result.verdict) {
    case "impossible": return "Går inte att köra: det är bevisat att tentorna inte ryms."
    case "blocked": return `Går inte att köra: ${result.blocked_exams} ${result.blocked_exams === 1 ? "tenta har" : "tentor har"} inget tillåtet tillfälle.`
    case "possible": return `Går att köra: en lösning hittades på ${result.seconds} s.`
    default: return "Inget hinder hittades, men det är inget bevis för att det går."
  }
}

/** Jobbfelet som text. */
export function precheckError(error: { message?: string } | string | null): string {
  if (typeof error === "string") return error
  return error?.message || "Förkontrollen misslyckades."
}
