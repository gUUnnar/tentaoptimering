import type { Constraint, DiagnosisChange, DiagnosisProbe, DiagnosisState, ProbeKind } from "./diagnosisApi.ts"

/** Namn på en ändring: parameterns etikett, annars id. Periodens datum (urvalet) heter "Planeringsperiod". */
export function changeLabel(change: DiagnosisChange, labels: Record<string, string>): string {
  if (change.section === "subset") return change.key === "date_from" ? "Planeringsperiod, start" : change.key === "date_to" ? "Planeringsperiod, slut" : `Urval: ${change.key}`
  return labels[change.id] ?? change.id
}

export const probeFor = (state: DiagnosisState, id: string): DiagnosisProbe | undefined => state.saved?.probes.find(probe => probe.id === id)

export const PROBE_TEXT: Record<ProbeKind, string> = {
  infeasible: "Omöjlig ensam",
  solution: "Går att lösa",
  inconclusive: "Oklart",
}

export const PROBE_HINT: Record<ProbeKind, string> = {
  infeasible: "Scenariot med bara den här ändringen saknar bevisat lösning.",
  solution: "Scenariot med bara den här ändringen hittade en lösning.",
  inconclusive: "Ingen lösning hittades och omöjligheten bevisades inte inom tidsgränsen.",
}

export type Conclusion = { tone: "cause" | "other" | "unclear"; text: string }

/** Slutsatsen av en färdig utredning, i klartext. Null medan ingen utredning finns. */
export function conclusion(state: DiagnosisState, labels: Record<string, string>): Conclusion | null {
  const saved = state.saved
  if (!saved) return null
  if (!saved.complete) return { tone: "unclear", text: "Utredningen avbröts innan den blev klar, så ingen slutsats kan dras." }
  if (saved.baseline_infeasible) return { tone: "other", text: `Det beror inte på dina ändringar: scenariot "${state.scenario_name}" saknar lösning redan utan dem.` }
  const names = saved.culprits.map(id => state.changes.find(change => change.id === id)).flatMap(change => change ? [`"${changeLabel(change, labels)}"`] : [])
  if (names.length === 1) return { tone: "cause", text: `Ändringen ${names[0]} gör ensam att det inte finns någon lösning.` }
  if (names.length > 1) return { tone: "cause", text: `Var och en av ändringarna ${names.join(", ")} gör ensam att det inte finns någon lösning.` }
  return { tone: "unclear", text: `Ingen enskild ändring kunde bevisas göra problemet omöjligt. Ändringarna kan samverka, eller så hann sökningen inte klart på ${saved.probe_seconds} sekunder per prov.` }
}

/** Raderna i begränsningslistan: de gällande begränsningarna, och därefter ändringar som inte är en av dem (till exempel vald period). */
export function constraintRows(state: DiagnosisState): Constraint[] {
  const known = new Set(state.constraints.map(item => item.id))
  const extra: Constraint[] = state.changes.filter(change => !known.has(change.id)).map(change => ({ id: change.id, value: change.run, source: "changed" }))
  return [...state.constraints, ...extra]
}
