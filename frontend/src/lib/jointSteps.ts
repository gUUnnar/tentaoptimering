import type { PhaseName } from "./jointTypes.ts"

// Körningens steg som användaren ser dem. Samma text används i tidslinjen, teckenförklaringen och detaljrutan.

export type StepInfo = { label: string; short: string; help: string }

export const STEP_INFO: Record<PhaseName, StepInfo> = {
  warm_start_check: {
    label: "Kontroll av förra körningen", short: "Förra körningen",
    help: "Förra körningens placering prövas mot de nya reglerna, dag för dag.",
  },
  relaxation: {
    label: "Grov plan och undre gräns", short: "Grov plan",
    help: "En förenklad modell väljer datum och lokaler och bevisar en lägsta möjlig kostnad.",
  },
  day_checks: {
    label: "Kontroll av varje dag", short: "Dagkontroll",
    help: "Varje dag prövas noga: ryms tentorna och finns bemanning?",
  },
  repair: {
    label: "Utredning och rättning", short: "Rättning",
    help: "Dagar som inte gick utreds och rättas, om nödvändigt med en reservplan.",
  },
  history: {
    label: "Försök att behålla ursprungliga tider", short: "Ursprungliga tider",
    help: "Modellen försöker flytta tentor tillbaka till sina ursprungliga tider utan att kostnaden ökar.",
  },
  finalize: {
    label: "Slutkontroll och sparande", short: "Slutkontroll",
    help: "Resultatet kontrolleras av en fristående kontroll och sparas.",
  },
}

export const STEP_ORDER: PhaseName[] = ["warm_start_check", "relaxation", "day_checks", "repair", "history", "finalize"]
