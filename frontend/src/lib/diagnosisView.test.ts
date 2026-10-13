import assert from "node:assert/strict"
import { describe, it } from "node:test"
import type { DiagnosisChange, DiagnosisState, SavedDiagnosis } from "./diagnosisApi.ts"
import { changeLabel, conclusion } from "./diagnosisView.ts"

const days: DiagnosisChange = { id: "calendar.weekdays", section: "parameters", key: "calendar.weekdays", baseline: [1, 2, 3, 4, 5, 6, 7], run: [1, 2, 3, 4, 5] }
const times: DiagnosisChange = { id: "calendar.start_times", section: "parameters", key: "calendar.start_times", baseline: ["08:00"], run: ["08:00", "13:00"] }
const labels = { "calendar.weekdays": "Tillåtna veckodagar", "calendar.start_times": "Starttider" }
const saved = (over: Partial<SavedDiagnosis>): SavedDiagnosis => ({ run_id: "r", scenario_id: "s", probe_seconds: 30, complete: true, probes: [], culprits: [], baseline_infeasible: false, ...over })
const state = (over: Partial<SavedDiagnosis> | null): DiagnosisState => ({ scenario_id: "s", scenario_name: "Scenariot", changes: [days, times], saved: over ? saved(over) : null, job: null })

describe("utredning av en körning utan lösning", () => {
  it("namnger ändringar med etikett, annars id, och periodens datum för sig", () => {
    assert.equal(changeLabel(days, labels), "Tillåtna veckodagar")
    assert.equal(changeLabel(days, {}), "calendar.weekdays")
    assert.equal(changeLabel({ ...days, id: "subset.date_from", section: "subset", key: "date_from" }, labels), "Planeringsperiod, start")
  })
  it("ingen slutsats före en utredning", () => assert.equal(conclusion(state(null), labels), null))
  it("pekar ut en enskild orsak", () => {
    const result = conclusion(state({ culprits: ["calendar.weekdays"] }), labels)
    assert.equal(result?.tone, "cause")
    assert.match(result?.text ?? "", /"Tillåtna veckodagar" gör ensam/)
  })
  it("pekar ut flera orsaker", () => {
    assert.match(conclusion(state({ culprits: ["calendar.weekdays", "calendar.start_times"] }), labels)?.text ?? "", /Var och en av ändringarna .*Starttider/)
  })
  it("säger att det inte är ändringarna när utgångsscenariot redan saknar lösning", () => {
    const result = conclusion(state({ baseline_infeasible: true, culprits: ["calendar.weekdays"] }), labels)
    assert.equal(result?.tone, "other")
    assert.match(result?.text ?? "", /beror inte på dina ändringar/)
  })
  it("påstår ingen orsak när ingen ensam ändring bevisats, och nämner tidsgränsen", () => {
    const result = conclusion(state({}), labels)
    assert.equal(result?.tone, "unclear")
    assert.match(result?.text ?? "", /30 sekunder/)
  })
  it("en avbruten utredning ger ingen slutsats", () => assert.equal(conclusion(state({ complete: false, culprits: ["calendar.weekdays"] }), labels)?.tone, "unclear"))
})
