import type { DayStatus } from "./jointTypes.ts"

// Texter per kontrolltyp (`kind` i händelserna). Användaren ska aldrig se lösarens engelska namn.

export type KindText = {
  /** Rubrik. */
  title: string
  /** Vad kontrollen gör. */
  explanation: string
  /** Vad det betyder när en dag "går inte", och vad som händer då. Null om typen saknar ett sådant utfall. */
  failure: string | null
}

const WARM_START: KindText = {
  title: "Kontroll av förra körningens placering",
  explanation: "Förra körningens placering prövas dag för dag mot de nya reglerna.",
  failure: "Tentorna ryms inte längre på dagen enligt de nya reglerna. Förra körningens placering kan därför inte användas som startpunkt.",
}
const DAY: KindText = {
  title: "Kontroll av varje dag",
  explanation: "Varje dag prövas mot den grova planens lokaler och bemanning.",
  failure: "Dagen går inte att genomföra med den grova planens lokaler och bemanning. Den utreds och rättas i stegen efter.",
}
const DIAGNOSIS: KindText = {
  title: "Utredning av dagar som inte gick",
  explanation: "Dagen prövas utan bemanningsgräns för att ta reda på varför den inte gick.",
  failure: "Dagen går inte att genomföra ens utan bemanningsgräns med de valda lokalerna: de rymmer aldrig dessa tentor samma dag. Den grova planen ändras därför i nästa varv.",
}
const REPAIR: KindText = {
  title: "Rättning tillsammans med granndagar",
  explanation: "Dagen löses om tillsammans med dagen före och efter, så att tentor får flyttas dit.",
  failure: "Dagen gick inte att rätta ens tillsammans med grannarna. En reservplan med fler lokaler eller vakter används i stället.",
}
const FALLBACK: KindText = {
  title: "Reservplan med fler lokaler eller vakter",
  explanation: "Reservplan: dagen får fler lokaler eller vakter. Det blir dyrare men ger en giltig lösning.",
  failure: "Ingen lösning hittades ens med fler lokaler eller vakter.",
}
const HISTORY: KindText = {
  title: "Försök att behålla ursprungliga tider",
  explanation: "Försöker flytta tentor tillbaka till sina ursprungliga tider utan att kostnaden ökar.",
  failure: "Ursprungliga tider fungerar inte för dessa dagar; ändringen genomförs inte.",
}
const CORE: KindText = {
  title: "Sökning efter orsaken till problemet",
  explanation: "Letar efter vilka tentor som tillsammans orsakar problemet.",
  failure: "Sökningen gav inget entydigt svar för dagen.",
}
const OTHER: KindText = {
  title: "Övriga kontroller",
  explanation: "Kontroller av en typ som gränssnittet inte har någon beskrivning av.",
  failure: "Dagen gick inte att genomföra i den här kontrollen.",
}

const KINDS: Record<string, KindText> = {
  "warm-start": WARM_START, day: DAY, diagnosis: DIAGNOSIS, repair: REPAIR, fallback: FALLBACK, history: HISTORY, core: CORE,
  // Äldre och alternativa namn som förekommer i sparade körningar.
  warm_start: WARM_START, warm_start_check: WARM_START, day_checks: DAY, economic_plan: DAY, exact: DAY, history_swap: HISTORY,
}

export const kindText = (kind: string): KindText => KINDS[kind] ?? OTHER
export const kindLabel = (kind: string): string => kindText(kind).title

export const TIMEOUT_TEXT = "Kontrollen hann inte bli klar inom tidsgränsen och gav inget säkert svar."

/** Förklaring av en dags status. "Går inte" beror på kontrolltypen. */
export function dayStatusHelp(status: DayStatus | "pending" | "running", kind: string): string {
  switch (status) {
    case "pending": return "Dagen har inte kontrollerats ännu."
    case "running": return "Dagen kontrolleras just nu."
    case "optimal": return "Dagen går att genomföra och är bevisat den billigaste möjliga för dagen."
    case "feasible": return "Dagen går att genomföra, men det är inte bevisat att den är billigast möjliga."
    case "infeasible": return kindText(kind).failure ?? OTHER.failure!
    case "unknown": return TIMEOUT_TEXT
  }
}
