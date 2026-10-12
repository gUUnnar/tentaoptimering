import assert from "node:assert/strict"
import { describe, it } from "node:test"
import { RunClock } from "./runClock.ts"

const T0 = 1_000_000 // lokal klocka i ms

describe("körningens klocka", () => {
  it("räknar vidare lokalt mellan serverns svar", () => {
    const clock = new RunClock()
    clock.reset(T0)
    clock.observe(10, T0)
    assert.equal(clock.read(T0), 10)
    assert.equal(clock.read(T0 + 2500), 12.5)
  })

  it("tiden står inte still när lösaren är tyst i 90 sekunder", () => {
    // Inga händelser, men servern rapporterar fortfarande körningens tid varje sekund.
    const clock = new RunClock()
    clock.reset(T0)
    let previous = 0
    for (let second = 1; second <= 90; second++) {
      clock.observe(second, T0 + second * 1000)
      const shown = clock.read(T0 + second * 1000 + 500)
      assert.ok(shown > previous, `sekund ${second}: ${shown} ska vara större än ${previous}`)
      previous = shown
    }
    assert.ok(previous >= 90)
  })

  it("tiden går vidare även utan svar (polling-fördröjning)", () => {
    const clock = new RunClock()
    clock.reset(T0)
    clock.observe(20, T0)
    // Inga svar på 8 sekunder: den lokala klockan fortsätter.
    assert.equal(clock.read(T0 + 8000), 28)
    // Svaret kommer och är lite före den lokala gissningen: visningen hoppar framåt.
    clock.observe(29.5, T0 + 8000)
    assert.equal(clock.read(T0 + 8000), 29.5)
  })

  it("går aldrig bakåt när serverns värde hoppar bakåt", () => {
    const clock = new RunClock()
    clock.reset(T0)
    clock.observe(30, T0)
    assert.equal(clock.read(T0 + 3000), 33)
    // Servern säger 31 efter 3 s: den lokala gissningen låg före. Visningen står still, backar inte.
    clock.observe(31, T0 + 3000)
    assert.equal(clock.read(T0 + 3000), 33)
    assert.equal(clock.read(T0 + 4000), 33) // 31 + 1 s
    assert.equal(clock.read(T0 + 5000), 33) // 31 + 2 s
    assert.equal(clock.read(T0 + 6000), 34) // förbi det som visats
  })

  it("visningen är monoton för en blandad följd av avläsningar och svar", () => {
    const clock = new RunClock()
    clock.reset(T0)
    const server = [0, 1, 1, 2, 9, 5, 6, 6.5, 20, 12, 13]
    let now = T0
    let previous = -1
    for (const value of server) {
      now += 700
      clock.observe(value, now)
      for (const offset of [0, 200, 400]) {
        const shown = clock.read(now + offset)
        assert.ok(shown >= previous, `${shown} ska inte vara mindre än ${previous}`)
        previous = shown
      }
    }
  })

  it("efter avslut visas serverns slutvärde och senare svar ändrar det inte", () => {
    const clock = new RunClock()
    clock.reset(T0)
    clock.observe(40, T0)
    clock.read(T0 + 3000)
    clock.finish(41.2)
    assert.equal(clock.read(T0 + 99_000), 41.2)
    clock.observe(500, T0 + 100_000)
    assert.equal(clock.read(T0 + 100_000), 41.2)
  })

  it("ogiltiga värden från servern ignoreras och ny körning börjar om från noll", () => {
    const clock = new RunClock()
    clock.reset(T0)
    clock.observe(5, T0)
    clock.observe(null, T0 + 1000)
    clock.observe(Number.NaN, T0 + 1000)
    clock.observe(-3, T0 + 1000)
    assert.equal(clock.read(T0 + 1000), 6)
    clock.finish(null) // äldre server utan slutvärde: det som visats behålls
    assert.equal(clock.read(T0 + 9000), 6)
    clock.reset(T0 + 20_000)
    assert.equal(clock.read(T0 + 20_000), 0)
  })
})
