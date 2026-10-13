import type {
  DayStatus, JointEvent, JointSummary, WarmStartRecord,
} from "../jointTypes.ts"

// Syntetiska exempelhändelser som TESTDATA för logiktesterna. Formen följer API-kontraktet; värdena är påhittade
// men har samma storleksordning som kontrollkörningen i docs/OPTIMERINGSSTRATEGI.md avsnitt 8. De är inte mätdata.
// Appkod får aldrig importera den här filen (säkras av ett test).

export type FixtureWarm = "accepted" | "rejected" | "none"
type Draft = Record<string, unknown> & { t: number; type: JointEvent["type"] }

export const DEMO_RUN_ID = "test-2027-vt-demo"
export const REJECTED_RUN_ID = "test-avvisad-start"

function weekdays(count: number): string[] {
  const days: string[] = []
  const cursor = new Date(Date.UTC(2027, 0, 11))
  while (days.length < count) {
    if (cursor.getUTCDay() !== 0 && cursor.getUTCDay() !== 6) days.push(cursor.toISOString().slice(0, 10))
    cursor.setUTCDate(cursor.getUTCDate() + 1)
  }
  return days
}

const DAYS = weekdays(73)

/**
 * Bygger en batch: en day_started- och en day-händelse per kontroll samt en batch-händelse efter varje färdig kontroll.
 * `withStarts: false` efterliknar äldre körningar som saknar händelsen day_started.
 */
function batch(
  out: Draft[], start: number, kind: string, dates: string[], parallel: number, workers: number,
  statusOf: (i: number) => DayStatus, secondsPer: number, options: { withStarts?: boolean; blocks?: Record<number, string[]> } = {},
): number {
  const counts: Record<string, number> = {}
  const withStarts = options.withStarts !== false
  let end = start
  dates.forEach((date, i) => {
    // Kontrollerna körs i omgångar om `parallel` åt gången och varje kontroll tar `secondsPer` sekunder.
    const startedAt = start + Math.floor(i / parallel) * secondsPer
    const t = startedAt + secondsPer
    const status = statusOf(i)
    counts[status] = (counts[status] ?? 0) + 1
    if (withStarts) out.push({ t: startedAt, type: "day_started", date, kind })
    const block = options.blocks?.[i]
    out.push({ t, type: "day", date, kind, status, seconds: Math.round(secondsPer * 10) / 10, ...(block ? { block } : {}) })
    out.push({ t: t + 0.01, type: "batch", kind, total: dates.length, done: i + 1, parallel, workers_per_check: workers, statuses: { ...counts } })
    end = t + 0.01
  })
  return end
}

export function buildFixtureEvents(warm: FixtureWarm): JointEvent[] {
  const out: Draft[] = []
  let t = 0
  out.push({ t: 0, type: "resources", threads: 8, memory_mb: 4096, parallel_checks: 4, workers_per_check: 2 })
  if (warm !== "none") {
    out.push({ t: 0.3, type: "phase", name: "warm_start_check", state: "started" })
    const failing = warm === "rejected" ? new Set([12, 13, 40, 41, 55]) : new Set<number>()
    t = batch(out, 0.3, "warm_start", DAYS, 4, 2, i => failing.has(i) ? "infeasible" : i % 6 === 0 ? "feasible" : "optimal", 1.2)
    out.push({ t: t + 0.2, type: "phase", name: "warm_start_check", state: "finished" })
    t += 0.4
    if (warm === "accepted") {
      out.push({ t, type: "warm_start", decision: "accepted", explanation: "Alla 73 dagar klarade omkontrollen mot de nya reglerna.", source_run_id: REJECTED_RUN_ID })
      out.push({ t: t + 0.1, type: "incumbent", cost_ore: 182_300_000, source: "warm start", changed_exams: 0 })
    } else {
      out.push({ t, type: "warm_start", decision: "rejected", explanation: "5 av 73 dagar klarade inte omkontrollen; placeringen användes inte som lösning.", source_run_id: REJECTED_RUN_ID })
    }
    t += 0.3
  } else {
    out.push({ t: 0.2, type: "warm_start", decision: "not_used", explanation: "Ingen varmstart begärdes.", source_run_id: null })
    t = 0.3
  }

  out.push({ t, type: "phase", name: "relaxation", state: "started" })
  out.push({ t: t + 22, type: "bound", lower_ore: 168_700_000, round: 1 })
  out.push({ t: t + 53, type: "bound", lower_ore: 173_900_000, round: 2 })
  const relaxEnd = t + 55
  out.push({ t: relaxEnd, type: "phase", name: "relaxation", state: "finished" })

  out.push({ t: relaxEnd + 0.1, type: "phase", name: "day_checks", state: "started" })
  const checkEnd = batch(out, relaxEnd + 0.1, "economic_plan", DAYS, 8, 1, i => i === 17 || i === 18 ? "infeasible" : i === 44 ? "unknown" : i % 9 === 0 ? "feasible" : "optimal", 2.4)
  out.push({ t: checkEnd + 0.1, type: "phase", name: "day_checks", state: "finished" })

  const repairStart = checkEnd + 0.2
  out.push({ t: repairStart, type: "phase", name: "repair", state: "started" })
  const repairEnd = batch(out, repairStart, "repair", [DAYS[17], DAYS[44]], 2, 2, i => i === 1 ? "optimal" : "feasible", 5, { blocks: { 0: [DAYS[17], DAYS[18]] } })
  out.push({ t: repairEnd + 0.1, type: "phase", name: "repair", state: "finished" })
  out.push({ t: repairEnd + 0.2, type: "incumbent", cost_ore: 180_500_000, source: "round 1", changed_exams: 412 })

  const historyStart = repairEnd + 0.3
  out.push({ t: historyStart, type: "phase", name: "history", state: "started" })
  const groups = [DAYS[3], DAYS[9], DAYS[22], DAYS[31], DAYS[50], DAYS[63]]
  const historyEnd = batch(out, historyStart, "history", groups, 3, 2, i => i === 4 ? "infeasible" : "optimal", 4)
  out.push({ t: historyEnd - 8, type: "incumbent", cost_ore: 180_200_000, source: "round 1 history", changed_exams: 351 })
  out.push({ t: historyEnd - 1, type: "incumbent", cost_ore: 180_050_000, source: "round 2 history", changed_exams: 300 })
  out.push({ t: historyEnd + 0.1, type: "phase", name: "history", state: "finished" })

  out.push({ t: historyEnd + 0.2, type: "phase", name: "finalize", state: "started" })
  out.push({ t: historyEnd + 2.5, type: "phase", name: "finalize", state: "finished" })
  out.push({ t: historyEnd + 2.6, type: "finished", outcome: "feasible_not_proven", cost_ore: 180_050_000, bound_ore: 173_900_000, cancelled: false })

  return out.sort((a, b) => a.t - b.t).map((draft, index) => ({ ...draft, seq: index + 1 }) as unknown as JointEvent)
}

export function fixtureWarmStart(warm: FixtureWarm, requested: string, events: JointEvent[]): WarmStartRecord {
  const firstSolution = events.find(event => event.type === "incumbent")?.t ?? null
  const execution = { threads: 8, memory_mb: 4096, parallel_day_checks: true, workers_per_check: 2 }
  if (warm === "none") {
    return { decision: "not_used", explanation: "Ingen varmstart begärdes; körningen startade kallt.", requested, source: null, changed_parameters: [], recheck: null, execution }
  }
  const rejected = warm === "rejected"
  return {
    decision: rejected ? "rejected" : "accepted",
    explanation: rejected
      ? "Den tidigare placeringen klarade inte omkontrollen mot de nya reglerna för 5 av 73 dagar och användes därför inte som lösning."
      : "Den tidigare placeringen klarade omkontrollen dag för dag mot de nya reglerna och blev första verifierade lösning.",
    requested,
    source: { run_id: REJECTED_RUN_ID, cost_ore: 182_300_000, technical_validation_now: rejected ? "fail" : "pass", result_sha256: "9f2c41ab07d3e5c8b16a0f4e2d7c93b5a8e1f60d4c2b7a9e3f1d85c60b2a7e41" },
    changed_parameters: ["calendar.exam_periods.extra_week", "cost.external_session_ore"],
    recheck: {
      status: rejected ? "rejected_days_failed" : "accepted",
      reasons: rejected ? ["5 dagar saknar genomförbar bemanning med den ändrade raster-regeln", "2 tentor saknar tillåtet pass efter ändrad tentamensperiod"] : [],
      notes: ["Omkontrollen gjordes med exakt dagmodell, inte mot sparad status."],
      exams_reused: rejected ? 1_212 : 1_268, exams_without_start: 0, exams_not_allowed: rejected ? 56 : 0,
      days_checked: 73, days_failed: rejected ? 5 : 0, check_seconds: 22.4,
      verified_cost_ore: rejected ? null : 182_300_000, hint_exams: rejected ? 1_212 : 0,
      first_solution_seconds: firstSolution, first_solution_source: rejected ? "round 1" : "warm start",
      final_cost_ore: 180_050_000, final_source: "round 2 history", interrupted: false,
    },
    execution,
  }
}

export function fixtureSummary(events: JointEvent[], warm: FixtureWarm): JointSummary {
  const finished = events.find(event => event.type === "finished")
  const firstIncumbent = events.find(event => event.type === "incumbent")
  const last = events.at(-1)
  const cost = finished?.type === "finished" ? finished.cost_ore : null
  const bound = finished?.type === "finished" ? finished.bound_ore : null
  const lastIncumbent = [...events].reverse().find(event => event.type === "incumbent")
  const outcome = finished?.type === "finished" && finished.cancelled ? "cancelled" : finished?.type === "finished" ? finished.outcome : "unknown"
  return {
    run_id: DEMO_RUN_ID, problem_id: "term-vt-2027", scenario_id: "joint_test", created_at: "2026-10-11T09:12:00",
    cost_ore: cost, bound_ore: bound, gap_ore: cost !== null && bound !== null ? cost - bound : null,
    gap: cost && bound !== null ? Math.max(0, (cost - bound) / cost) : null,
    changed_exams: lastIncumbent?.type === "incumbent" ? lastIncumbent.changed_exams : null, exams_total: 1172, staff_pool_size: 41,
    first_solution_seconds: firstIncumbent?.t ?? null, first_solution_basis: "solver_start", first_solution_source: "warm start",
    wall_seconds: last?.t ?? null, outcome, proven_optimum: outcome === "optimal", has_verified_solution: outcome !== "unknown", cancelled: outcome === "cancelled",
    warm_start_decision: warm === "none" ? "not_used" : warm, parameters_changed_from_default: [], parameters_changed_count: 0, period: { date_from: null, date_to: null }, planning_basis: null, unverified_reason: null,
    technical_validation: "pass", business_verification: "not_evaluated", provenance: "not_evaluated",
  }
}
