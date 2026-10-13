import type { DataQuality } from "@/lib/bookingTypes"
import { flagList } from "@/lib/bookingView"

/**
 * Fynd i datat för de rader som visas: räkningar utan tolkning. Orsaken till ett fynd anges inte. Rader som liknar ett mönster som
 * dataägaren ännu inte bekräftat redovisas för sig och är inte omklassade.
 */
export function Findings({ quality }: { quality: DataQuality }) {
  const flags = flagList(quality)
  const unverified = Object.entries(quality.unverified_rule_matches)
  if (!flags.length && !unverified.length) return null
  return <section aria-label="Fynd i datat" className="rounded-md border border-slate-200 bg-white p-3 text-xs text-slate-900">
    <h3 className="text-sm font-semibold">Fynd i datat</h3>
    {flags.length > 0 && <ul className="mt-1 flex flex-wrap gap-1.5">{flags.map(flag => <li key={flag.code} className="rounded border bg-slate-50 px-1.5 py-0.5" title={flag.code}>{flag.label}: <strong>{flag.count}</strong></li>)}</ul>}
    {unverified.length > 0 && <p className="mt-1.5 text-slate-800">Rader som liknar mönster som dataägaren inte bekräftat (inte omklassade): {unverified.map(([id, count]) => `${id} (${count})`).join(", ")}.</p>}
    <p className="mt-1.5 text-slate-800">Fynden beskriver vad uttaget innehåller. De säger inte varför uppgifter saknas.</p>
  </section>
}
