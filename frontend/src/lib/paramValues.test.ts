import assert from "node:assert/strict"
import { describe, it } from "node:test"
import { byId, PARAMETERS } from "./testing/paramFixture.ts"
import { formatMoneyOre, formatWithUnit, oreToKrText, parseKrToOre, unitInfo } from "./paramUnits.ts"
import {
  baselineValue, hasEditor, isValidDate, isValidTime, isWeekdayParam, parseDraft, parseInteger, parseNumber, sameValue, toDraft, validateLadder,
} from "./paramValues.ts"
import { formatParamValue } from "./paramFormat.ts"

describe("enheter och kronor/öre", () => {
  it("känner igen belopp i öre och visar dem som kronor", () => {
    assert.deepEqual(unitInfo("ore_per_session"), { money: true, label: "kr per tillfälle" })
    assert.deepEqual(unitInfo("ore_per_year"), { money: true, label: "kr per år" })
    assert.deepEqual(unitInfo("öre"), { money: true, label: "kr" })
    assert.deepEqual(unitInfo("öre/timme"), { money: true, label: "kr per timme" })
    assert.deepEqual(unitInfo("minutes"), { money: false, label: "minuter" })
    assert.deepEqual(unitInfo("percent"), { money: false, label: "%" })
    assert.deepEqual(unitInfo(null), { money: false, label: "" })
    assert.deepEqual(unitInfo("okänd enhet"), { money: false, label: "okänd enhet" })
  })

  it("öre till kronor som redigerbar text", () => {
    assert.equal(oreToKrText(125000), "1250")
    assert.equal(oreToKrText(125050), "1250,5")
    assert.equal(oreToKrText(125005), "1250,05")
    assert.equal(oreToKrText(5), "0,05")
    assert.equal(oreToKrText(0), "0")
    assert.equal(oreToKrText(-250), "-2,5")
  })

  it("kronor till öre utan flyttalsfel", () => {
    const ore = (text: string) => { const r = parseKrToOre(text); return r.ok ? r.ore : r.error }
    assert.equal(ore("1250"), 125000)
    assert.equal(ore("1250,50"), 125050)
    assert.equal(ore("1 250.5"), 125050)
    assert.equal(ore("1.15"), 115)
    assert.equal(ore("0,07"), 7)
    assert.equal(ore("-3"), -300)
    assert.match(String(ore("12,345")), /högst två decimaler/)
    assert.match(String(ore("")), /belopp/)
    assert.match(String(ore("abc")), /högst två decimaler/)
  })

  it("omvandlingen är symmetrisk för heltalsöre", () => {
    for (const value of [0, 1, 9, 10, 99, 100, 101, 12345, 125000, 99999999]) {
      assert.deepEqual(parseKrToOre(oreToKrText(value)), { ok: true, ore: value })
    }
  })

  it("visar belopp och enheter på svenska", () => {
    assert.match(formatMoneyOre(125050), /^1\s250,5\skr$/)
    assert.match(formatWithUnit(125000, "ore_per_session"), /^1\s250\skr per tillfälle$/)
    assert.equal(formatWithUnit(30, "minutes"), "30 minuter")
    assert.match(formatWithUnit(10, "percent"), /^10\s%$/)
    assert.equal(formatWithUnit(0.01, "fraction"), "0,01 andel (0–1)")
  })
})

describe("tolkning av tal, datum och tid", () => {
  it("heltal och decimaltal", () => {
    assert.deepEqual(parseInteger("12"), { ok: true, value: 12 })
    assert.deepEqual(parseInteger(" 1 200 "), { ok: true, value: 1200 })
    assert.equal(parseInteger("1,5").ok, false)
    assert.equal(parseInteger("").ok, false)
    assert.deepEqual(parseNumber("0,25"), { ok: true, value: 0.25 })
    assert.deepEqual(parseNumber("3"), { ok: true, value: 3 })
    assert.equal(parseNumber("x").ok, false)
  })
  it("giltiga datum och klockslag", () => {
    assert.equal(isValidDate("2027-02-28"), true)
    assert.equal(isValidDate("2027-02-30"), false)
    assert.equal(isValidDate("2027-2-3"), false)
    assert.equal(isValidTime("08:00"), true)
    assert.equal(isValidTime("24:00"), false)
    assert.equal(isValidTime("8:00"), false)
  })
})

describe("parseDraft per värdetyp", () => {
  const parse = (id: string, draft: unknown) => parseDraft(byId(id), draft)

  it("heltal med enhet och belopp i kronor ger öre", () => {
    assert.deepEqual(parse("window.later_days", "3"), { ok: true, value: 3 })
    assert.equal(parse("window.later_days", "3,5").ok, false)
    assert.deepEqual(parse("cost.staff_session_ore", "1300"), { ok: true, value: 130000 })
    assert.deepEqual(parse("cost.staff_session_ore", "1300,25"), { ok: true, value: 130025 })
    assert.equal(parse("cost.staff_session_ore", "1300,255").ok, false)
    assert.deepEqual(parse("cost.annualization_factor", "1,25"), { ok: true, value: 1.25 })
  })

  it("boolean och val", () => {
    assert.deepEqual(parse("rooms.allow_split", false), { ok: true, value: false })
    assert.deepEqual(parse("demand.rounding", "nearest"), { ok: true, value: "nearest" })
    assert.equal(parse("demand.rounding", "okänd").ok, false)
  })

  it("datum får vara tomma när standardvärdet är tomt, tid inte", () => {
    assert.deepEqual(parse("calendar.start_date", ""), { ok: true, value: "" })
    assert.deepEqual(parse("calendar.start_date", "2027-01-11"), { ok: true, value: "2027-01-11" })
    assert.equal(parse("calendar.start_date", "11/1").ok, false)
    assert.equal(parse("calendar.earliest_start_time", "").ok, false)
    assert.deepEqual(parse("calendar.earliest_start_time", "07:30"), { ok: true, value: "07:30" })
  })

  it("listor: sorteras, dubbletter och tomma listor avvisas", () => {
    assert.deepEqual(parse("calendar.start_times", ["14:00", "08:00"]), { ok: true, value: ["08:00", "14:00"] })
    assert.equal(parse("calendar.start_times", ["08:00", "08:00"]).ok, false)
    assert.equal(parse("calendar.start_times", ["8"]).ok, false)
    assert.equal(parse("calendar.start_times", []).ok, false)
    assert.deepEqual(parse("calendar.weekdays", ["5", "1", "3"]), { ok: true, value: [1, 3, 5] })
    assert.equal(parse("calendar.weekdays", []).ok, false)
    assert.equal(parse("calendar.weekdays", ["8"]).ok, false)
    assert.equal(parse("calendar.weekdays", ["x"]).ok, false)
  })

  it("veckodagar känns igen på id och intervall gäller bara dem", () => {
    assert.equal(isWeekdayParam(byId("calendar.weekdays")), true)
    assert.equal(isWeekdayParam(byId("solver.seed")), false)
  })

  it("perioder: start före slut och giltiga värden", () => {
    assert.deepEqual(parse("calendar.blocked_ranges", [{ start: "2027-03-01", end: "2027-03-05" }]), { ok: true, value: [{ start: "2027-03-01", end: "2027-03-05" }] })
    const reversed = parse("calendar.blocked_ranges", [{ start: "2027-03-06", end: "2027-03-05" }])
    assert.equal(reversed.ok, false)
    assert.match((reversed as { error: string }).error, /Rad 1: slutet ligger före början/)
    assert.equal(parse("calendar.blocked_ranges", [{ start: "2027-03-0", end: "2027-03-05" }]).ok, false)
    assert.equal(parse("staffing.shifts", [{ start: "07:30", end: "19:30" }]).ok, true)
    assert.equal(parse("staffing.shifts", [{ start: "20:00", end: "19:30" }]).ok, false)
  })

  it("typer utan redigerare tolkas inte", () => {
    assert.equal(hasEditor("matrix"), false)
    assert.equal(parse("digital.compatibility_matrix", "x").ok, false)
  })
})

describe("bemanningstrappan", () => {
  const rows = (...pairs: [string, string][]) => pairs.map(([max, staff]) => ({ max, staff }))

  it("godtar stigande trösklar", () => {
    assert.deepEqual(validateLadder(rows(["50", "1"], ["150", "2"], ["300", "3"])), { rowErrors: [null, null, null], error: null })
  })
  it("avvisar tröskel som inte stiger, med radnummer", () => {
    const check = validateLadder(rows(["50", "1"], ["50", "2"], ["40", "3"]))
    assert.equal(check.rowErrors[0], null)
    assert.match(check.rowErrors[1]!, /högre än föregående rad \(50\)/)
    assert.match(check.rowErrors[2]!, /högre än föregående rad \(50\)/)
    assert.match(check.error!, /^Rad 2:/)
  })
  it("avvisar tom trappa, noll och decimaler", () => {
    assert.match(validateLadder([]).error!, /minst en rad/)
    assert.match(validateLadder(rows(["0", "1"])).rowErrors[0]!, /minst 1/)
    assert.match(validateLadder(rows(["50", "1,5"])).rowErrors[0]!, /vakter/)
    assert.match(validateLadder(rows(["abc", "1"])).rowErrors[0]!, /deltagare/)
  })
  it("ger värdet i API:ets form och roundtrip från utkast", () => {
    const param = byId("staffing.ladder")
    const draft = toDraft(param)
    assert.deepEqual(draft, rows(["50", "1"], ["150", "2"], ["300", "3"]))
    assert.deepEqual(parseDraft(param, draft), { ok: true, value: param.value })
    const edited = rows(["60", "1"], ["150", "2"], ["300", "3"])
    assert.deepEqual(parseDraft(param, edited), {
      ok: true, value: [{ max_participants: 60, required_staff: 1 }, { max_participants: 150, required_staff: 2 }, { max_participants: 300, required_staff: 3 }],
    })
  })
})

describe("utkast och utgångsvärden", () => {
  it("utgångsvärdet tolkas som ett utkast: omordning är ingen ändring", () => {
    const times = { ...byId("calendar.start_times"), value: ["14:00", "08:00"] }
    assert.deepEqual(baselineValue(times), ["08:00", "14:00"])
  })
  it("alla redigerbara testparametrar går att göra till utkast och tillbaka", () => {
    for (const param of PARAMETERS.filter(item => hasEditor(item.value_type))) {
      const parsed = parseDraft(param, toDraft(param))
      assert.equal(parsed.ok, true, param.id)
      assert.equal(sameValue((parsed as { value: unknown }).value, baselineValue(param)), true, param.id)
    }
  })
  it("sameValue ignorerar nyckelordning", () => {
    assert.equal(sameValue({ a: 1, b: [1, 2] }, { b: [1, 2], a: 1 }), true)
    assert.equal(sameValue([1, 2], [2, 1]), false)
  })
})

describe("visning av värden", () => {
  it("klartext per typ", () => {
    assert.equal(formatParamValue(byId("rooms.allow_split"), true), "Ja")
    assert.equal(formatParamValue(byId("demand.rounding"), "up"), "Uppåt")
    assert.equal(formatParamValue(byId("calendar.weekdays"), [1, 2, 3, 4, 5, 6, 7]), "Alla veckodagar")
    assert.equal(formatParamValue(byId("calendar.weekdays"), [1, 3, 5]), "mån, ons, fre")
    assert.equal(formatParamValue(byId("calendar.start_times"), ["08:00", "14:00"]), "08:00, 14:00")
    assert.equal(formatParamValue(byId("calendar.start_date"), ""), "(tomt)")
    assert.match(formatParamValue(byId("cost.staff_session_ore"), 125000), /^1\s250\skr per tillfälle$/)
    assert.equal(formatParamValue(byId("staffing.ladder"), byId("staffing.ladder").value), "upp till 50 deltagare: 1 vakt; upp till 150 deltagare: 2 vakter; upp till 300 deltagare: 3 vakter")
    assert.equal(formatParamValue(byId("calendar.blocked_ranges"), []), "(inga perioder)")
  })
})
