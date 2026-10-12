import type {
  BatchEvent, DayStatus, FinishedEvent, IncumbentEvent, JointEvent, PhaseName, ResourcesEvent, WarmStartEvent,
} from "./jointTypes.ts"

// Ren avledning av vyernas tillstånd ur en händelselista. Samma kod används för live och uppspelning.

export type PhaseRun = { name: PhaseName; startedAt: number; finishedAt: number | null }
export type BoundPoint = { t: number; lower_ore: number; round: number }
export type IncumbentPoint = { t: number; cost_ore: number; source: string; changed_exams: number }
export type DayCell = { date: string; kind: string; status: DayStatus; seconds: number; t: number }

export type JointState = {
  phases: PhaseRun[]
  batches: Record<string, BatchEvent>
  days: Record<string, DayCell[]> // per kontrolltyp, i ankomstordning
  incumbents: IncumbentPoint[]
  bounds: BoundPoint[]
  warmStart: WarmStartEvent | null
  resources: ResourcesEvent | null
  finished: FinishedEvent | null
  lastT: number
  lastSeq: number
}

export const emptyJointState = (): JointState => ({
  phases: [], batches: {}, days: {}, incumbents: [], bounds: [], warmStart: null, resources: null, finished: null, lastT: 0, lastSeq: 0,
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
      const cell: DayCell = { date: event.date, kind: event.kind, status: event.status, seconds: event.seconds, t: event.t }
      const at = cells.findIndex(item => item.date === event.date)
      next.days = { ...state.days, [event.kind]: at < 0 ? [...cells, cell] : cells.map((item, i) => i === at ? cell : item) }
      break
    }
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

export type StepId = "warm_start_check" | "relaxation" | "day_checks" | "repair_history" | "finalize"
export type StepState = "pending" | "active" | "done" | "skipped"
export const STEP_DEFS: { id: StepId; label: string; phases: PhaseName[] }[] = [
  { id: "warm_start_check", label: "Varmstartkontroll", phases: ["warm_start_check"] },
  { id: "relaxation", label: "Relaxation", phases: ["relaxation"] },
  { id: "day_checks", label: "Dagkontroller", phases: ["day_checks"] },
  { id: "repair_history", label: "Reparation / historik", phases: ["repair", "history"] },
  { id: "finalize", label: "Klart", phases: ["finalize"] },
]

export type StepView = { id: StepId; label: string; state: StepState; seconds: number; repeats: number }

/** Förbrukad tid per steg. `nowT` är körningens aktuella tid i sekunder och används bara för pågående faser. */
export function stepViews(state: JointState, nowT: number): StepView[] {
  const finished = state.finished !== null
  const views = STEP_DEFS.map((def): StepView => {
    const runs = state.phases.filter(run => def.phases.includes(run.name))
    const seconds = runs.reduce((sum, run) => sum + Math.max(0, (run.finishedAt ?? Math.max(nowT, run.startedAt)) - run.startedAt), 0)
    const open = runs.some(run => run.finishedAt === null)
    return { id: def.id, label: def.label, seconds, repeats: runs.length, state: open && !finished ? "active" : runs.length ? "done" : "pending" }
  })
  // Steg utan körning som ligger före ett senare påbörjat steg (eller efter körningens slut) markeras som överhoppade.
  const lastStarted = views.reduce((last, view, index) => view.repeats ? index : last, -1)
  return views.map((view, index) => {
    if (view.state !== "pending") return view
    if (index < lastStarted || (finished && index !== views.length - 1)) return { ...view, state: "skipped" }
    return view
  })
}

export type DayGridCell =
  | { kind: "known"; cell: DayCell }
  | { kind: "pending"; running: boolean }

/** Dagrutnätet för en kontrolltyp. Dagar som ännu inte rapporterats saknar datum i kontraktet och visas som anonyma rutor. */
export function dayGrid(state: JointState, kind: string): DayGridCell[] {
  const known = [...(state.days[kind] ?? [])].sort((a, b) => a.date.localeCompare(b.date))
  const batch = state.batches[kind]
  const cells: DayGridCell[] = known.map(cell => ({ kind: "known", cell }))
  if (!batch) return cells
  const missing = Math.max(0, batch.total - known.length)
  const active = state.finished === null && missing > 0
  // Kontraktet har ingen "dag påbörjad"-händelse: så många rutor som kontrollerna kan köra samtidigt visas som pågående.
  const running = active ? Math.min(Math.max(1, batch.parallel), missing) : 0
  for (let i = 0; i < missing; i++) cells.push({ kind: "pending", running: i < running })
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
