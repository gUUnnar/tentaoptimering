// Enheter och belopp. API:et och vyn räknar i kronor; ingen omräkning sker.

export type UnitInfo = { money: boolean; label: string }

const RAW_UNITS: Record<string, string> = {
  percent: "%", procent: "%", days: "dagar", dagar: "dagar", minutes: "minuter", minuter: "minuter", seconds: "sekunder", sekunder: "sekunder",
  hours: "timmar", timmar: "timmar", factor: "gånger", faktor: "gånger", fraction: "andel (0–1)", andel: "andel (0–1)",
}

const PER_TEXT: Record<string, string> = {
  year: "år", år: "år", session: "tillfälle", tillfälle: "tillfälle", pass: "pass", hour: "timme", timme: "timme", exam: "tentamen", tentamen: "tentamen",
  seat: "plats", plats: "plats", day: "dag", dag: "dag", minute: "minut", minut: "minut",
}

// "kr", "kr_per_year", "kr/timme", "kr per år" ...
const MONEY = /^kr(?:[\s_/]+(?:per[\s_]+)?(.+))?$/i

/** Tolkar enhetstexten från API:et. Belopp i kronor (enhet kr); okända enheter visas som de är. */
export function unitInfo(unit: string | null | undefined): UnitInfo {
  const text = (unit ?? "").trim()
  if (!text) return { money: false, label: "" }
  const money = MONEY.exec(text)
  if (money) {
    const rest = money[1]?.trim().toLowerCase()
    return { money: true, label: rest ? `kr per ${PER_TEXT[rest] ?? rest.replace(/_/g, " ")}` : "kr" }
  }
  return { money: false, label: RAW_UNITS[text.toLowerCase()] ?? text }
}

export type KrParse = { ok: true; kr: number } | { ok: false; error: string }

const SPACES = /[\s  ]/g

/** Kronor som redigerbar text: 123.45 blir "123,45", 123 blir "123". Inga tusentalsavgränsare. */
export function krToText(kr: number): string {
  return Number.isFinite(kr) ? String(kr).replace(".", ",") : ""
}

/** Kronor (text med , eller .) till tal. Högst två decimaler. */
export function parseKr(text: string): KrParse {
  const clean = text.replace(SPACES, "").replace(",", ".")
  if (clean === "") return { ok: false, error: "Ange ett belopp i kronor." }
  if (!/^-?\d+(\.\d{1,2})?$/.test(clean)) return { ok: false, error: "Ange kronor med högst två decimaler, till exempel 1250 eller 1250,50." }
  const kr = Number(clean)
  if (!Number.isSafeInteger(Math.round(kr * 100))) return { ok: false, error: "Beloppet är för stort." }
  return { ok: true, kr }
}

const krFormat = new Intl.NumberFormat("sv-SE", { minimumFractionDigits: 0, maximumFractionDigits: 2 })

/** Kronor som visningstext med eventuella decimaler, t.ex. "1 250,50 kr". */
export function formatMoneyKr(kr: number): string {
  return `${krFormat.format(kr)} kr`
}

const numberFormat = new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 6 })

/** Ett tal med enhet för visning. Belopp skrivs i kronor. */
export function formatWithUnit(value: number, unit: string | null | undefined): string {
  const info = unitInfo(unit)
  if (info.money) return info.label === "kr" ? formatMoneyKr(value) : `${krFormat.format(value)} ${info.label}`
  const text = numberFormat.format(value)
  if (!info.label) return text
  return info.label === "%" ? `${text} %` : `${text} ${info.label}`
}
