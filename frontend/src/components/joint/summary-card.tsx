import { CircleX } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { describeVerdict } from "@/lib/jointFormat"
import { changedParameters, changedParametersHeading, summaryView, type StatView } from "@/lib/jointSummaryView"
import type { JointSummary } from "@/lib/jointTypes"
import { VerdictChip } from "./status-chip"

/**
 * Sammanfattningen. Med verifierad lösning: kostnad som intervall (utan bevisat optimum) och de viktigaste måtten.
 * Utan verifierad lösning: bara ett besked med skälet och domarna, aldrig en kostnad eller ett intervall.
 */
export function SummaryCard({ summary, labels }: { summary: JointSummary; labels: Record<string, string> }) {
  const view = summaryView(summary)
  const changed = changedParameters(summary, labels)
  return <section className="space-y-3" aria-label="Sammanfattning av körningen">
    <Card>
      <CardHeader><CardTitle>Sammanfattning</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {view.verified ? <>
          <div className={view.statement.proven ? "rounded-md bg-emerald-50 p-3 text-emerald-900" : "rounded-md bg-amber-50 p-3 text-amber-900"}>
            <div className="text-xs">{view.statement.proven ? "Verifierad kostnad (lägsta möjliga i modellen är bevisad)" : "Kostnadsintervall: undre gräns–verifierad kostnad"}</div>
            <div className="mt-0.5 text-2xl font-semibold tabular-nums">{view.statement.headline}</div>
            <div className="mt-1 text-xs">{view.statement.note}</div>
            <div className="mt-1 text-xs">Det är en modellkostnad. Faktisk kostnad, teoretisk årlig potential och verifierad realiserbar besparing redovisas separat och framgår inte av denna siffra.</div>
          </div>
          <Stats stats={view.stats}/>
          <p className="text-xs text-slate-900">Utfall: <strong>{view.outcomeText}</strong></p>
        </> : <>
          <div role="alert" className="rounded-md border-2 border-red-700 bg-red-50 p-3 text-red-950">
            <p className="flex items-center gap-2 text-base font-semibold"><CircleX size={20} className="shrink-0" aria-hidden="true"/>Körningen har ingen verifierad lösning{summary.cancelled ? " (den stoppades)" : ""}</p>
            <p className="mt-1 text-sm">{view.reason}</p>
            <p className="mt-1 text-xs">Därför redovisas ingen kostnad, inget kostnadsintervall och inga mått för en lösning. En placering som inte är kontrollerad räknas inte som lösning.</p>
            <dl className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs" aria-label="Domar">
              <div className="flex items-center gap-1.5"><dt>Teknisk eftervalidering:</dt><dd><VerdictChip status={describeVerdict(summary.technical_validation).status}/></dd></div>
              <div className="flex items-center gap-1.5"><dt>Verksamhetsmässig verifiering:</dt><dd><VerdictChip status={describeVerdict(summary.business_verification).status}/></dd></div>
            </dl>
          </div>
          <Stats stats={view.stats}/>
        </>}
        <div className="text-xs text-slate-900">
          <p className="font-semibold">{changedParametersHeading(summary)}</p>
          {changed.length > 0 && <ul className="mt-1 flex flex-wrap gap-1.5" aria-label="Parametrar som avviker från standardvärdet">
            {changed.map(item => <li key={item.id} title={item.id} className="rounded border bg-slate-50 px-1.5 py-0.5">{item.label ?? <span className="font-mono text-[11px]">{item.id}</span>}</li>)}
          </ul>}
        </div>
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
