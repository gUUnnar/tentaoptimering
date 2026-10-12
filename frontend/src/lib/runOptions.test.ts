import assert from "node:assert/strict"
import { describe, it } from "node:test"
import { DEFAULT_RUN_OPTIONS, checkRunOptions, runOptionsValid, toStartBody } from "./runOptions.ts"

describe("körval", () => {
  it("standardvalen är giltiga och ger automatisk start utan parametrar", () => {
    assert.equal(runOptionsValid(DEFAULT_RUN_OPTIONS), true)
    assert.deepEqual(toStartBody("joint_real_subset", DEFAULT_RUN_OPTIONS, {}), {
      scenario: "joint_real_subset", warm_start: "auto", threads: 0, memory_mb: null, parallel_day_checks: true,
    })
  })
  it("ändrade parametrar skickas med, specifik körning skickas som id", () => {
    const body = toStartBody("s", { ...DEFAULT_RUN_OPTIONS, mode: "specific", specific: "run-7", threads: "4", memory: "2048", parallel: false }, { "window.later_days": 2 })
    assert.deepEqual(body, { scenario: "s", warm_start: "run-7", threads: 4, memory_mb: 2048, parallel_day_checks: false, parameters: { "window.later_days": 2 } })
  })
  it("ogiltiga val ger fel per fält", () => {
    const check = checkRunOptions({ ...DEFAULT_RUN_OPTIONS, mode: "specific", specific: "", threads: "-1", memory: "0" })
    assert.ok(check.threads && check.memory && check.warm)
    assert.equal(checkRunOptions({ ...DEFAULT_RUN_OPTIONS, threads: "" }).threads !== null, true)
    assert.equal(checkRunOptions({ ...DEFAULT_RUN_OPTIONS, memory: "1,5" }).memory !== null, true)
  })
})
