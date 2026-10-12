// Enheter och belopp. API:et räknar i öre (heltal); vyn visar och tar emot kronor. All omvandling sker här.

export type UnitInfo = { money: boolean; label: string }

const RAW_UNITS: Record<string, string> = {
  percent: "%", procent: "%", days: "dagar", dagar: "dagar", minutes: "minuter", minuter: "minuter", seconds: "sekunder", sekunder: "sekunder",
  hours: "timmar", timmar: "timmar", factor: "gånger", faktor: "gånger", fraction: "andel (0–1)", andel: "andel (0–1)",
}

const PER_TEXT: Record<string, string> = {
  year: "år", år: "år", session: "tillfälle", tillfälle: "tillfälle", pass: "pass", hour: "timme", timme: "timme", exam: "tentamen", tentamen: "tentamen",
  seat: "plats", plats: "plats", day: "dag", dag: "dag", minute: "minut", minut: "minut",
}

// "ore", "öre", "ore_per_year", "öre/timme", "öre per år" ...
const MONEY = /^(?:ore|öre)(?:[\s_/]+(?:per[\s_]+)?(.+))?$/i

/** Tolkar enhetstexten från API:et. Belopp i öre blir kronor; okända enheter visas som de är. */
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

export type KrParse = { ok: true; ore: number } | { ok: false; error: string }

const SPACES = /[\s  ]/g

/** Öre till kronor som redigerbar text: "12345" öre blir "123,45", "12300" blir "123". Inga tusentalsavgränsare. */
export function oreToKrText(ore: number): string {
  if (!Number.isFinite(ore)) return ""
  if (!Number.isInteger(ore)) return String(ore / 100).replace(".", ",") // bör inte förekomma; bevarar värdet förlustfritt
  const sign = ore < 0 ? "-" : ""
  const abs = Math.abs(ore)
  const kr = Math.floor(abs / 100)
  const rest = abs % 100
  return rest === 0 ? `${sign}${kr}` : `${sign}${kr},${String(rest).padStart(2, "0").replace(/0$/, "")}`
}

/** Kronor (text med , eller .) till öre. Högst två decimaler. */
export function parseKrToOre(text: string): KrParse {
  const clean = text.replace(SPACES, "").replace(",", ".")
  if (clean === "") return { ok: false, error: "Ange ett belopp i kronor." }
  if (!/^-?\d+(\.\d{1,2})?$/.test(clean)) return { ok: false, error: "Ange kronor med högst två decimaler, till exempel 1250 eller 1250,50." }
  const [whole, decimals = ""] = clean.replace("-", "").split(".")
  const ore = Number(whole) * 100 + Number(decimals.padEnd(2, "0"))
  if (!Number.isSafeInteger(ore)) return { ok: false, error: "Beloppet är för stort." }
  return { ok: true, ore: clean.startsWith("-") ? -ore : ore }
}

const krFormat = new Intl.NumberFormat("sv-SE", { minimumFractionDigits: 0, maximumFractionDigits: 2 })

/** Öre som visningstext i kronor med eventuella ören, t.ex. "1 250,50 kr". */
export function formatMoneyOre(ore: number): string {
  return `${krFormat.format(ore / 100)} kr`
}

const numberFormat = new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 6 })

/** Ett tal med enhet för visning. Belopp i öre skrivs som kronor. */
export function formatWithUnit(value: number, unit: string | null | undefined): string {
  const info = unitInfo(unit)
  if (info.money) return info.label === "kr" ? formatMoneyOre(value) : `${krFormat.format(value / 100)} ${info.label}`
  const text = numberFormat.format(value)
  if (!info.label) return text
  return info.label === "%" ? `${text} %` : `${text} ${info.label}`
}
