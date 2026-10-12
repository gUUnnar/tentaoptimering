import type {
  BatchEvent, DayStatus, FinishedEvent, IncumbentEvent, JointEvent, PhaseName, ResourcesEvent, WarmStartEvent,
} from "./jointTypes.ts"

// Ren avledning av vyernas tillstånd ur en händelselista. Samma kod används för live och uppspelning.

export type PhaseRun = { name: PhaseName; startedAt: number; finishedAt: number | null }
export type BoundPoint = { t: number; lower_ore: number; round: number }
export type IncumbentPoint = { t: number; cost_ore: number; source: string; changed_exams: number }
export type DayCell = { date: string; kind: string; status: DayStatus; seconds: number; t: number; block?: string[] }

export type JointState = {
  phases: PhaseRun[]
  batches: Record<string, BatchEvent>
  days: Record<string, DayCell[]> // per kontrolltyp, i ankomstordning
  /** Påbörjade men ännu inte färdiga dagkontroller per kontrolltyp (datum -> starttid). Nyckeln finns när händelsen day_started har förekommit. */
  started: Record<string, Record<string, number>>
  incumbents: IncumbentPoint[]
  bounds: BoundPoint[]
  warmStart: WarmStartEvent | null
  resources: ResourcesEvent | null
  finished: FinishedEvent | null
  lastT: number
  lastSeq: number
}

export const emptyJointState = (): JointState => ({
  phases: [], batches: {}, days: {}, started: {}, incumbents: [], bounds: [], warmStart: null, resources: null, finished: null, lastT: 0, lastSeq: 0,
})

export function applyEvent(state: JointState, event: JointEvent): JointState {
  const next: JointState = { ...state, lastT: Math.max(state.lastT, event.t), lastSeq: Math.max(state.lastSeq, event.seq) }
  switch (event.type) {
    case "phase": {
      if (event.state === "started") { next.phases = [...state.phases, { name: event.name, startedAt: event.t, finishedAt: null }]; break }
      const index = findLastOpen(state.phases, event.name)
      // En avslutad fas utan registrerad start visas med nolltid hellre än att tappas.
      next.phases = index < 0 ? [...state.phases, { name: event.name, startedAt: event.t, finishedAt: event.t }]
        : state.phases.map((run, i) => i === index ? { ...run, finishedAt: event.t } : run)
      break
    }
    case "batch": next.batches = { ...state.batches, [event.kind]: event }; break
    case "day": {
      const cells = state.days[event.kind] ?? []
      const cell: DayCell = { date: event.date, kind: event.kind, status: event.status, seconds: event.seconds, t: event.t, ...(event.block ? { block: event.block } : {}) }
      const at = cells.findIndex(item => item.date === event.date)
      next.days = { ...state.days, [event.kind]: at < 0 ? [...cells, cell] : cells.map((item, i) => i === at ? cell : item) }
      if (event.kind in state.started) {
        const { [event.date]: _done, ...rest } = state.started[event.kind]
        next.started = { ...state.started, [event.kind]: rest }
      }
      break
    }
    case "day_started":
      next.started = { ...state.started, [event.kind]: { ...(state.started[event.kind] ?? {}), [event.date]: event.t } }
      break
    case "incumbent": next.incumbents = [...state.incumbents, toIncumbent(event)]; break
    case "bound": next.bounds = [...state.bounds, { t: event.t, lower_ore: event.lower_ore, round: event.round }]; break
    case "warm_start": next.warmStart = event; break
    case "resources": next.resources = event; break
    case "finished": next.finished = event; break
  }
  return next
}

const toIncumbent = (event: IncumbentEvent): IncumbentPoint => ({ t: event.t, cost_ore: event.cost_ore, source: event.source, changed_exams: event.changed_exams })

function findLastOpen(phases: PhaseRun[], name: PhaseName): number {
  for (let i = phases.length - 1; i >= 0; i--) if (phases[i].name === name && phases[i].finishedAt === null) return i
  return -1
}

export function foldEvents(events: JointEvent[], from: JointState = emptyJointState()): JointState {
  return events.reduce(applyEvent, from)
}

/** Lägger till nya händelser och ignorerar sådana som redan finns (sekvensnumret avgör), så att omtagen polling är ofarlig. */
export function mergeEvents(existing: JointEvent[], incoming: JointEvent[]): JointEvent[] {
  const seen = new Set(existing.map(event => event.seq))
  const added = incoming.filter(event => !seen.has(event.seq))
  return added.length ? [...existing, ...added].sort((a, b) => a.seq - b.seq) : existing
}

// ---- Härledda mått -------------------------------------------------------------------------------------------

export const bestIncumbent = (state: JointState): IncumbentPoint | null => state.incumbents.at(-1) ?? null
export const firstIncumbent = (state: JointState): IncumbentPoint | null => state.incumbents[0] ?? null
export const bestBoundOre = (state: JointState): number | null =>
  state.bounds.length ? Math.max(...state.bounds.map(point => point.lower_ore)) : null

/** Verifierad kostnad (övre gräns) enligt sista kända uppgift; slutuppgiften väger tyngre än mellanläget. */
export function currentCostOre(state: JointState): number | null {
  return state.finished?.cost_ore ?? bestIncumbent(state)?.cost_ore ?? null
}
export function currentBoundOre(state: JointState): number | null {
  return state.finished?.bound_ore ?? bestBoundOre(state)
}

/** Gap som bråkdel av verifierad kostnad: (kostnad - undre gräns) / kostnad. */
export function gapFraction(costOre: number | null, boundOre: number | null): number | null {
  if (costOre === null || boundOre === null || costOre <= 0) return null
  return Math.max(0, (costOre - boundOre) / costOre)
}

export type DayGridCell =
  | { kind: "known"; cell: DayCell }
  /** Kontrollen har börjat (händelsen day_started). */
  | { kind: "running"; date: string; startedAt: number }
  /** Ej påbörjad. `running: true` är en uppskattning och används bara när körningen saknar händelsen day_started. */
  | { kind: "pending"; running: boolean }

/** Har körningen rapporterat verkligt påbörjade dagar för den här kontrolltypen? */
export const hasRealStarts = (state: JointState, kind: string): boolean => kind in state.started

/** Dagrutnätet för en kontrolltyp: färdiga och pågående dagar med datum, därefter anonyma rutor för dem som inte rapporterats. */
export function dayGrid(state: JointState, kind: string): DayGridCell[] {
  const finished = state.finished !== null
  // En kontroll som upprepas med alla trådar startar om efter att den redan rapporterats klar; då gäller den nya starten.
  const doneAt = new Map((state.days[kind] ?? []).map(cell => [cell.date, cell.t]))
  const running = finished ? [] : Object.entries(state.started[kind] ?? {}).filter(([date, startedAt]) => startedAt > (doneAt.get(date) ?? -1))
    .map(([date, startedAt]): DayGridCell => ({ kind: "running", date, startedAt }))
  const runningDates = new Set(running.map(cell => cell.kind === "running" ? cell.date : ""))
  const known = (state.days[kind] ?? []).filter(cell => !runningDates.has(cell.date)).map((cell): DayGridCell => ({ kind: "known", cell }))
  const dateOf = (cell: DayGridCell) => cell.kind === "known" ? cell.cell.date : cell.kind === "running" ? cell.date : ""
  const cells = [...known, ...running].sort((a, b) => dateOf(a).localeCompare(dateOf(b)))
  const batch = state.batches[kind]
  if (!batch) return cells
  const missing = Math.max(0, batch.total - cells.length)
  // Utan händelsen day_started (äldre körningar och uppspelning) uppskattas pågående: så många som kontrollerna kan köra samtidigt.
  const estimated = !hasRealStarts(state, kind) && !finished && missing > 0 ? Math.min(Math.max(1, batch.parallel), missing) : 0
  for (let i = 0; i < missing; i++) cells.push({ kind: "pending", running: i < estimated })
  return cells
}

export const dayKinds = (state: JointState): string[] => {
  const kinds = new Set([...Object.keys(state.batches), ...Object.keys(state.days)])
  return [...kinds]
}

/** Aktiv batch (för räknaren "kontroller samtidigt"): den senaste vars kontroller inte är klara. */
export function activeBatch(state: JointState): BatchEvent | null {
  if (state.finished) return null
  const open = Object.values(state.batches).filter(batch => batch.done < batch.total)
  return open.sort((a, b) => b.t - a.t)[0] ?? null
}

export function dayCounts(cells: DayGridCell[]): Record<string, number> {
  const counts: Record<string, number> = { pending: 0, running: 0, optimal: 0, feasible: 0, infeasible: 0, unknown: 0 }
  for (const cell of cells) {
    if (cell.kind === "pending") counts[cell.running ? "running" : "pending"] += 1
    else if (cell.kind === "running") counts.running += 1
    else counts[cell.cell.status] += 1
  }
  return counts
}

type Point = { t: number; upper?: number; lower?: number }

/** Stegserier för verifierad kostnad (övre gräns) och bevisad undre gräns, i Mkr över körningens tid. */
export function costSeries(state: JointState, nowT: number): Point[] {
  const times = new Set<number>([0, ...state.incumbents.map(p => p.t), ...state.bounds.map(p => p.t)])
  const end = Math.max(nowT, state.lastT, ...times)
  times.add(end)
  return [...times].sort((a, b) => a - b).map(t => {
    const upper = [...state.incumbents].reverse().find(p => p.t <= t)
    const lowers = state.bounds.filter(p => p.t <= t)
    return {
      t,
      upper: upper ? upper.cost_ore / 100_000_000 : undefined,
      lower: lowers.length ? Math.max(...lowers.map(p => p.lower_ore)) / 100_000_000 : undefined,
    }
  })
}
