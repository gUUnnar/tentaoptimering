export type SummaryInput = {
  rounds: number
  /** Dagar som inte gick i varv före det sista, alltså de som kan ha föranlett ett nytt varv. */
  failedBeforeLast: number
  failedDays: number
  /** Har någon dagkontroll rapporterat färdiga dagar? */
  dayChecked: boolean
  ended: "completed" | "cancelled" | "failed" | null
  running: boolean
}

const days = (count: number) => `${count} ${count === 1 ? "dag" : "dagar"}`

/** Sammanfattning i klartext. Det som inte är känt utelämnas; inget fylls i på gissning. */
export function timelineSummary(input: SummaryInput): string {
  const { rounds, ended } = input
  if (rounds === 0) return ""
  const head = `${input.running ? "Hittills " : ""}${rounds} varv`
  let detail = ""
  if (rounds >= 2) {
    const changes = rounds - 1
    detail = `den grova planen ändrades ${changes} ${changes === 1 ? "gång" : "gånger"}`
    if (input.failedBeforeLast > 0) detail += ` eftersom ${days(input.failedBeforeLast)} inte gick att genomföra`
  } else if (input.failedDays > 0) {
    detail = `${days(input.failedDays)} gick inte att genomföra med den grova planen`
  } else if (input.dayChecked) {
    detail = "alla dagar gick att genomföra med den grova planen"
  }
  const tail = ended === "cancelled" ? " Körningen stoppades." : ended === "failed" ? " Körningen misslyckades." : ""
  return `${head}${detail ? `: ${detail}` : ""}.${tail}`
}
