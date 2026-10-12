import assert from "node:assert/strict"
import { describe, it } from "node:test"
import { ApiError, errorFromBody, normalizeChangedParameters, toJointScenario, toJointSummary, type BackendSummary } from "./jointApi.ts"
import { subsetText, runtimeEstimate } from "./jointScenarioInfo.ts"

const backend: BackendSummary = {
  run_id: "run-2", problem_id: "term-vt-2027", scenario_id: "joint_real_subset", created_at: "2026-10-12T10:00:00",
  solver_outcome: "feasible_not_proven", has_verified_solution: true, cost_is_proven_optimum: false,
  cost_ore: 182300000, lower_bound_ore: 177300000, gap_ore: 5000000, gap_relative: 0.027,
  changed_exams: 242, exams_total: 1172, staff_pool_size: 41, wall_time_seconds: 299.2,
  first_solution_seconds: 109.6, first_solution_basis: "solver_start", first_solution_source: "round 1", cancelled: false,
  warm_start_decision: "accepted", parameters_changed_from_default: ["cost.staff_session_ore"],
  verdicts: { technical_validation: "pass", business_verification: "not_evaluated", provenance: "not_evaluated", technically_validated: true, source: "joint_validation.json" },
}

describe("översättning av backendens sammanfattning", () => {
  it("byter fältnamn och håller de tre domarna isär", () => {
    const summary = toJointSummary(backend)
    assert.equal(summary.bound_ore, 177300000)
    assert.equal(summary.gap, 0.027)
    assert.equal(summary.gap_ore, 5000000)
    assert.equal(summary.wall_seconds, 299.2)
    assert.equal(summary.staff_pool_size, 41)
    assert.equal(summary.exams_total, 1172)
    assert.equal(summary.first_solution_basis, "solver_start")
    assert.equal(summary.warm_start_decision, "accepted")
    assert.equal(summary.proven_optimum, false)
    assert.deepEqual([summary.technical_validation, summary.business_verification, summary.provenance], ["pass", "not_evaluated", "not_evaluated"])
    assert.deepEqual(summary.parameters_changed_from_default, [{ id: "cost.staff_session_ore", label: null }])
  })
  it("bevisat optimum kommer från cost_is_proven_optimum eller utfallet optimal", () => {
    assert.equal(toJointSummary({ ...backend, cost_is_proven_optimum: true }).proven_optimum, true)
    assert.equal(toJointSummary({ ...backend, cost_is_proven_optimum: undefined, solver_outcome: "optimal" }).proven_optimum, true)
  })
  it("en körning utan verifierad lösning markeras, och saknade domar blir aldrig godkända", () => {
    const summary = toJointSummary({ ...backend, has_verified_solution: false, cancelled: true, verdicts: undefined as never })
    assert.equal(summary.has_verified_solution, false)
    assert.equal(summary.cancelled, true)
    assert.deepEqual([summary.technical_validation, summary.business_verification, summary.provenance], ["not_evaluated", "not_evaluated", "not_evaluated"])
  })
  it("tål olika former av listan över ändrade parametrar", () => {
    assert.deepEqual(normalizeChangedParameters(["a", "b"]), [{ id: "a", label: null }, { id: "b", label: null }])
    assert.deepEqual(normalizeChangedParameters([{ id: "a", label: "Namn", old: 1 }]), [{ id: "a", label: "Namn" }])
    assert.deepEqual(normalizeChangedParameters({ a: 1, b: 2 }), [{ id: "a", label: null }, { id: "b", label: null }])
    assert.deepEqual(normalizeChangedParameters(undefined), [])
    assert.deepEqual(normalizeChangedParameters([3, null]), [])
  })
})

describe("felsvar från API:et", () => {
  it("422 med fel per parameter bevaras", () => {
    const error = errorFromBody(422, { detail: { errors: [{ id: "window.later_days", message: "För stort." }, { id: "calendar.weekdays", message: "Tom." }] } })
    assert.ok(error instanceof ApiError)
    assert.equal(error.status, 422)
    assert.deepEqual(error.errors, [{ id: "window.later_days", message: "För stort." }, { id: "calendar.weekdays", message: "Tom." }])
    assert.equal(error.message, "2 värden är ogiltiga.")
  })
  it("ett enda fel ger felets text som meddelande", () => {
    assert.equal(errorFromBody(422, { detail: { errors: [{ id: "x", message: "Fel text." }] } }).message, "Fel text.")
  })
  it("detail som text, standardlistan från FastAPI och tomt svar", () => {
    assert.equal(errorFromBody(409, { detail: "Namnet finns redan." }).message, "Namnet finns redan.")
    assert.equal(errorFromBody(422, { detail: [{ msg: "field required" }, { msg: "andra" }] }).message, "field required andra")
    assert.equal(errorFromBody(500, {}).message, "Anropet misslyckades (HTTP 500).")
    assert.equal(errorFromBody(500, null).status, 500)
  })
})

describe("scenarier och körtid", () => {
  it("scenario utan problem_id får namnet som problem-id (saknat problem_id)", () => {
    assert.equal(toJointScenario({ id: "joint_real_subset", name: "joint_real_subset_2026" }).problem_id, "joint_real_subset_2026")
    assert.equal(toJointScenario({ id: "a", name: "b", problem_id: "c" }).problem_id, "c")
  })
  const full = toJointScenario({ id: "s", name: "S", subset: { plan_area: "Uppsala", selection: "rule", exam_count: 1172, description: "Hela terminen, Uppsala" } })
  it("urvalet i klartext med antal tentor", () => {
    assert.match(subsetText(full), /^Hela terminen, Uppsala, 1\s172 tentor$/)
    const named = toJointSummaryLike("Hela terminen, 1 172 tentor", 1172)
    assert.equal(subsetText(named), "Hela terminen, 1 172 tentor")
    assert.equal(subsetText(toJointScenario({ id: "s", name: "S" })), "")
    assert.equal(subsetText(toJointScenario({ id: "s", name: "S", subset: { plan_area: "Visby", selection: "event_list", exam_count: null, description: "" } })), "Visby")
  })
  it("ärlig körtidsuppgift beroende på antal tentor", () => {
    assert.equal(runtimeEstimate(null), null)
    assert.match(runtimeEstimate(1172)!.text, /2–5 minuter/)
    assert.equal(runtimeEstimate(1172)!.long, true)
    assert.equal(runtimeEstimate(12)!.long, false)
    assert.match(runtimeEstimate(12)!.text, /under en minut/)
  })
})

function toJointSummaryLike(description: string, exam_count: number) {
  return toJointScenario({ id: "s", name: "S", subset: { plan_area: "Uppsala", selection: "rule", exam_count, description } })
}
