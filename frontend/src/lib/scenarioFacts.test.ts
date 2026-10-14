import assert from "node:assert/strict"
import { describe, it } from "node:test"
import { toJointScenario } from "./jointApi.ts"
import type { PeriodCheck } from "./jointTypes.ts"
import { FEATURED_PARAM_IDS, featuredParameters, otherParameters } from "./featuredParams.ts"
import { defaultScenarioId, referenceFirst } from "./jointScenarioInfo.ts"
import { scenarioFacts } from "./scenarioFacts.ts"

const scenario = toJointScenario({ id: "s", name: "S", description: "Alla tentor i underlaget, 12 januari till 31 mars 2026.", subset: { plan_area: "Uppsala", selection: "rule", exam_count: 1172, description: "Alla tentor 2026-01-12 till 2026-03-31" } })
const check = { ready_events: 40 } as PeriodCheck

describe("fakta om det som ska köras", () => {
  it("visar tentor, område, period och underlag, var och en en gång", () => {
    const facts = scenarioFacts(scenario, null, null, null, { preparedAt: "2026-10-13T12:40:00+00:00", state: "current" })
    assert.deepEqual(facts.map(fact => fact.key), ["exams", "area", "period", "underlay"])
    assert.match(facts[0].text, /^1\s172 tentor$/)
    assert.equal(facts[1].text, "Uppsala")
    assert.equal(facts[2].text, "12 januari–31 mars 2026")
    assert.equal(facts[3].attention, false)
  })
  it("ett valt datumintervall och dess tentor går före scenariots egna", () => {
    const facts = scenarioFacts(scenario, { from: "2026-02-02", to: "2026-02-06" }, check, null, null)
    assert.equal(facts.find(fact => fact.key === "exams")?.text, "40 tentor")
    assert.equal(facts.find(fact => fact.key === "period")?.text, "2026-02-02 – 2026-02-06")
    assert.equal(facts.some(fact => fact.key === "underlay"), false)
  })
  it("antalet för ett valt intervall väntar på serverns kontroll i stället för att visa scenariots antal", () => {
    assert.equal(scenarioFacts(scenario, { from: "2026-02-02", to: "2026-02-06" }, null, null, null).some(fact => fact.key === "exams"), false)
  })
  it("ett underlag som inte är aktuellt markeras", () => {
    const fact = scenarioFacts(scenario, null, null, null, { preparedAt: "2026-10-13T12:40:00+00:00", state: "stale" }).find(item => item.key === "underlay")
    assert.equal(fact?.attention, true)
    assert.match(fact?.text ?? "", /inte aktuellt/)
  })
})

describe("utvalda parametrar", () => {
  const param = (id: string) => ({ id, label: id, order: 0, group: "g" }) as never
  it("visas i fast ordning och bara om de finns, och resten hamnar under Fler parametrar", () => {
    const all = ["solver.seed", "calendar.start_times", "calendar.weekdays", "okänd.parameter"].map(param)
    assert.deepEqual(featuredParameters(all).map(item => (item as { id: string }).id), ["calendar.weekdays", "calendar.start_times"])
    assert.deepEqual(otherParameters(all).map(item => (item as { id: string }).id), ["solver.seed", "okänd.parameter"])
  })
  it("listan har inga dubbletter", () => assert.equal(new Set(FEATURED_PARAM_IDS).size, FEATURED_PARAM_IDS.length))
})

describe("förvalt scenario", () => {
  it("referensen är förvald och står först, annars det första", () => {
    const list = [{ id: "joint_real_subset" }, { id: "joint_base" }, { id: "joint_underlay_period" }]
    assert.equal(defaultScenarioId(list), "joint_base")
    assert.deepEqual(referenceFirst(list).map(item => item.id), ["joint_base", "joint_real_subset", "joint_underlay_period"])
    assert.equal(defaultScenarioId([{ id: "a" }, { id: "b" }]), "a")
    assert.equal(defaultScenarioId([]), "")
  })
})
