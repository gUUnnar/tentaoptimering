import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { describeVerdict } from "@/lib/jointFormat"
import type { JointSummary } from "@/lib/jointTypes"
import { VerdictChip } from "./status-chip"
import { InfoTip } from "@/components/ui/info-tip"

/** De tre domarna hålls isär. Teknisk korrekthet är aldrig verksamhetsmässig genomförbarhet. */
export function VerdictCards({ summary }: { summary: JointSummary }) {
  const technical = describeVerdict(summary.technical_validation)
  const business = describeVerdict(summary.business_verification)
  const provenance = describeVerdict(summary.provenance)
  return <section className="space-y-4" aria-label="De tre bedömningarna">
    <h3 className="flex items-center gap-1.5 text-sm font-semibold">Bedömningar
      <InfoTip label="Teknisk korrekthet och genomförbarhet">Teknisk korrekthet är inte verksamhetsmässig genomförbarhet. Den tekniska eftervalideringen visar att placeringen följer de regler modellen kan uttrycka, inte att schemat går att genomföra i verksamheten. Data eller modellstöd som saknas räknas aldrig som godkänt.</InfoTip></h3>
    <div className="grid gap-4 lg:grid-cols-3">
      <Card><CardHeader><CardTitle className="flex items-center gap-1.5">Teknisk eftervalidering<InfoTip label="Vad är det här?">Fristående kontroll av att placeringen är fullständig och följer de hårda villkoren.</InfoTip></CardTitle></CardHeader><CardContent className="space-y-2 text-xs">
        <VerdictChip status={technical.status}/>
        {technical.reason && <p>{technical.reason}</p>}
        <Details items={technical.details}/>
      </CardContent></Card>
      <Card><CardHeader><CardTitle className="flex items-center gap-1.5">Verksamhetsmässig verifiering<InfoTip label="Vad är det här?">Om schemat går att genomföra med faktiska avtal, lagar och arbetstidsvillkor. Normalt ej bedömd i nuläget.</InfoTip></CardTitle></CardHeader><CardContent className="space-y-2 text-xs">
        <VerdictChip status={business.status}/>
        {business.reason && <p>{business.reason}</p>}
        <Details items={business.details}/>
      </CardContent></Card>
      <Card><CardHeader><CardTitle className="flex items-center gap-1.5">Ursprung<InfoTip label="Vad är det här?">Visar vilka data och antaganden resultatet vilar på.</InfoTip></CardTitle></CardHeader><CardContent className="space-y-2 text-xs">
        {provenance.status && <p>Status: {provenance.status === "not_evaluated" ? "ej bedömd (not_evaluated)" : provenance.status}</p>}
        {provenance.reason && <p>{provenance.reason}</p>}
        <Details items={provenance.details}/>
        {!provenance.status && !provenance.reason && !provenance.details.length && <p className="text-slate-800">Ursprunget är inte redovisat.</p>}
      </CardContent></Card>
    </div>
  </section>
}

function Details({ items }: { items: [string, string][] }) {
  if (!items.length) return null
  return <dl className="space-y-0.5">{items.map(([key, value]) => <div key={key} className="flex justify-between gap-2 border-t border-slate-100 pt-0.5"><dt className="text-slate-800">{key}</dt><dd className="text-right font-medium">{value}</dd></div>)}</dl>
}
