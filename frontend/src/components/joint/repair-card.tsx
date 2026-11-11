import { CircleCheck, CircleHelp, Loader2, Wand2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Notice } from "@/components/ui/notice"
import type { RepairBody } from "@/lib/repairApi"
import { canApplyRepair, repairEffectText, repairIsVerified, repairProgressText, repairTitle, repairVerifiedText } from "@/lib/repairView"
import { useRepair } from "@/lib/useRepair"

type Props = {
  /** Det som söks för: samma kropp som en körning (ett scenario, eller en tidigare körning som `run-…`). */
  body: RepairBody
  /** Ändras nyckeln försvinner ett gammalt förslag. */
  stateKey: string
  /** Fyller i förslagets parametrar i formuläret. */
  onApply: (parameters: Record<string, unknown>) => void
  disabled?: boolean
}

/** "Föreslå minsta ändring" för en körning som inte går att lösa: den minsta mängd ändringar (kalender, datum, fasta bokningar) som solvern visar går. */
export function RepairCard({ body, stateKey, onApply, disabled }: Props) {
  const repair = useRepair(stateKey)
  const running = repair.status === "running"
  const result = repair.result
  return <div className="space-y-2 rounded-md border border-slate-300 bg-white p-3 text-sm text-slate-900" aria-label="Förslag på ändring">
    <div className="flex flex-wrap items-center gap-3">
      <Button type="button" variant="outline" disabled={disabled || running} onClick={() => void repair.run(body)}>
        <Wand2 size={15} className="mr-1" aria-hidden="true"/>{running ? "Söker …" : result ? "Föreslå igen" : "Föreslå minsta ändring"}
      </Button>
      <span className="text-xs text-slate-800">Söker bland kalender, datum och fasta bokningar. Det kan ta några minuter.</span>
    </div>
    {running && <p className="flex items-center gap-2" role="status"><Loader2 size={15} className="animate-spin" aria-hidden="true"/>{repairProgressText(repair.current)}</p>}
    {repair.status === "error" && <Notice tone="error" title="Sökningen kunde inte genomföras." open><p>{repair.error}</p></Notice>}
    {repair.status === "done" && result && <div className="space-y-2" role="status">
      <p className="flex items-center gap-2 font-semibold">
        {repairIsVerified(result) ? <CircleCheck size={16} className="text-emerald-700" aria-hidden="true"/> : <CircleHelp size={16} className="text-amber-700" aria-hidden="true"/>}
        {repairTitle(result)}
      </p>
      <p>{result.summary}</p>
      {result.steps.length > 0 && <ul className="list-disc space-y-1 pl-5">
        {result.steps.map(step => <li key={step.id}>{step.label}{step.side_effect && <span className="block text-xs text-amber-900">{step.side_effect}</span>}</li>)}
      </ul>}
      {repairEffectText(result) && <p>{repairEffectText(result)}</p>}
      {repairVerifiedText(result) && <p>{repairVerifiedText(result)}</p>}
      {canApplyRepair(result) && <Button type="button" onClick={() => onApply(result.parameters)}>Tillämpa i formuläret</Button>}
      <p className="text-xs text-slate-700">{result.note}</p>
    </div>}
  </div>
}
