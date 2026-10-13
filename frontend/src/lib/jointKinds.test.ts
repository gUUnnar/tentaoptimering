import assert from "node:assert/strict"
import { describe, it } from "node:test"
import { dayStatusHelp, kindLabel, kindText, TIMEOUT_TEXT } from "./jointKinds.ts"
import { scenarioDetails, runtimeEstimate } from "./jointScenarioInfo.ts"
import { toJointScenario } from "./jointApi.ts"

const KINDS = ["warm-start", "day", "diagnosis", "repair", "fallback", "history", "core"]
const ENGLISH = /\b(day|diagnosis|warm-start|warm start|fallback|core|repair|history|relaxation|batch)\b/i

describe("förklaringar per kontrolltyp", () => {
  it("varje typ har egen rubrik och egen förklaring, och ingen text är engelsk", () => {
    const titles = new Set(KINDS.map(kind => kindText(kind).title))
    assert.equal(titles.size, KINDS.length)
    for (const kind of KINDS) {
      const text = kindText(kind)
      assert.doesNotMatch(`${text.title} ${text.explanation} ${text.failure ?? ""}`, ENGLISH, kind)
    }
    assert.doesNotMatch(kindLabel("något-okänt"), ENGLISH)
  })

  it("exakta förklaringar", () => {
    assert.equal(kindText("warm-start").explanation, "Förra körningens placering prövas dag för dag mot de nya reglerna.")
    assert.equal(kindText("day").explanation, "Varje dag prövas mot den grova planens lokaler och bemanning.")
    assert.equal(kindText("diagnosis").explanation, "Dagen prövas utan bemanningsgräns för att ta reda på varför den inte gick.")
    assert.equal(kindText("repair").explanation, "Dagen löses om tillsammans med dagen före och efter, så att tentor får flyttas dit.")
    assert.equal(kindText("fallback").explanation, "Reservplan: dagen får fler lokaler eller vakter. Det blir dyrare men ger en giltig lösning.")
    assert.equal(kindText("history").explanation, "Försöker flytta tentor tillbaka till sina ursprungliga tider utan att kostnaden ökar.")
    assert.equal(kindText("core").explanation, "Letar efter vilka tentor som tillsammans orsakar problemet.")
  })

  it('"Går inte" är olika för varje typ och diagnosen säger inte längre att dagen rättas i nästa steg', () => {
    const failures = KINDS.map(kind => kindText(kind).failure)
    assert.equal(new Set(failures).size, KINDS.length)
    assert.equal(dayStatusHelp("infeasible", "diagnosis"), "Dagen går inte att genomföra ens utan bemanningsgräns med de valda lokalerna: de rymmer aldrig dessa tentor samma dag. Den grova planen ändras därför i nästa varv.")
    assert.doesNotMatch(dayStatusHelp("infeasible", "diagnosis"), /rättas i nästa steg/)
    assert.equal(dayStatusHelp("infeasible", "day"), "Dagen går inte att genomföra med den grova planens lokaler och bemanning. Den utreds och rättas i stegen efter.")
    assert.equal(dayStatusHelp("infeasible", "repair"), "Dagen gick inte att rätta ens tillsammans med grannarna. En reservplan med fler lokaler eller vakter används i stället.")
    assert.equal(dayStatusHelp("infeasible", "fallback"), "Ingen lösning hittades ens med fler lokaler eller vakter.")
    assert.equal(dayStatusHelp("infeasible", "history"), "Ursprungliga tider fungerar inte för dessa dagar; ändringen genomförs inte.")
    assert.match(dayStatusHelp("infeasible", "warm-start"), /^Tentorna ryms inte längre på dagen/)
  })

  it("äldre och alternativa kindnamn mappas till rätt typ, okända får en neutral text", () => {
    assert.equal(kindText("economic_plan"), kindText("day"))
    assert.equal(kindText("warm_start"), kindText("warm-start"))
    assert.equal(kindText("history_swap"), kindText("history"))
    assert.equal(kindLabel("zzz"), "Övriga kontroller")
    assert.equal(dayStatusHelp("unknown", "day"), TIMEOUT_TEXT)
  })
})

describe("scenariots period ur dess egna uppgifter", () => {
  const scenario = toJointScenario({
    id: "joint_underlay_period", name: "Alla tentor i underlaget (12 jan–31 mars 2026)", problem_id: "joint_underlay_period_2026",
    description: "Alla tentor som är klara för modellering i Uppsala i underlaget, 12 januari till 31 mars 2026, planerade tillsammans: datum, salar och bemanning. Underlaget innehåller inga tentor efter 31 mars; tentor i april–juni ingår därför inte.",
    subset: { plan_area: "Uppsala", selection: "rule", exam_count: 1172, description: "Alla tentor som är klara för modellering i Uppsala med ursprungsdatum 2026-01-12 till 2026-03-31 (1172 tentor)." },
  })
  it("period och upplysning om att underlaget saknar senare tentor", () => {
    const details = scenarioDetails(scenario)
    assert.equal(details.period, "12 januari–31 mars 2026")
    assert.equal(details.coverageNote, "Underlaget innehåller inga tentor efter 31 mars; tentor i april–juni ingår därför inte.")
    assert.doesNotMatch(details.description, /Underlaget innehåller inga tentor efter/)
    assert.match(details.description, /^Alla tentor som är klara/)
  })
  it("scenario utan period eller upplysning påstår ingenting", () => {
    const details = scenarioDetails(toJointScenario({ id: "s", name: "S", description: "Tolv tentor.", subset: { plan_area: "Uppsala", selection: "event_list", exam_count: 12, description: "12 namngivna tentor i Uppsala." } }))
    assert.deepEqual(details, { period: null, coverageNote: null, description: "Tolv tentor." })
    assert.deepEqual(scenarioDetails(undefined), { period: null, coverageNote: null, description: "" })
  })
  it("gränssnittets texter påstår inte hela terminen eller VT", () => {
    assert.doesNotMatch(runtimeEstimate(1172)!.text, /hela terminen|\bVT\b/i)
    assert.doesNotMatch(`${scenarioDetails(scenario).period} ${scenario.name}`, /hela terminen|\bVT\b/i)
  })
})
