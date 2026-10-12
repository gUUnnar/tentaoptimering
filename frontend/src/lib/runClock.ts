// Körningens klocka. Servern skickar körningens verkliga tid (`elapsed_seconds`) i varje svar; mellan svaren
// räknar en lokal klocka vidare. Visningen går aldrig bakåt: den är det största av vad som redan visats och
// serverns senaste värde plus tiden som gått lokalt sedan svaret.

export class RunClock {
  private serverSeconds = 0
  private receivedAtMs = 0
  private shown = 0
  private final: number | null = null

  /** Ny körning: klockan börjar om från noll. */
  reset(nowMs: number): void {
    this.serverSeconds = 0
    this.receivedAtMs = nowMs
    this.shown = 0
    this.final = null
  }

  /** Ett svar från servern med körningens tid just nu. Ogiltiga värden ignoreras. */
  observe(serverSeconds: number | null | undefined, nowMs: number): void {
    if (this.final !== null || typeof serverSeconds !== "number" || !Number.isFinite(serverSeconds) || serverSeconds < 0) return
    this.serverSeconds = serverSeconds
    this.receivedAtMs = nowMs
  }

  /** Körningen är slut: serverns slutvärde visas från och med nu. */
  finish(serverSeconds: number | null | undefined): void {
    if (typeof serverSeconds === "number" && Number.isFinite(serverSeconds) && serverSeconds >= 0) this.final = serverSeconds
    else this.final = this.shown
    this.shown = this.final
  }

  /** Tiden som ska visas just nu, i sekunder. */
  read(nowMs: number): number {
    if (this.final !== null) return this.final
    const estimate = this.serverSeconds + Math.max(0, nowMs - this.receivedAtMs) / 1000
    this.shown = Math.max(this.shown, estimate)
    return this.shown
  }
}
