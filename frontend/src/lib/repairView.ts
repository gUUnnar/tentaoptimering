import type { RepairResult, RepairStatus } from "./repairApi"

const TITLES: Record<RepairStatus, string> = {
  nothing_needed: "Inget behöver ändras: inställningarna går redan att lösa.",
  found: "Det här är den minsta ändringen som gör körningen möjlig",
  unproven: "Ett troligt förslag, men solvern har inte hunnit visa att det går",
  not_found: "Ingen lösning hittades med de ändringar som får föreslås",
  incomplete: "Sökningen hann inte klart",
}

export const repairTitle = (result: RepairResult): string => TITLES[result.status]

/** Bara ett förslag med minst en ändring kan föras över till formuläret. */
export const canApplyRepair = (result: RepairResult): boolean =>
  (result.status === "found" || result.status === "unproven") && Object.keys(result.parameters).length > 0

/** Verifierat = solvern hittade en lösning med förslaget; allt annat är inte bevisat. */
export const repairIsVerified = (result: RepairResult): boolean => result.status === "found" && result.verified !== null

export function repairVerifiedText(result: RepairResult): string {
  if (repairIsVerified(result)) return result.verified?.seconds != null ? `Solvern hittade en lösning med förslaget på ${result.verified.seconds} s.` : "Solvern hittade en lösning med förslaget."
  if (result.status === "unproven") return "Ingen lösning är hittad ännu: förslaget är inte bevisat."
  return ""
}

export function repairEffectText(result: RepairResult): string {
  const { before, after } = result.exams_without_occasion
  return before === 0 ? "" : `Tentor utan tillåtet tillfälle: ${before} → ${after}.`
}

export const repairProgressText = (current: string | null): string => current ? `${current} …` : "Söker …"
