import { CircleCheck, CircleHelp, CircleX } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { COST_NAME, COST_SCOPE, describeVerdict } from "@/lib/jointFormat"
import { summaryView, type StatView } from "@/lib/jointSummaryView"
import type { JointSummary } from "@/lib/jointTypes"
import { VerdictChip } from "./status-chip"
import { InfoTip } from "@/components/ui/info-tip"
import { Notice } from "@/components/ui/notice"
import { HowToRead } from "./how-to-read"

/**
 * Sammanfattningen. Med verifierad lösning: kostnad som intervall (utan bevisat optimum) och de viktigaste måtten.
 * Utan verifierad lösning: bara ett besked med skälet och domarna, aldrig en kostnad eller ett intervall.
 */
export function SummaryCard({ summary, labels }: { summary: JointSummary; labels: Record<string, string> }) {
  const view = summaryView(summary)
  const Extras = () => <PlanningNote summary={summary}/>
  return <section className="space-y-3" aria-label="Sammanfattning av körningen">
    <Card>
      <CardHeader><CardTitle className="flex items-center gap-1.5">Sammanfattning<InfoTip label="Så läser du resultatet"><HowToRead/></InfoTip></CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {view.verified ? <>
          <div className="rounded-md border p-3">
            <div className="flex items-center gap-2 text-sm font-bold">
              {view.statement.proven ? <CircleCheck size={18} className="text-emerald-700" aria-hidden="true"/> : <CircleHelp size={18} className="text-amber-700" aria-hidden="true"/>}
              {view.statement.proven ? "Lägsta kostnad i modellen, bevisad" : "Lägsta funna kostnad, inte bevisat lägsta"}
              <InfoTip label="Om kostnaden">
                <span className="block">{COST_NAME} {COST_SCOPE}.</span>
                <span className="block">{view.statement.note}</span>
                <span className="block">Det är en modellkostnad. Faktisk kostnad och verifierad realiserbar besparing redovisas separat.</span>
              </InfoTip>
            </div>
            <div className="mt-1 text-3xl font-bold tabular-nums">{view.statement.headline}</div>
          </div>
          <Stats stats={view.stats}/>
          <p className="text-xs text-slate-900">Utfall: <strong>{view.outcomeText}</strong></p>
        </> : <>
          <div role="alert" className="rounded-md border border-red-700 bg-red-50 p-3 text-red-950">
            <p className="flex items-center gap-2 text-base font-semibold"><CircleX size={20} className="shrink-0" aria-hidden="true"/>Körningen har ingen verifierad lösning{summary.cancelled ? " (den stoppades)" : ""}</p>
            <p className="mt-1 text-sm">{view.reason}</p>
            <p className="mt-1 text-xs">Därför redovisas ingen kostnad, inget kostnadsintervall och inga mått för en lösning.</p>
          </div>
          <Stats stats={view.stats}/>
        </>}
        {view.verified ? <Extras/> : <details className="text-xs text-slate-900"><summary className="cursor-pointer font-medium">Planering och domar</summary><div className="mt-2 space-y-3"><Extras/>
          <dl className="flex flex-wrap gap-x-5 gap-y-1" aria-label="Domar">
            <div className="flex items-center gap-1.5"><dt>Teknisk eftervalidering:</dt><dd><VerdictChip status={describeVerdict(summary.technical_validation).status}/></dd></div>
            <div className="flex items-center gap-1.5"><dt>Verksamhetsmässig verifiering:</dt><dd><VerdictChip status={describeVerdict(summary.business_verification).status}/></dd></div>
          </dl></div></details>}
      </CardContent>
    </Card>
  </section>
}

function Stats({ stats }: { stats: StatView[] }) {
  if (!stats.length) return null
  return <dl className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
    {stats.map(stat => <div key={stat.label} className="rounded-md border p-2.5"><dt className="text-xs text-slate-900">{stat.label}</dt><dd className="mt-0.5 text-base font-semibold tabular-nums">{stat.value}</dd>{stat.hint && <p className="mt-0.5 text-[11px] text-slate-800">{stat.hint}</p>}</div>)}
  </dl>
}

/** Perioden körningen planerades för och hur resultatet ska läsas: explorativt, utan kännedom om bokningar utanför de valda tentorna. */
function PlanningNote({ summary }: { summary: JointSummary }) {
  const { date_from: from, date_to: to } = summary.period
  const basis = summary.planning_basis
  if (!from && !to && !basis) return null
  return <div className="space-y-2">
    <p className="flex items-center gap-1.5 rounded-md bg-slate-100 p-2.5 text-xs text-slate-900">
      {(from || to) && <span><strong>Planeringsperiod:</strong> {from ?? "början"} – {to ?? "slutet"}</span>}
      {basis && <><span aria-hidden="true">·</span><strong>{basis.label}</strong>
        <InfoTip label="Om planeringsunderlaget">
          {basis.reasons.length > 0 ? <><span className="block font-semibold">Skäl:</span>{basis.reasons.map(reason => <span key={reason.code} className="block">• {reason.text}</span>)}</> : <span className="block">{basis.note}</span>}
          <span className="block"><strong>{basis.cost_name}.</strong> {basis.cost_note}</span>
        </InfoTip></>}
    </p>
    {summary.period.partial && <Notice tone="warning" title="Delvis planerad period"><p>Du valde {summary.period.requested_from} – {summary.period.requested_to}, men underlaget täcker bara {from} – {to} (godkänd kortare period). Resultatet gäller inte hela den valda perioden.</p></Notice>}
  </div>
}
