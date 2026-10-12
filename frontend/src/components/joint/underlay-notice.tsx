import { Database } from "lucide-react"
import { Button } from "@/components/ui/button"

/** Besked när underlaget saknas, med genväg till sidan Underlag. */
export function UnderlayNotice({ onOpen, detail }: { onOpen: () => void; detail?: string }) {
  return <div role="alert" className="flex flex-wrap items-start justify-between gap-3 rounded-md border-2 border-amber-700 bg-amber-50 p-3 text-sm text-amber-950">
    <div className="flex max-w-3xl items-start gap-2">
      <Database size={18} className="mt-0.5 shrink-0" aria-hidden="true"/>
      <div>
        <p className="font-semibold">Underlaget är inte förberett.</p>
        <p className="mt-0.5">{detail ?? "Optimeringen räknar på ett förberett underlag och hela terminen kan inte köras utan det. Välj källdatakatalog och förbered underlaget under Underlag, kom sedan tillbaka hit."}</p>
      </div>
    </div>
    <Button type="button" variant="outline" onClick={onOpen}>Gå till Underlag</Button>
  </div>
}
