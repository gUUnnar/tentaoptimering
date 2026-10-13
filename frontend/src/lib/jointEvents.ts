import type { EventsResponse, JointEvent, JointJobStatus } from "./jointTypes.ts"

const obj = (value: unknown): Record<string, unknown> => value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {}

/**
 * Gör om ett felvärde till text. Servern skickar text ("OSError: disk full"), men i ett defensivt läge kan det vara
 * ett objekt {type, message}. React får aldrig försöka rendera ett objekt.
 */
export function errorText(value: unknown): string | null {
  if (value === null || value === undefined || value === "") return null
  if (typeof value === "string") return value
  if (typeof value === "object") {
    const { type, message } = obj(value)
    const kind = typeof type === "string" && type ? type : ""
    const text = typeof message === "string" && message ? message : ""
    if (kind && text) return `${kind}: ${text}`
    if (kind || text) return kind || text
    return "Okänt fel."
  }
  return String(value)
}

const STATUSES: ReadonlySet<string> = new Set(["running", "completed", "failed", "cancelled"])

/** Normaliserar händelser från servern: felfältet i `finished` blir text. Övrigt lämnas orört. */
export function normalizeEvents(raw: unknown): JointEvent[] {
  if (!Array.isArray(raw)) return []
  return raw.filter(item => item && typeof item === "object").map(item => {
    const event = item as JointEvent
    return event.type === "finished" && "error" in event ? { ...event, error: errorText((event as { error?: unknown }).error) } : event
  })
}

/** Läser svaret från /events defensivt. En okänd status tolkas som att körningen pågår, inte som klar. */
export function toEventsResponse(raw: unknown): EventsResponse {
  const body = obj(raw)
  const status = typeof body.status === "string" && STATUSES.has(body.status) ? body.status as JointJobStatus : "running"
  const elapsed = body.elapsed_seconds
  return {
    status,
    events: normalizeEvents(body.events),
    last_seq: typeof body.last_seq === "number" ? body.last_seq : 0,
    run_id: typeof body.run_id === "string" ? body.run_id : null,
    error: errorText(body.error),
    elapsed_seconds: typeof elapsed === "number" && Number.isFinite(elapsed) && elapsed >= 0 ? elapsed : null,
  }
}
