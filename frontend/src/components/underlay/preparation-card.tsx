import { CircleAlert, CircleCheck, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { STATE_TEXT } from "@/lib/underlay"
import type { PreparationJob, UnderlayInfo } from "@/lib/underlayApi"

type Props = {
  underlay: UnderlayInfo | null; job: PreparationJob | null; running: boolean; starting: boolean; stateError: string; startError: string
  canPrepare: boolean; why: string | null; onPrepare: () => void; onOpenJoint: () => void
}

/** Stegen i förberedelsen med det pågående steget markerat. */
function Steps({ job }: { job: PreparationJob }) {
  const done = job.progress.index
  return <ol className="space-y-1 text-sm" aria-label="Steg i förberedelsen">
    {job.steps.map((step, position) => {
      const state = position + 1 < done ? "klart" : position + 1 === done ? "pågår" : "väntar"
      return <li key={step.key} className={`flex items-center gap-2 ${state === "väntar" ? "text-slate-700" : "text-slate-900"}`}>
        {state === "klart" ? <CircleCheck size={15} className="text-emerald-800" aria-hidden="true"/> : state === "pågår" ? <Loader2 size={15} className="animate-spin" aria-hidden="true"/> : <span className="inline-block size-[15px] rounded-full border border-slate-400" aria-hidden="true"/>}
        <span>{step.label}</span><span className="sr-only"> ({state})</span>
      </li>
    })}
  </ol>
}

/** Förklaring av vad förberedelsen gör, start av den, stegvis förlopp och underlagets tillstånd. */
export function PreparationCard({ underlay, job, running, starting, stateError, startError, canPrepare, why, onPrepare, onOpenJoint }: Props) {
  const state = underlay?.state ?? "missing"
  const prepared = state !== "missing"
  const label = running || starting ? "Förbereder …" : prepared ? "Förbered om" : "Förbered underlag"
  const ask = () => {
    if (state === "current" && !window.confirm("Underlaget är redan förberett och stämmer med källfilerna. Vill du förbereda det om ändå?")) return
    onPrepare()
  }
  return <Card>
    <CardHeader><CardTitle>2. Förbered underlaget</CardTitle></CardHeader>
    <CardContent className="space-y-3">
      <div className="max-w-3xl space-y-2 text-sm text-slate-900">
        <p>Förberedelsen läser Excel-filerna i källdatakatalogen (tentaplaceringar, Ladok-uppgifter om tentander och lokalhyror), rensar och kopplar ihop dem och sparar ett bearbetat underlag som optimeringen räknar på: tentor, deltagare, salar och möjliga placeringar.</p>
        <p><strong>Förberedelsen krävs före en optimering.</strong> Scenarier som väljer tentor efter regler hämtar dem ur det förberedda underlaget. Kör den första gången och igen när källfilerna har bytts ut. Det tar vanligtvis från några sekunder till någon minut. Det gamla underlaget ersätts först när det nya är helt klart, så ett avbrott förstör inget.</p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" disabled={!canPrepare} onClick={ask} aria-describedby="prepare-why">{label}</Button>
        {why && <span id="prepare-why" className="text-xs text-slate-800">{why}</span>}
      </div>
      {(running || starting) && <div role="status" className="space-y-2">
        <p className="text-sm">{job ? `Steg ${Math.max(job.progress.index, 1)} av ${job.progress.total}: ${job.progress.label}` : "Startar förberedelsen …"}</p>
        {job && <Steps job={job}/>}
      </div>}
      {!running && job?.status === "completed" && <p className="flex items-center gap-2 text-sm text-emerald-900" role="status"><CircleCheck size={16} aria-hidden="true"/>Underlaget har förberetts.</p>}
      {!running && job?.status === "failed" && <div className="flex items-start gap-2 rounded-md border border-red-700 bg-red-50 p-3 text-sm text-red-900" role="alert"><CircleAlert size={18} className="mt-0.5 shrink-0" aria-hidden="true"/><div><p className="font-semibold">Förberedelsen misslyckades. Det tidigare underlaget är orört.</p><p className="whitespace-pre-line">{job.error}</p></div></div>}
      {startError && <p className="whitespace-pre-line text-sm text-red-900" role="alert">{startError}</p>}
      {stateError && <p className="text-sm text-red-900" role="alert">Kunde inte läsa underlagets tillstånd från servern: {stateError}</p>}
      <div className={`border-t pt-3 text-sm ${state === "current" ? "text-slate-900" : state === "missing" ? "text-amber-900" : "text-amber-900"}`} role="status">
        <p><strong>Läge:</strong> {underlay ? STATE_TEXT[state] : stateError ? "Okänt." : "Läser underlagets tillstånd …"}</p>
        {underlay?.reasons.length ? <ul className="mt-1 list-disc pl-5">{underlay.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul> : null}
        {state === "current" && !running && <Button type="button" className="mt-2" onClick={onOpenJoint}>Gå till Optimering</Button>}
      </div>
    </CardContent>
  </Card>
}
