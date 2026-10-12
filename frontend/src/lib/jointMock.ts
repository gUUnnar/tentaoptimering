import { ApiError, type JointApi } from "./jointApi.ts"
import {
  DEMO_RUN_ID, MOCK_CANDIDATES, MOCK_RUNS, MOCK_SCENARIOS, REJECTED_RUN_ID, buildFixtureEvents, fixtureSummary, fixtureWarmStart,
  type FixtureWarm,
} from "./jointFixture.ts"
import type { EventsResponse, FinishedEvent, JointEvent, SavedRun, StartJointRunBody } from "./jointTypes.ts"

// Mockad datakälla: spelar upp inspelade exempelhändelser i verklig tid (snabbad med ?speed=N, standard 8),
// så att gränssnittet kan utvecklas och visas utan backend. Aktiveras med ?mock=1.

type StoredRun = { events: JointEvent[]; warm: FixtureWarm; requested: string }
type Job = { startedMs: number; fixture: JointEvent[]; warm: FixtureWarm; requested: string; cancelAtMs: number | null; runId: string | null; settled: boolean }

const CANCEL_DELAY_MS = 1500
const storedRuns = new Map<string, StoredRun>()
const savedRuns: SavedRun[] = [...MOCK_RUNS]
const jobs = new Map<string, Job>()
let jobCounter = 0

function seedStored(): void {
  if (storedRuns.size) return
  storedRuns.set(DEMO_RUN_ID, { events: buildFixtureEvents("accepted"), warm: "accepted", requested: "auto" })
  storedRuns.set(REJECTED_RUN_ID, { events: buildFixtureEvents("rejected"), warm: "rejected", requested: REJECTED_RUN_ID })
}

function speed(): number {
  const value = Number(new URLSearchParams(typeof window === "undefined" ? "" : window.location.search).get("speed"))
  return Number.isFinite(value) && value > 0 ? value : 8
}

function warmFor(requested: string): FixtureWarm {
  if (requested === "none") return "none"
  return requested === REJECTED_RUN_ID ? "rejected" : "accepted"
}

function settle(jobId: string, job: Job, events: JointEvent[], scenario: string): string | null {
  if (job.settled) return job.runId
  job.settled = true
  const hasSolution = events.some(event => event.type === "incumbent")
  if (!hasSolution) return null
  job.runId = `mock-live-${jobId}`
  storedRuns.set(job.runId, { events, warm: job.warm, requested: job.requested })
  savedRuns.unshift({ run_id: job.runId, scenario_id: scenario, status: "completed", engine: "joint", created_at: new Date().toISOString() })
  return job.runId
}

export const mockJointApi: JointApi = {
  mock: true,
  listScenarios: async () => MOCK_SCENARIOS,
  listCandidates: async problemId => MOCK_CANDIDATES.filter(candidate => candidate.problem_id === problemId),
  async startRun(body: StartJointRunBody) {
    seedStored()
    const warm = warmFor(body.warm_start)
    const jobId = `mock-${++jobCounter}-${body.scenario}`
    jobs.set(jobId, { startedMs: Date.now(), fixture: buildFixtureEvents(warm), warm, requested: body.warm_start, cancelAtMs: null, runId: null, settled: false })
    return { job_id: jobId }
  },
  async events(jobId, after): Promise<EventsResponse> {
    const job = jobs.get(jobId)
    if (!job) throw new ApiError("Okänt jobb (mockläget glömmer jobb vid omladdning).", 404)
    const now = Date.now()
    const scenario = jobId.split("-").slice(2).join("-")
    const elapsedT = ((job.cancelAtMs ?? now) - job.startedMs) / 1000 * speed()
    const body = job.fixture.filter(event => event.type !== "finished" && event.t <= elapsedT)
    const natural = job.cancelAtMs === null && job.fixture.at(-1)!.t <= elapsedT
    if (job.cancelAtMs !== null && now >= job.cancelAtMs + CANCEL_DELAY_MS) {
      const incumbents = body.filter(event => event.type === "incumbent")
      const best = incumbents.at(-1)
      const bounds = body.filter(event => event.type === "bound")
      const finished: FinishedEvent = {
        seq: job.fixture.length + 1, t: elapsedT + 0.8, type: "finished", cancelled: true,
        outcome: best ? "feasible_not_proven" : "unknown",
        cost_ore: best?.type === "incumbent" ? best.cost_ore : null,
        bound_ore: bounds.length ? Math.max(...bounds.map(event => event.type === "bound" ? event.lower_ore : 0)) : null,
      }
      const all = [...body, finished]
      const runId = settle(jobId, job, all, scenario)
      return { status: "cancelled", events: all.filter(event => event.seq > after), last_seq: finished.seq, run_id: runId }
    }
    if (natural) {
      const all = job.fixture
      const runId = settle(jobId, job, all, scenario)
      return { status: "completed", events: all.filter(event => event.seq > after), last_seq: all.at(-1)!.seq, run_id: runId }
    }
    return { status: "running", events: body.filter(event => event.seq > after), last_seq: Math.max(after, body.at(-1)?.seq ?? 0), run_id: null }
  },
  async cancel(jobId) {
    const job = jobs.get(jobId)
    if (job && job.cancelAtMs === null) job.cancelAtMs = Date.now()
  },
  async runEvents(runId) {
    seedStored()
    const run = storedRuns.get(runId)
    if (!run) throw new ApiError("Körningen saknar sparade händelser.", 404)
    return run.events
  },
  async warmStart(runId) {
    seedStored()
    const run = storedRuns.get(runId)
    if (!run) return null
    return fixtureWarmStart(run.warm, run.requested, run.events)
  },
  async summary(runId) {
    seedStored()
    const run = storedRuns.get(runId)
    if (!run) throw new ApiError("Sammanfattning saknas för körningen.", 404)
    return fixtureSummary(run.events, run.warm)
  },
  async listRuns() { seedStored(); return savedRuns },
}
