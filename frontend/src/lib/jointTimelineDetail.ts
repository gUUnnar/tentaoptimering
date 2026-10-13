import { formatDuration, formatKr } from "./jointFormat.ts"
import { kindText } from "./jointKinds.ts"
import { STEP_INFO } from "./jointSteps.ts"
import type { KindStats, Timeline, TimelineBlock, TimelineSegment } from "./jointTimeline.ts"

// Texten som visas när man pekar på, fokuserar eller klickar ett segment i tidslinjen.

export type CheckLine = {
  kind: string; title: string; explanation: string
  /** T.ex. "4 av 6 dagar klara, 2 misslyckades". */
  counts: string
  /** Vad det ledde till när dagar inte gick. Null när alla gick. */
  consequence: string | null
}

export type SegmentDetail = {
  heading: string
  statusText: string
  timeText: string
  help: string
  checks: CheckLine[]
  notes: string[]
}

const STATUS = { running: "Pågår", done: "Klar", stopped: "Avbröts innan den blev klar" } as const

export function countsText(stats: KindStats): string {
  const days = stats.total !== null && stats.total >= stats.done ? `${stats.done} av ${stats.total} dagar klara` : `${stats.done} ${stats.done === 1 ? "dag" : "dagar"} klara`
  if (stats.failed === 0) return stats.done > 0 ? `${days}, ingen misslyckades` : days
  const timeout = stats.timedOut > 0 ? ` (varav ${stats.timedOut} nådde tidsgränsen)` : ""
  return `${days}, ${stats.failed} misslyckades${timeout}`
}

/** `previousFailed` är antalet dagar som inte gick i förra varvets dagkontroll, om det finns ett förra varv. */
export function segmentDetail(segment: TimelineSegment, block: TimelineBlock, previousFailed: number | null): SegmentDetail {
  const info = STEP_INFO[segment.step]
  const notes: string[] = []
  if (segment.boundOre !== null) notes.push(`Undre gräns som bevisades i det här varvet: ${formatKr(segment.boundOre)}.`)
  if (segment.step === "relaxation" && previousFailed !== null && previousFailed > 0) {
    notes.push(`Förra varvet hade ${previousFailed} ${previousFailed === 1 ? "dag" : "dagar"} som inte gick att genomföra; den grova planen räknades om.`)
  }
  if (segment.status === "stopped") notes.push("Körningen avslutades medan steget pågick.")
  return {
    heading: block.round !== null ? `${block.label}: ${info.label}` : info.label,
    statusText: STATUS[segment.status],
    timeText: `${formatDuration(segment.seconds)} (från ${formatDuration(segment.startedAt)} till ${formatDuration(segment.endedAt)} efter körningens start)`,
    help: info.help,
    checks: segment.checks.map(stats => {
      const text = kindText(stats.kind)
      return { kind: stats.kind, title: text.title, explanation: text.explanation, counts: countsText(stats), consequence: stats.failed > 0 ? text.failure : null }
    }),
    notes,
  }
}

/** Dagar som inte gick i dagkontrollen i varvet före `round`. Null om det inte finns något förra varv. */
export function previousRoundFailed(timeline: Timeline, round: number | null): number | null {
  if (round === null || round < 2) return null
  const previous = timeline.blocks.find(block => block.round === round - 1)
  const check = previous?.segments.find(segment => segment.step === "day_checks")
  return check ? check.failedDates.length : null
}
