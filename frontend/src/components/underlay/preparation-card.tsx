import { CircleAlert, CircleCheck, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { JobProgress, UnderlayStatus } from "@/lib/underlay"

type Props = {
  progress: JobProgress; error: string; status: UnderlayStatus | "error"
  canPrepare: boolean; why: string | null; onPrepare: () => void
}

const STATUS_TEXT: Record<UnderlayStatus | "error", string> = {
  present: "Förberett underlag finns. Optimeringen kan köras.",
  missing: "Underlaget är inte förberett än. Optimeringen av tentor ur underlaget kan inte köras förrän förberedelsen är klar.",
  unknown: "Det går inte att avgöra om underlaget är förberett.",
  error: "Kunde inte kontrollera om underlaget är förberett (servern svarade inte).",
}

/** Förklaring av vad förberedelsen gör, start av den och dess status. */
export function PreparationCard({ progress, error, status, canPrepare, why, onPrepare }: Props) {
  const busy = progress === "starting" || progress === "running"
  return <Card>
    <CardHeader><CardTitle>2. Förbered underlaget</CardTitle></CardHeader>
    <CardContent className="space-y-3">
      <div className="max-w-3xl space-y-2 text-sm text-slate-900">
        <p>Förberedelsen läser Excel-filerna i källdatakatalogen (tentaplaceringar, Ladok-uppgifter om tentander och lokalhyror), rensar och kopplar ihop dem och sparar ett bearbetat underlag som optimeringen räknar på: tentor, deltagare, salar och möjliga placeringar.</p>
        <p><strong>Förberedelsen krävs före en optimering.</strong> Scenarier som väljer tentor efter regler hämtar dem ur det förberedda underlaget. Kör den första gången och igen när källfilerna har bytts ut. Det tar en stund; du kan lämna sidan under tiden.</p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" disabled={!canPrepare} onClick={onPrepare} aria-describedby="prepare-why">{busy ? "Förbereder …" : "Förbered underlag"}</Button>
        {why && <span id="prepare-why" className="text-xs text-slate-800">{why}</span>}
      </div>
      {busy && <p className="flex items-center gap-2 text-sm" role="status"><Loader2 size={16} className="animate-spin" aria-hidden="true"/>{progress === "starting" ? "Startar förberedelsen …" : "Underlaget förbereds. Det kan ta flera minuter."}</p>}
      {progress === "completed" && <p className="flex items-center gap-2 text-sm text-emerald-900" role="status"><CircleCheck size={16} aria-hidden="true"/>Underlaget har förberetts.</p>}
      {progress === "failed" && <div className="flex items-start gap-2 rounded-md border border-red-700 bg-red-50 p-3 text-sm text-red-900" role="alert"><CircleAlert size={18} className="mt-0.5 shrink-0" aria-hidden="true"/><div><p className="font-semibold">Förberedelsen misslyckades.</p><p className="whitespace-pre-line">{error}</p></div></div>}
      {progress !== "failed" && error && <p className="text-xs text-amber-900" role="alert">{error}</p>}
      <p className={`border-t pt-3 text-sm ${status === "missing" ? "text-amber-900" : "text-slate-900"}`} role="status"><strong>Läge:</strong> {STATUS_TEXT[status]}</p>
    </CardContent>
  </Card>
}
