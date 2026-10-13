import type { FinishedEvent, JointEvent, PhaseName, WarmStartEvent } from "./jointTypes.ts"
import { timelineSummary } from "./jointTimelineSummary.ts"
import { warmStartBadge, warmStartSentence } from "./jointFormat.ts"

// Tidslinje över det som faktiskt körs, byggd av händelserna. Samma modell används i livevy, resultatvy och uppspelning.

export type SegmentStatus = "running" | "done" | "stopped"
export type BlockStatus = "pending" | "running" | "done" | "skipped" | "stopped"
export type BlockKind = "warm_start" | "round" | "final"

/** Kontroller av en typ inom ett steg. `total` är null när körningen inte rapporterat hur många som ingår. */
export type KindStats = { kind: string; total: number | null; done: number; failed: number; infeasible: number; timedOut: number }

export type TimelineSegment = {
  id: string
  step: PhaseName
  /** Varvet segmentet hör till. Null för kontrollen av förra körningen och slutkontrollen. */
  round: number | null
  startedAt: number
  endedAt: number
  seconds: number
  status: SegmentStatus
  /** Andel av tidslinjens bredd, 0–1, med en lägsta synlig bredd. */
  share: number
  checks: KindStats[]
  /** Datum som inte gick att genomföra (infeasible eller tidsgräns) i segmentets kontroller. */
  failedDates: string[]
  /** Undre gräns som bevisades i det här varvet (bara för grov plan). */
  boundOre: number | null
}

export type TimelineBlock = {
  id: string; kind: BlockKind; label: string; round: number | null
  segments: TimelineSegment[]; status: BlockStatus; seconds: number; share: number
  /** Utfall eller skäl i klartext, t.ex. varför kontrollen av förra körningen hoppades över. */
  note: string | null
}

export type Timeline = {
  blocks: TimelineBlock[]
  rounds: number
  /** Dagar som inte gick att genomföra i dagkontrollerna, utan dubbletter. */
  failedDays: string[]
  summary: string
  running: boolean
  ended: "completed" | "cancelled" | "failed" | null
}

export const MIN_SHARE = 0.04

/** Fördelar bredden proportionellt mot tiden men ger varje del minst `min`. Summan blir 1. */
export function layoutShares(durations: number[], min = MIN_SHARE): number[] {
  const n = durations.length
  if (n === 0) return []
  const total = durations.reduce((sum, value) => sum + Math.max(0, value), 0)
  if (total <= 0 || n * min >= 1) return durations.map(() => 1 / n)
  const fixed = new Set<number>()
  let shares: number[] = []
  for (let pass = 0; pass <= n; pass++) {
    const free = durations.map((_, i) => i).filter(i => !fixed.has(i))
    const remaining = 1 - fixed.size * min
    const freeTotal = free.reduce((sum, i) => sum + Math.max(0, durations[i]), 0)
    shares = durations.map((value, i) => fixed.has(i) ? min : freeTotal > 0 ? Math.max(0, value) / freeTotal * remaining : remaining / free.length)
    const small = free.filter(i => shares[i] < min)
    if (!small.length) break
    small.forEach(i => fixed.add(i))
  }
  return shares
}

// ---- Uppbyggnad ----------------------------------------------------------------------------------------------------

type Instance = { total: number; done: number }
type Draft = {
  step: PhaseName; round: number | null; startedAt: number; endedAt: number | null
  instances: Map<string, Instance[]>; statuses: Map<string, Map<string, string>>
}

const isFailure = (status: string) => status === "infeasible" || status === "unknown"

/** En omgång kontroller (batch) börjar när räknaren står på noll, minskar eller totalen ändras. */
function track(draft: Draft, kind: string, total: number, done: number): void {
  const list = draft.instances.get(kind) ?? []
  const current = list.at(-1)
  if (!current || done === 0 || done < current.done || total !== current.total) list.push({ total, done })
  else current.done = done
  draft.instances.set(kind, list)
}

function statsOf(draft: Draft): KindStats[] {
  const kinds = [...new Set([...draft.instances.keys(), ...draft.statuses.keys()])]
  return kinds.map(kind => {
    const instances = draft.instances.get(kind) ?? []
    const statuses = [...(draft.statuses.get(kind)?.values() ?? [])]
    const infeasible = statuses.filter(status => status === "infeasible").length
    const timedOut = statuses.filter(status => status === "unknown").length
    const batchDone = instances.reduce((sum, item) => sum + item.done, 0)
    return {
      kind, total: instances.length ? instances.reduce((sum, item) => sum + item.total, 0) : null,
      done: Math.max(batchDone, statuses.length), failed: infeasible + timedOut, infeasible, timedOut,
    }
  })
}

function failedDatesOf(draft: Draft): string[] {
  return [...new Set([...draft.statuses.values()].flatMap(map => [...map].filter(([, status]) => isFailure(status)).map(([date]) => date)))].sort()
}

/**
 * Bygger tidslinjen. `nowT` är körningens tid just nu och avgör hur långt ett pågående segment sträcker sig.
 * Faser kan upprepas (grov plan, dagkontroll, rättning och ursprungliga tider körs en gång per varv); varje
 * start av den grova planen inleder ett nytt varv.
 */
export function buildTimeline(events: JointEvent[], nowT: number): Timeline {
  const sorted = [...events].sort((a, b) => a.seq - b.seq)
  const drafts: Draft[] = []
  let open: Draft | null = null
  let round = 0
  let warm: WarmStartEvent | null = null
  let finishedEvent: FinishedEvent | null = null
  const bounds = new Map<number, number>()
  for (const event of sorted) {
    switch (event.type) {
      case "phase": {
        if (event.state === "started") {
          if (open && open.endedAt === null) open.endedAt = event.t
          if (event.name === "relaxation") round += 1
          else if (round === 0 && event.name !== "warm_start_check" && event.name !== "finalize") round = 1
          const outside = event.name === "warm_start_check" || event.name === "finalize"
          open = { step: event.name, round: outside ? null : round, startedAt: event.t, endedAt: null, instances: new Map(), statuses: new Map() }
          drafts.push(open)
        } else {
          for (let i = drafts.length - 1; i >= 0; i--) {
            if (drafts[i].step === event.name && drafts[i].endedAt === null) { drafts[i].endedAt = event.t; if (open === drafts[i]) open = null; break }
          }
        }
        break
      }
      case "batch": { const target = open ?? drafts.at(-1); if (target) track(target, event.kind, event.total, event.done); break }
      case "day": {
        const target = open ?? drafts.at(-1)
        if (target) {
          const map = target.statuses.get(event.kind) ?? new Map<string, string>()
          map.set(event.date, event.status)
          target.statuses.set(event.kind, map)
        }
        break
      }
      case "bound": bounds.set(event.round, Math.max(bounds.get(event.round) ?? 0, event.lower_ore)); break
      case "warm_start": warm = event; break
      case "finished": finishedEvent = event; break
      default: break
    }
  }
  const finished = finishedEvent as FinishedEvent | null
  const ended: Timeline["ended"] = finished === null ? null : finished.cancelled ? "cancelled" : finished.outcome === "failed" ? "failed" : "completed"
  const segments = drafts.map((draft, index): TimelineSegment => {
    const status: SegmentStatus = draft.endedAt !== null ? "done" : ended === null ? "running" : ended === "completed" ? "done" : "stopped"
    const end = draft.endedAt ?? (finished ? finished.t : Math.max(nowT, draft.startedAt))
    const endedAt = Math.max(end, draft.startedAt)
    return {
      id: `${index}-${draft.step}`, step: draft.step, round: draft.round, startedAt: draft.startedAt, endedAt, seconds: endedAt - draft.startedAt, status, share: 0,
      checks: statsOf(draft), failedDates: failedDatesOf(draft),
      boundOre: draft.step === "relaxation" && draft.round !== null ? bounds.get(draft.round) ?? null : null,
    }
  })
  return assemble(segments, warm as WarmStartEvent | null, finished, ended)
}

function blockStatus(segments: TimelineSegment[]): BlockStatus {
  if (segments.some(item => item.status === "running")) return "running"
  return segments.some(item => item.status === "stopped") ? "stopped" : "done"
}

function assemble(segments: TimelineSegment[], warm: WarmStartEvent | null, finished: FinishedEvent | null, ended: Timeline["ended"]): Timeline {
  const rounds = Math.max(0, ...segments.map(item => item.round ?? 0))
  const blocks: TimelineBlock[] = []

  const warmSegments = segments.filter(item => item.step === "warm_start_check")
  const warmDecided = warm !== null || segments.length > 0 || finished !== null
  const warmSentence = warm ? warmStartSentence(warm.decision, warm.explanation) : null
  blocks.push({
    id: "warm", kind: "warm_start", label: "Kontroll av förra körningen", round: null, segments: warmSegments, seconds: 0, share: 0,
    status: warmSegments.length ? blockStatus(warmSegments) : warmDecided ? "skipped" : "pending",
    note: warmSegments.length ? (warm ? [warmStartBadge(warm.decision), warmSentence].filter(Boolean).join(". ") : null)
      : warmDecided ? warmSentence ?? "Ingen kontroll av förra körningen registrerades." : null,
  })

  for (let r = 1; r <= rounds; r++) {
    const list = segments.filter(item => item.round === r)
    blocks.push({ id: `round-${r}`, kind: "round", label: `Varv ${r}`, round: r, segments: list, status: blockStatus(list), seconds: 0, share: 0, note: null })
  }

  const finalSegments = segments.filter(item => item.step === "finalize")
  const finalSkipped = ended === "cancelled" ? "Körningen stoppades innan slutkontrollen." : ended === "failed" ? "Körningen misslyckades innan slutkontrollen." : "Ingen slutkontroll registrerades."
  blocks.push({
    id: "final", kind: "final", label: "Slutkontroll och sparande", round: null, segments: finalSegments, seconds: 0, share: 0,
    status: finalSegments.length ? blockStatus(finalSegments) : finished ? "skipped" : "pending",
    note: !finalSegments.length && finished ? finalSkipped : null,
  })

  // Bredd: varje segment, och varje block utan segment, får en andel proportionell mot tiden men minst MIN_SHARE.
  type Item = { segment: TimelineSegment | null; block: TimelineBlock }
  const items = blocks.flatMap((block): Item[] => block.segments.length ? block.segments.map(segment => ({ segment, block })) : [{ segment: null, block }])
  const shares = layoutShares(items.map(item => item.segment?.seconds ?? 0))
  items.forEach((item, index) => { if (item.segment) item.segment.share = shares[index]; item.block.share += shares[index] })
  blocks.forEach(block => { block.seconds = block.segments.reduce((sum, item) => sum + item.seconds, 0) })

  const dayChecks = segments.filter(item => item.step === "day_checks")
  const failedDays = [...new Set(dayChecks.flatMap(item => item.failedDates))].sort()
  const failedBeforeLast = new Set(dayChecks.filter(item => (item.round ?? 0) < rounds).flatMap(item => item.failedDates))
  return {
    blocks, rounds, failedDays, ended, running: ended === null && segments.length > 0,
    summary: timelineSummary({
      rounds, failedBeforeLast: failedBeforeLast.size, failedDays: failedDays.length,
      dayChecked: dayChecks.some(item => item.checks.some(check => check.done > 0)), ended, running: ended === null,
    }),
  }
}
