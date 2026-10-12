import assert from "node:assert/strict"
import { describe, it } from "node:test"
import { OPTIONS } from "./testing/optionsFixture.ts"
import { NO_ROOMS_DRAFT } from "./paramValues.ts"
import { byId, PARAMETERS } from "./testing/paramFixture.ts"
import { changesToRequest, collectErrors, computeChanges, crossErrors, filterParameters, groupParameters, isEditable, lockedParameters, splitServerErrors } from "./paramDiff.ts"

describe("ändringar jämfört med scenariot", () => {
  it("orörda parametrar och värden som skrivits tillbaka är inga ändringar", () => {
    assert.deepEqual(computeChanges(PARAMETERS, {}), [])
    assert.deepEqual(computeChanges(PARAMETERS, { "window.later_days": "0" }), [])
    assert.deepEqual(computeChanges(PARAMETERS, { "calendar.start_times": ["14:00", "08:00"] }), [])
    assert.deepEqual(computeChanges(PARAMETERS, { "cost.staff_session_ore": "1250" }), [])
  })

  it("en ändring visar gammalt och nytt värde i klartext", () => {
    const [change] = computeChanges(PARAMETERS, { "cost.staff_session_ore": "1300" })
    assert.equal(change.id, "cost.staff_session_ore")
    assert.equal(change.newValue, 130000)
    assert.equal(change.oldValue, 125000)
    assert.match(change.oldText, /^1\s250\skr per tillfälle$/)
    assert.match(change.newText, /^1\s300\skr per tillfälle$/)
    assert.equal(change.error, null)
  })

  it("scenariots värde (inte standardvärdet) är utgångspunkt", () => {
    const scenario = PARAMETERS.map(p => p.id === "window.later_days" ? { ...p, scenario_value: 5, value: 5, differs_from_default: true } : p)
    assert.deepEqual(computeChanges(scenario, { "window.later_days": "5" }), [])
    const [change] = computeChanges(scenario, { "window.later_days": "0" })
    assert.equal(change.oldText, "5 dagar")
    assert.equal(change.newText, "0 dagar")
  })

  it("ogiltigt utkast räknas som ändring med fel och skickas inte", () => {
    const changes = computeChanges(PARAMETERS, { "window.later_days": "tre", "demand.rounding": "nearest" })
    assert.equal(changes.length, 2)
    assert.match(changes.find(c => c.id === "window.later_days")!.error!, /heltal/)
    assert.deepEqual(changesToRequest(changes), { "demand.rounding": "nearest" })
  })

  it("låsta parametrar och parametrar utan redigerare ändras aldrig", () => {
    assert.deepEqual(computeChanges(PARAMETERS, { "rules.keep_course_order": false, "digital.compatibility_matrix": {} }), [])
  })

  it("trappan: ändrad rad ger en ändring, ogiltig trappa ger fel", () => {
    const good = computeChanges(PARAMETERS, { "staffing.ladder": [{ max: "60", staff: "1" }, { max: "150", staff: "2" }, { max: "300", staff: "3" }] })
    assert.equal(good[0].error, null)
    assert.equal((good[0].newValue as { max_participants: number }[])[0].max_participants, 60)
    const bad = computeChanges(PARAMETERS, { "staffing.ladder": [{ max: "100", staff: "1" }, { max: "100", staff: "2" }] })
    assert.match(bad[0].error!, /Rad 2/)
  })
})

describe("kontroller mellan parametrar och serverfel", () => {
  it("första datum efter sista datum", () => {
    const errors = crossErrors(PARAMETERS, { "calendar.start_date": "2027-06-01", "calendar.end_date": "2027-05-01" })
    assert.match(errors["calendar.end_date"], /före första datum/)
    assert.deepEqual(crossErrors(PARAMETERS, { "calendar.start_date": "2027-01-01", "calendar.end_date": "2027-05-01" }), {})
    assert.deepEqual(crossErrors(PARAMETERS, { "calendar.start_date": "2027-01-01" }), {})
  })

  it("serverfel läggs vid rätt rad, okända id:n hamnar i sammanfattningen och inget går förlorat", () => {
    const split = splitServerErrors([
      { id: "window.later_days", message: "Måste vara minst 0." }, { id: "window.later_days", message: "Högst 60." },
      { id: "okänd.parameter", message: "Finns inte." }, { id: "", message: "Allmänt fel." },
    ], PARAMETERS)
    assert.equal(split.byId["window.later_days"], "Måste vara minst 0. Högst 60.")
    assert.deepEqual(split.general, ["okänd.parameter: Finns inte.", "Allmänt fel."])
  })

  it("lokala fel går före serverfel för samma parameter", () => {
    const changes = computeChanges(PARAMETERS, { "window.later_days": "x" })
    const errors = collectErrors(changes, {}, { "window.later_days": "Serverns text.", "demand.rounding": "Annat fel." })
    assert.match(errors["window.later_days"], /heltal/)
    assert.equal(errors["demand.rounding"], "Annat fel.")
  })
})

describe("grupper och filter", () => {
  it("grupperar efter backendens ordning", () => {
    const groups = groupParameters(PARAMETERS)
    assert.equal(groups[0].group, "Tidsflexibilitet")
    assert.deepEqual(groups.map(g => g.group), [...new Set(groups.map(g => g.group))])
    assert.equal(groups.reduce((sum, g) => sum + g.items.length, 0), PARAMETERS.length)
  })

  it("gruppnamn och ordning kommer från katalogen (grupp-id visas som läsbart namn)", () => {
    const tagged = PARAMETERS.map(p => ({ ...p, group: p.group === "Tidsflexibilitet" ? "tid" : p.group === "Lokaler" ? "rum" : "ovrigt" }))
    const groups = groupParameters(tagged, { labels: { tid: "Tid och kalender", rum: "Lokaler", ovrigt: "Efterfrågan och övrigt" }, order: ["rum", "tid", "ovrigt"] })
    assert.deepEqual(groups.map(g => g.group), ["rum", "tid", "ovrigt"])
    assert.deepEqual(groups.map(g => g.label), ["Lokaler", "Tid och kalender", "Efterfrågan och övrigt"])
    assert.equal(groupParameters(tagged)[0].label, groupParameters(tagged)[0].group, "utan etiketter visas id:t")
    const found = filterParameters(tagged, { query: "kalender", showAdvanced: true, keep: new Set(), groupLabels: { tid: "Tid och kalender" } })
    assert.ok(found.some(p => p.id === "calendar.weekdays"))
  })

  it("avancerade parametrar döljs utom när de visas eller har ändrats", () => {
    const base = { query: "", showAdvanced: false, keep: new Set<string>() }
    assert.equal(filterParameters(PARAMETERS, base).some(p => p.id === "solver.seed"), false)
    assert.equal(filterParameters(PARAMETERS, { ...base, showAdvanced: true }).some(p => p.id === "solver.seed"), true)
    assert.equal(filterParameters(PARAMETERS, { ...base, keep: new Set(["solver.seed"]) }).some(p => p.id === "solver.seed"), true)
  })

  it("sökning på namn, id, hjälptext och grupp", () => {
    const find = (query: string) => filterParameters(PARAMETERS, { query, showAdvanced: true, keep: new Set() }).map(p => p.id)
    assert.deepEqual(find("vaktkostnad"), ["cost.staff_session_ore"])
    assert.ok(find("STAFFING").includes("staffing.ladder"))
    assert.ok(find("bemanning").length >= 2)
    assert.equal(byId("solver.seed").advanced, true)
  })
})

describe("parametrar som inte kan ändras", () => {
  const base = { query: "", showAdvanced: true, keep: new Set<string>() }
  it("är bortfiltrerade som standard och visas på begäran", () => {
    const hidden = filterParameters(PARAMETERS, base)
    assert.equal(hidden.some(param => !isEditable(param)), false)
    const shown = filterParameters(PARAMETERS, { ...base, showLocked: true })
    assert.equal(shown.length - hidden.length, lockedParameters(PARAMETERS).length)
    assert.ok(lockedParameters(PARAMETERS).length > 0)
  })
  it("antalet som visas stämmer med totalen minus de bortfiltrerade", () => {
    const visible = filterParameters(PARAMETERS, { ...base, showAdvanced: false })
    const hiddenCount = PARAMETERS.length - visible.length
    const expected = PARAMETERS.filter(param => !isEditable(param) || param.advanced).length
    assert.equal(hiddenCount, expected)
    assert.equal(filterParameters(PARAMETERS, { ...base, showAdvanced: false, showLocked: true }).length, PARAMETERS.length - PARAMETERS.filter(param => param.advanced).length)
  })
  it("salar och flyttbara typer är låsta utan alternativ ur underlaget och redigerbara med dem", () => {
    const [rooms, types] = [byId("rooms.selection"), byId("flex.movable_types")]
    for (const param of [rooms, types]) {
      assert.equal(isEditable(param), false, param.id)
      assert.equal(isEditable(param, null), false, param.id)
      assert.equal(isEditable(param, OPTIONS), true, param.id)
      assert.equal(filterParameters(PARAMETERS, base).some(item => item.id === param.id), false)
      assert.equal(filterParameters(PARAMETERS, { ...base, showLocked: true }).some(item => item.id === param.id), true)
      assert.equal(filterParameters(PARAMETERS, { ...base, options: OPTIONS }).some(item => item.id === param.id), true)
      assert.ok(lockedParameters(PARAMETERS).some(item => item.id === param.id))
      assert.equal(lockedParameters(PARAMETERS, OPTIONS).some(item => item.id === param.id), false)
    }
  })
  it("en sal som inte finns bland alternativen är ett fel, och ändringen räknas bara med alternativen", () => {
    assert.deepEqual(computeChanges(PARAMETERS, { "rooms.selection": ["A-101"] }), [])
    const [change] = computeChanges(PARAMETERS, { "rooms.selection": ["A-101", "A-102"] }, OPTIONS)
    assert.deepEqual([change.newValue, change.error, change.newText], [["A-101", "A-102"], null, "2 salar: A-101, A-102"])
    assert.equal(change.oldText, "Alla salar")
    const unknown = computeChanges(PARAMETERS, { "rooms.selection": ["Z-9"] }, OPTIONS)[0]
    assert.match(unknown.error ?? "", /Z-9.*finns inte/)
    assert.equal(computeChanges(PARAMETERS, { "rooms.selection": [NO_ROOMS_DRAFT] }, OPTIONS)[0].error, "Minst en sal måste vara vald.")
  })
  it("sökning hittar inte låsta parametrar förrän de visas", () => {
    const query = "ordningen inom kurs"
    assert.equal(filterParameters(PARAMETERS, { ...base, query }).length, 0)
    assert.equal(filterParameters(PARAMETERS, { ...base, query, showLocked: true }).length, 1)
  })
})
