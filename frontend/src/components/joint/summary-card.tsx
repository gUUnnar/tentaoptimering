import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { costStatement, firstSolutionBasisText, formatCount, formatDuration, formatGap, formatKr, outcomeLabel, sourceLabel } from "@/lib/jointFormat"
import { gapFraction } from "@/lib/jointState"
import type { JointSummary } from "@/lib/jointTypes"

/** Kostnad som intervall utan bevisat optimum, samt de viktigaste måtten för körningen. */
export function SummaryCard({ summary, labels }: { summary: JointSummary; labels: Record<string, string> }) {
  const gap = summary.gap ?? gapFraction(summary.cost_ore, summary.bound_ore)
  const statement = costStatement(summary.cost_ore, summary.bound_ore, summary.proven_optimum)
  const basis = firstSolutionBasisText(summary.first_solution_basis)
  const firstHint = [basis, summary.first_solution_source ? `från ${sourceLabel(summary.first_solution_source)}` : ""].filter(Boolean).join(", ")
  return <section className="space-y-3" aria-label="Sammanfattning av körningen">
    {!summary.has_verified_solution && <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-900">Körningen har ingen fullständig, kontrollerad lösning{summary.cancelled ? " (den stoppades)" : ""}. Kostnaderna nedan ska inte läsas som en lösning.</p>}
    <Card>
      <CardHeader><CardTitle>Sammanfattning</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <div className={statement.proven ? "rounded-md bg-emerald-50 p-3 text-emerald-900" : "rounded-md bg-amber-50 p-3 text-amber-900"}>
          <div className="text-xs">{statement.proven ? "Verifierad kostnad (lägsta möjliga i modellen är bevisad)" : "Kostnadsintervall: undre gräns–verifierad kostnad"}</div>
          <div className="mt-0.5 text-2xl font-semibold tabular-nums">{statement.headline}</div>
          <div className="mt-1 text-xs">{statement.note}</div>
          <div className="mt-1 text-xs">Det är en modellkostnad. Faktisk kostnad, teoretisk årlig potential och verifierad realiserbar besparing redovisas separat och framgår inte av denna siffra.</div>
        </div>
        <dl className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
          <Stat label="Verifierad kostnad" hint="Lägsta kostnad hittills som är kontrollerad" value={formatKr(summary.cost_ore)}/>
          <Stat label="Undre gräns" hint="Lägsta kostnad som bevisats möjlig" value={formatKr(summary.bound_ore)}/>
          <Stat label="Gap" hint={summary.gap_ore !== null ? `${formatKr(summary.gap_ore)} över undre gräns` : "Avstånd mellan de två"} value={formatGap(gap)}/>
          <Stat label="Flyttade tentor" hint={summary.exams_total !== null ? `av ${formatCount(summary.exams_total)}` : undefined} value={formatCount(summary.changed_exams)}/>
          <Stat label="Vaktpool" hint="Antal vakter" value={formatCount(summary.staff_pool_size)}/>
          <Stat label="Tid till första lösning" hint={firstHint || undefined} value={formatDuration(summary.first_solution_seconds)}/>
          <Stat label="Total tid" value={formatDuration(summary.wall_seconds)}/>
        </dl>
        <p className="text-xs text-slate-900">Utfall: <strong>{outcomeLabel(summary.outcome)}</strong></p>
        {summary.parameters_changed_from_default.length > 0 && <div className="text-xs text-slate-900">
          <p className="font-semibold">Parametrar som avviker från standardvärdet i den här körningen:</p>
          <ul className="mt-1 flex flex-wrap gap-1.5">{summary.parameters_changed_from_default.map(item => <li key={item.id} className="rounded border bg-slate-50 px-1.5 py-0.5">{item.label ?? labels[item.id] ?? item.id}</li>)}</ul>
        </div>}
      </CardContent>
    </Card>
  </section>
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return <div className="rounded-md border p-2.5"><dt className="text-xs text-slate-900">{label}</dt><dd className="mt-0.5 text-base font-semibold tabular-nums">{value}</dd>{hint && <p className="mt-0.5 text-[11px] text-slate-800">{hint}</p>}</div>
}
