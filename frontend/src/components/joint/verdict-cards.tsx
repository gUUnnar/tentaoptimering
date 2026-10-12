import { TriangleAlert } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { describeVerdict } from "@/lib/jointFormat"
import type { JointSummary } from "@/lib/jointTypes"
import { VerdictChip } from "./status-chip"

/** De tre domarna hålls isär. Teknisk korrekthet är aldrig verksamhetsmässig genomförbarhet. */
export function VerdictCards({ summary }: { summary: JointSummary }) {
  const technical = describeVerdict(summary.technical_validation)
  const business = describeVerdict(summary.business_verification)
  const provenance = describeVerdict(summary.provenance)
  return <section className="space-y-4" aria-label="De tre bedömningarna">
    <div className="flex items-start gap-2 rounded-md border-2 border-amber-700 bg-amber-50 p-3 text-sm text-amber-950" role="note">
      <TriangleAlert size={18} className="mt-0.5 shrink-0" aria-hidden="true"/>
      <p><strong>Teknisk korrekthet är inte verksamhetsmässig genomförbarhet.</strong> Den tekniska eftervalideringen visar att placeringen följer de regler modellen kan uttrycka. Den visar inte att schemat går att genomföra i verksamheten. Data eller modellstöd som saknas räknas aldrig som godkänt.</p>
    </div>
    <div className="grid gap-4 lg:grid-cols-3">
      <Card><CardHeader><CardTitle>Teknisk eftervalidering</CardTitle></CardHeader><CardContent className="space-y-2 text-xs">
        <VerdictChip status={technical.status}/>
        <p className="text-slate-800">Fristående kontroll av att placeringen är fullständig och följer de hårda villkoren.</p>
        {technical.reason && <p>{technical.reason}</p>}
        <Details items={technical.details}/>
      </CardContent></Card>
      <Card><CardHeader><CardTitle>Verksamhetsmässig verifiering</CardTitle></CardHeader><CardContent className="space-y-2 text-xs">
        <VerdictChip status={business.status}/>
        <p className="text-slate-800">Om schemat går att genomföra med faktiska avtal, lagar och arbetstidsvillkor. Normalt <code>not_evaluated</code> (ej bedömd) i nuläget.</p>
        {business.reason && <p>{business.reason}</p>}
        <Details items={business.details}/>
      </CardContent></Card>
      <Card><CardHeader><CardTitle>Ursprung</CardTitle></CardHeader><CardContent className="space-y-2 text-xs">
        {provenance.status && <p>Status: {provenance.status === "not_evaluated" ? "ej bedömd (not_evaluated)" : provenance.status}</p>}
        {provenance.reason && <p>{provenance.reason}</p>}
        <Details items={provenance.details}/>
        {!provenance.status && !provenance.reason && !provenance.details.length && <p className="text-slate-800">Ursprunget är inte redovisat.</p>}
        <p className="text-slate-800">Visar vilka data och antaganden resultatet vilar på.</p>
      </CardContent></Card>
    </div>
  </section>
}

function Details({ items }: { items: [string, string][] }) {
  if (!items.length) return null
  return <dl className="space-y-0.5">{items.map(([key, value]) => <div key={key} className="flex justify-between gap-2 border-t border-slate-100 pt-0.5"><dt className="text-slate-800">{key}</dt><dd className="text-right font-medium">{value}</dd></div>)}</dl>
}
