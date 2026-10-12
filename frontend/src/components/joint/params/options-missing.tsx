import { Database } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { OptionsLoad } from "@/lib/paramOptions"

export const PREPARE_TEXT = "Förbered underlaget för att kunna välja"

/** Skrivskyddad visning av en parameter vars alternativ saknas: aktuellt värde och varför den inte går att ändra än. */
export function OptionsMissing({ load, valueText, describedBy, label, onOpenUnderlay, onRetry }: {
  load: OptionsLoad; valueText: string; describedBy: string; label: string; onOpenUnderlay: () => void; onRetry: () => void
}) {
  const waiting = load.status === "idle" || load.status === "loading"
  return <div role="group" aria-label={label} aria-describedby={describedBy} className="rounded-md border border-slate-300 bg-white p-2 text-sm">
    <div className="whitespace-pre-wrap break-words">{valueText}</div>
    {waiting && <p className="mt-1 text-xs text-slate-800" role="status">Hämtar alternativen ur underlaget …</p>}
    {load.status === "error" && <div className="mt-1 text-xs text-red-900" role="alert">
      <p>Kunde inte hämta alternativen: {load.error}</p>
      <div className="mt-1.5 flex flex-wrap gap-2">
        <Button type="button" size="sm" variant="outline" onClick={onRetry}>Försök igen</Button>
        <Button type="button" size="sm" variant="outline" onClick={onOpenUnderlay}><Database size={13} className="mr-1" aria-hidden="true"/>{PREPARE_TEXT}</Button>
      </div>
    </div>}
    {load.status === "ready" && <div className="mt-1.5">
      <p className="text-xs text-slate-800">Visas bara, eftersom underlaget inte är förberett.</p>
      <Button type="button" size="sm" variant="outline" className="mt-1.5" onClick={onOpenUnderlay}><Database size={13} className="mr-1" aria-hidden="true"/>{PREPARE_TEXT}</Button>
    </div>}
  </div>
}
