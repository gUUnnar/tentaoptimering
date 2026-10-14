import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { describe, it } from "node:test"
import { toJointOptions, toJointSummary, type BackendSummary } from "./jointApi.ts"
import { assumptionView, assumptionsChanged, interpretationView, metricRows, NOT_COMPARED_TEXT, toCompareResult } from "./jointCompare.ts"
import { errorText, toEventsResponse } from "./jointEvents.ts"
import { formatKr } from "./jointFormat.ts"
import { changedParameters, changedParametersHeading, summaryView } from "./jointSummaryView.ts"
import type { JointSummary } from "./jointTypes.ts"

// Riktiga svar från backend (ögonblicksbilder i testing/contract) matas genom klientens adaptrar. Varje fält i
// svaret måste vara hanterat: ett nytt eller omdöpt fält i en ögonblicksbild får testet att säga ifrån, så att
// kontraktsglapp fångas här och inte i webbläsaren.

type Raw = Record<string, any>
const load = (name: string): Raw => JSON.parse(readFileSync(new URL(`./testing/contract/${name}.json`, import.meta.url), "utf8"))
const ids = (summary: JointSummary) => summary.parameters_changed_from_default.map(item => item.id)

/** Fält i backendens sammanfattning -> (vad klienten läser, vad det ska vara). */
const SUMMARY_FIELDS: Record<string, [(out: JointSummary) => unknown, (raw: Raw) => unknown] | "ignored"> = {
  cancelled: [out => out.cancelled, raw => raw.cancelled],
  changed_exams: [out => out.changed_exams, raw => raw.changed_exams],
  cost_is_proven_optimum: [out => out.proven_optimum, raw => raw.cost_is_proven_optimum],
  cost_ore: [out => out.cost_ore, raw => raw.cost_ore],
  created_at: [out => out.created_at, raw => raw.created_at],
  exams_total: [out => out.exams_total, raw => raw.exams_total],
  first_solution_basis: [out => out.first_solution_basis, raw => raw.first_solution_basis],
  first_solution_seconds: [out => out.first_solution_seconds, raw => raw.first_solution_seconds],
  first_solution_source: [out => out.first_solution_source, raw => raw.first_solution_source],
  gap_ore: [out => out.gap_ore, raw => raw.gap_ore],
  gap_relative: [out => out.gap, raw => raw.gap_relative],
  has_verified_solution: [out => out.has_verified_solution, raw => raw.has_verified_solution],
  lower_bound_ore: [out => out.bound_ore, raw => raw.lower_bound_ore],
  parameters_changed_count: [out => out.parameters_changed_count, raw => raw.parameters_changed_count],
  parameters_changed_from_default: [out => ids(out), raw => raw.parameters_changed_from_default],
  problem_id: [out => out.problem_id, raw => raw.problem_id],
  period: [out => out.period, raw => raw.period],
  planning_basis: [out => out.planning_basis, raw => raw.planning_basis],
  run_id: [out => out.run_id, raw => raw.run_id],
  scenario_id: [out => out.scenario_id, raw => raw.scenario_id],
  solver_outcome: [out => out.outcome, raw => raw.solver_outcome],
  staff_pool_size: [out => out.staff_pool_size, raw => raw.staff_pool_size],
  unverified_reason: [out => out.unverified_reason, raw => raw.unverified_reason],
  verdicts: [out => [out.technical_validation, out.business_verification, out.provenance],
    raw => [raw.verdicts.technical_validation, raw.verdicts.business_verification, raw.verdicts.provenance]],
  wall_time_seconds: [out => out.wall_seconds, raw => raw.wall_time_seconds],
  warm_start_decision: [out => out.warm_start_decision, raw => raw.warm_start_decision],
  // Visas inte: den tekniska domen (verdicts.technical_validation) är det som redovisas.
  technical_placement_complete: "ignored",
}

describe("sammanfattning: riktiga svar genom adaptern", () => {
  for (const name of ["summary_verified", "summary_unverified"]) {
    it(`${name}: inget fält tappas`, () => {
      const raw = load(name)
      const out = toJointSummary(raw as BackendSummary)
      for (const key of Object.keys(raw)) {
        const rule = SUMMARY_FIELDS[key]
        assert.ok(rule, `Fältet "${key}" i svaret från backend hanteras inte av klienten`)
        if (rule === "ignored") continue
        assert.deepEqual(rule[0](out), rule[1](raw), `fältet ${key}`)
      }
    })
  }

  it("parametrar som avviker från standard blir en lista med id och ett antal", () => {
    const out = toJointSummary(load("summary_verified") as BackendSummary)
    assert.deepEqual(ids(out), ["cost.room_annual_per_seat_ore", "cost.staff_annual_ore", "solver.time_limit_seconds", "solver.workers", "staffing.ladder", "window.later_days"])
    assert.equal(out.parameters_changed_count, 6)
    assert.equal(changedParametersHeading(out), "6 parametrar avviker från standardvärdet i den här körningen:")
  })

  it("etiketten slås upp i parameterlistan, annars visas id", () => {
    const out = toJointSummary(load("summary_verified") as BackendSummary)
    const shown = changedParameters(out, { "cost.staff_annual_ore": "Årskostnad per vaktresurs" })
    assert.deepEqual(shown.find(item => item.id === "cost.staff_annual_ore"), { id: "cost.staff_annual_ore", label: "Årskostnad per vaktresurs" })
    assert.deepEqual(shown.find(item => item.id === "window.later_days"), { id: "window.later_days", label: null })
  })

  it("verifierad körning visar kostnad, gränser och mått", () => {
    const view = summaryView(toJointSummary(load("summary_verified") as BackendSummary))
    assert.equal(view.verified, true)
    if (!view.verified) return
    assert.equal(view.statement.proven, true)
    assert.equal(view.statement.headline, formatKr(9000))
    // Bevisat lägsta: rubriken räcker, verifierad kostnad, undre gräns och gap visas inte en gång till.
    for (const label of ["Verifierad kostnad", "Undre gräns", "Gap"]) assert.equal(view.stats.some(item => item.label === label), false)
    assert.equal(view.stats.find(item => item.label === "Vaktpool")?.value, "1")
  })

  it("kostnad som inte är bevisat lägsta visar verifierad kostnad, undre gräns och gap", () => {
    const view = summaryView(toJointSummary({ ...load("summary_verified"), cost_is_proven_optimum: false, solver_outcome: "feasible_not_proven", lower_bound_ore: 8000, gap_relative: 0.1, gap_ore: 1000 } as BackendSummary))
    assert.equal(view.verified, true)
    if (!view.verified) return
    assert.equal(view.statement.proven, false)
    assert.equal(view.stats.find(item => item.label === "Verifierad kostnad")?.value, formatKr(9000))
    assert.equal(view.stats.some(item => item.label === "Undre gräns"), true)
  })

  it("körning utan verifierad lösning visar bara skälet, aldrig en kostnad eller ett intervall", () => {
    const raw = load("summary_unverified")
    const out = toJointSummary(raw as BackendSummary)
    assert.equal(out.cost_ore, null)
    assert.equal(out.bound_ore, null)
    assert.equal(out.gap, null)
    assert.equal(out.changed_exams, null)
    assert.equal(out.staff_pool_size, null)
    assert.equal(out.unverified_reason, raw.unverified_reason)
    const view = summaryView(out)
    assert.equal(view.verified, false)
    assert.equal(view.reason, raw.unverified_reason)
    assert.equal(view.statement, null)
    assert.equal(view.outcomeText, null)
    assert.ok(view.stats.every(stat => !/kr|%|Kostnad|gräns|Gap|Vaktpool|Flyttade/i.test(`${stat.label} ${stat.value}`)), JSON.stringify(view.stats))
  })

  it("även om servern skulle skicka kostnadsmått utan verifierad lösning visas de inte", () => {
    const out = toJointSummary({ ...load("summary_unverified"), cost_ore: 9000, lower_bound_ore: 8000, gap_ore: 1000, gap_relative: 0.1, changed_exams: 3, staff_pool_size: 4 } as BackendSummary)
    assert.deepEqual([out.cost_ore, out.bound_ore, out.gap_ore, out.gap, out.changed_exams, out.staff_pool_size, out.proven_optimum], [null, null, null, null, null, null, false])
  })

  it("en körning utan skäl från servern får ändå ett besked", () => {
    const view = summaryView(toJointSummary({ ...load("summary_unverified"), unverified_reason: null } as BackendSummary))
    assert.equal(view.verified, false)
    assert.ok(view.reason.length > 10)
  })
})

// ---- Händelser -----------------------------------------------------------------------------------------------------

const EVENT_FIELDS: Record<string, string[]> = {
  phase: ["name", "state"], batch: ["kind", "total", "done", "parallel", "workers_per_check", "statuses"], day_started: ["date", "kind", "block"],
  day: ["date", "kind", "status", "seconds", "block"], incumbent: ["cost_ore", "source", "changed_exams"], bound: ["lower_ore", "round"],
  warm_start: ["decision", "explanation", "source_run_id"], resources: ["threads", "memory_mb", "parallel_checks", "workers_per_check"],
  finished: ["outcome", "cost_ore", "bound_ore", "cancelled", "error"],
}

describe("händelser: riktiga svar genom adaptern", () => {
  for (const name of ["events_completed", "events_failed"]) {
    it(`${name}: alla fält hanteras och inga händelser ändras`, () => {
      const raw = load(name)
      for (const key of Object.keys(raw)) assert.ok(["elapsed_seconds", "error", "events", "last_seq", "run_id", "status"].includes(key), `Fältet "${key}" hanteras inte`)
      for (const event of raw.events) {
        assert.ok(event.type in EVENT_FIELDS, `Okänd händelsetyp ${event.type}`)
        for (const key of Object.keys(event)) assert.ok(["seq", "t", "type", ...EVENT_FIELDS[event.type]].includes(key), `Händelsen ${event.type} har fältet "${key}" som klienten inte känner till`)
      }
      const out = toEventsResponse(raw)
      assert.equal(out.status, raw.status)
      assert.equal(out.last_seq, raw.last_seq)
      assert.equal(out.run_id, raw.run_id)
      assert.equal(out.elapsed_seconds, raw.elapsed_seconds)
      assert.deepEqual(out.events, raw.events)
    })
  }

  it("körningens verkliga tid följer med", () => {
    for (const name of ["events_completed", "events_failed"]) {
      const raw = load(name)
      assert.equal(typeof raw.elapsed_seconds, "number")
      assert.equal(toEventsResponse(raw).elapsed_seconds, raw.elapsed_seconds)
    }
    assert.equal(toEventsResponse({ status: "running", events: [], last_seq: 0 }).elapsed_seconds, null)
  })

  it("felet är text, både som text och som objekt", () => {
    const failed = load("events_failed")
    assert.equal(toEventsResponse(failed).error, "OSError: disk full")
    assert.equal(toEventsResponse(load("events_completed")).error, null)
    const objectError = toEventsResponse({ ...failed, error: { type: "OSError", message: "disk full" } })
    assert.equal(objectError.error, "OSError: disk full")
    assert.equal(typeof objectError.error, "string")
    const finished = toEventsResponse({ ...failed, events: [{ ...failed.events.at(-1), error: { type: "ValueError", message: "fel" } }] }).events[0]
    assert.equal(finished.type === "finished" ? finished.error : null, "ValueError: fel")
  })

  it("felvärden av olika form blir alltid text eller null", () => {
    assert.equal(errorText(null), null)
    assert.equal(errorText(undefined), null)
    assert.equal(errorText(""), null)
    assert.equal(errorText("fel"), "fel")
    assert.equal(errorText({ message: "bara text" }), "bara text")
    assert.equal(errorText({ type: "KeyError" }), "KeyError")
    assert.equal(errorText({}), "Okänt fel.")
    assert.equal(errorText(42), "42")
  })

  it("okänd status tolkas som pågående, inte som klar", () => {
    assert.equal(toEventsResponse({ status: "mystery", events: [], last_seq: 0 }).status, "running")
  })
})

// ---- Jämförelse ----------------------------------------------------------------------------------------------------

const COMPARE_FIELDS = ["assumption_changes", "base", "comparable", "interpretable", "interpretation", "metrics", "parameter_changes", "reason", "run", "uncertainty_ore"]
const METRICS = ["changed_exams", "cost_ore", "first_solution_seconds", "gap_ore", "lower_bound_ore", "rooms_used", "staff_pool_size", "wall_time_seconds"]

describe("jämförelse: riktiga svar genom adaptern", () => {
  for (const name of ["compare_assumption_changed", "compare_no_previous", "compare_unverified_base"]) {
    it(`${name}: inget fält tappas`, () => {
      const raw = load(name)
      for (const key of Object.keys(raw)) assert.ok(COMPARE_FIELDS.includes(key), `Fältet "${key}" hanteras inte`)
      const out = toCompareResult(raw)
      assert.equal(out.comparable, raw.comparable)
      assert.equal(out.interpretable, raw.interpretable)
      assert.equal(out.interpretation, raw.interpretation)
      assert.equal(out.reason, raw.reason)
      assert.equal(out.uncertainty_ore, raw.uncertainty_ore)
      assert.deepEqual(out.assumption_changes, raw.assumption_changes)
      assert.equal(out.run.run_id, raw.run.run_id)
      assert.equal(out.run.has_verified_solution, raw.run.has_verified_solution)
      assert.equal(out.base?.run_id ?? null, raw.base?.run_id ?? null)
      assert.equal(out.base?.has_verified_solution ?? null, raw.base?.has_verified_solution ?? null)
      assert.deepEqual(out.parameter_changes, raw.parameter_changes)
      assert.deepEqual(Object.keys(out.metrics).sort(), Object.keys(raw.metrics).sort())
      for (const [key, metric] of Object.entries<any>(raw.metrics)) {
        assert.ok(METRICS.includes(key), `Måttet "${key}" hanteras inte`)
        assert.deepEqual((out.metrics as any)[key], { old: metric.old, new: metric.new, delta: metric.delta }, key)
      }
    })
  }

  it("ändrade antaganden: rutan, tolkningen och måtttabellen", () => {
    const result = toCompareResult(load("compare_assumption_changed"))
    assert.equal(assumptionsChanged(result), true)
    assert.equal(result.interpretable, false)
    const box = assumptionView(result)
    assert.ok(box)
    assert.equal(box.title, "Antaganden har ändrats")
    assert.deepEqual(box.groups.map(group => group.items), [["Årskostnad per vaktresurs"]])
    const view = interpretationView(result)
    assert.equal(view.tone, "not_interpretable")
    assert.match(view.text, /^Kostnads- och bemanningsantagandena har ändrats/)
    assert.match(view.text, /Ingen kostnadsskillnad redovisas/)

    const rows = metricRows(result)
    const byKey = Object.fromEntries(rows.map(row => [row.key, row]))
    for (const key of ["cost_ore", "lower_bound_ore", "gap_ore"]) {
      assert.equal(byKey[key].notCompared, true, key)
      assert.equal(byKey[key].delta, NOT_COMPARED_TEXT, key)
      assert.equal(byKey[key].direction, "unknown")
    }
    assert.equal(byKey.cost_ore.old, formatKr(7000))
    assert.equal(byKey.cost_ore.new, formatKr(9000))
    for (const key of ["rooms_used", "staff_pool_size", "changed_exams"]) {
      assert.equal(byKey[key].physical, true, key)
      assert.equal(byKey[key].notCompared, false, key)
      assert.equal(byKey[key].delta, "Oförändrat", key)
    }
    assert.deepEqual(rows.slice(0, 3).map(row => row.physical), [true, true, true], "fysiska mått står först")
    assert.equal(byKey.wall_time_seconds.physical, false)
  })

  it("ändrade antaganden: ingen kostnadsskillnad räknas fram, inte ens när servern skickar en", () => {
    const raw = load("compare_assumption_changed")
    raw.metrics.cost_ore.delta = 2000
    raw.metrics.lower_bound_ore.delta = null
    const rows = metricRows(toCompareResult(raw))
    assert.equal(rows.find(row => row.key === "cost_ore")?.delta, NOT_COMPARED_TEXT)
    assert.equal(rows.find(row => row.key === "lower_bound_ore")?.delta, NOT_COMPARED_TEXT)
  })

  it("ändrad efterfrågan räknas också som ändrade antaganden", () => {
    const raw = load("compare_assumption_changed")
    raw.assumption_changes = { cost: [], demand: ["Antal tentander"] }
    const box = assumptionView(toCompareResult(raw))
    assert.deepEqual(box?.groups.map(group => group.items), [["Antal tentander"]])
  })

  it("utan ändrade antaganden finns ingen ruta och kostnadsskillnaden visas", () => {
    const raw = load("compare_assumption_changed")
    raw.assumption_changes = { cost: [], demand: [] }
    raw.metrics.cost_ore.delta = 2000
    const result = toCompareResult(raw)
    assert.equal(assumptionView(result), null)
    assert.notEqual(metricRows(result).find(row => row.key === "cost_ore")?.delta, NOT_COMPARED_TEXT)
  })

  it("jämförelse mot körning utan verifierad lösning visas utan fel och utan kostnadsskillnad", () => {
    const result = toCompareResult(load("compare_unverified_base"))
    assert.equal(result.comparable, false)
    assert.equal(result.base?.has_verified_solution, false)
    assert.equal(interpretationView(result).title, "Körningarna går inte att jämföra")
    assert.equal(interpretationView(result).text, load("compare_unverified_base").interpretation)
    const rows = metricRows(result)
    assert.equal(rows.length, 8)
    const cost = rows.find(row => row.key === "cost_ore")!
    assert.equal(cost.old, "–")
    assert.equal(cost.delta, "–", "körningarna är inte jämförbara alls, så ingen skillnad och ingen påstådd orsak på raden")
    assert.ok(rows.every(row => !row.physical), "inget fysiskt mått framhävs som jämförbart när jämförelsen saknas")
    assert.ok(rows.filter(row => !row.notCompared).every(row => row.delta === "–" || /^[+−]|Oförändrat/.test(row.delta)))
    assert.ok(assumptionView(result), "antagandena har ändrats även här")
  })

  it("en körning utan verifierad lösning visar inga lösningsmått i tabellen", () => {
    const raw = load("compare_assumption_changed")
    raw.run.has_verified_solution = false
    const rows = metricRows(toCompareResult(raw))
    assert.equal(rows.find(row => row.key === "cost_ore")?.new, "–")
    assert.equal(rows.find(row => row.key === "staff_pool_size")?.new, "–")
    assert.notEqual(rows.find(row => row.key === "wall_time_seconds")?.new, "–")
  })

  it("ingen tidigare körning", () => {
    const result = toCompareResult(load("compare_no_previous"))
    assert.equal(result.base, null)
    assert.equal(result.reason, "Ingen tidigare körning av samma scenario")
    assert.equal(result.interpretable, null)
    assert.deepEqual(result.metrics, {})
    assert.deepEqual(metricRows(result), [])
    assert.equal(assumptionView(result), null)
  })
})

// ---- Alternativ ur underlaget (salar och tentamenstyper) -------------------------------------------------------------

describe("alternativ: riktigt svar genom adaptern", () => {
  const raw = load("options")
  it("alla fält hanteras och inget tappas", () => {
    for (const key of Object.keys(raw)) assert.ok(["data_available", "exam_types", "plan_area", "rooms", "scenario_id"].includes(key), `Fältet "${key}" hanteras inte av klienten`)
    for (const room of raw.rooms) for (const key of Object.keys(room)) assert.ok(["address", "building_id", "capacity", "digital", "label", "room_id"].includes(key), `Salsfältet "${key}" hanteras inte`)
    for (const type of raw.exam_types) for (const key of Object.keys(type)) assert.ok(["count", "label", "value"].includes(key), `Typfältet "${key}" hanteras inte`)
    const out = toJointOptions(raw)
    assert.equal(out.data_available, raw.data_available)
    assert.equal(out.scenario_id, raw.scenario_id)
    assert.equal(out.plan_area, raw.plan_area)
    assert.deepEqual(out.rooms, raw.rooms)
    assert.deepEqual(out.exam_types, raw.exam_types)
  })
  it("typens värde är gemener och digitalstödet ett av de kända", () => {
    for (const type of toJointOptions(raw).exam_types) assert.equal(type.value, type.value.toLowerCase())
    for (const room of toJointOptions(raw).rooms) assert.ok(["all", "partial", "none", "unknown"].includes(room.digital))
  })
  it("saknat underlag ger tomma listor", () => {
    const out = toJointOptions({ ...raw, data_available: false, rooms: [], exam_types: [], plan_area: null })
    assert.deepEqual([out.data_available, out.rooms, out.exam_types], [false, [], []])
  })
})
