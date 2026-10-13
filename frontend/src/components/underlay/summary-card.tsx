import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatBytes, formatWhen } from "@/lib/underlay"
import type { UnderlayManifest } from "@/lib/underlayApi"

const COUNT_LABELS: [string, string][] = [["bookings", "Bokningsrader"], ["exam_events", "Tentamenstillfällen"], ["ladok_activities", "Ladok-aktiviteter"], ["optimization_demands", "Efterfrågeposter"], ["optimization_rooms", "Salar i lokalregistret"]]
const number = (value: number | null | undefined) => (value === null || value === undefined ? "okänt" : value.toLocaleString("sv-SE"))

/** Vad det förberedda underlaget innehåller och vad det byggdes av, ur underlagets manifest. */
export function SummaryCard({ manifest }: { manifest: UnderlayManifest }) {
  const { period, quality } = manifest
  return <Card>
    <CardHeader><CardTitle>Förberett underlag</CardTitle></CardHeader>
    <CardContent className="space-y-4 text-sm text-slate-900">
      <dl className="grid max-w-3xl grid-cols-[max-content_1fr] gap-x-6 gap-y-1">
        <dt className="text-slate-800">Förberett</dt><dd>{formatWhen(manifest.prepared_at)}</dd>
        <dt className="text-slate-800">Källkatalog</dt><dd><code className="break-all">{manifest.source_dir}</code></dd>
        <dt className="text-slate-800">Bokningarnas period</dt><dd>{period.first && period.last ? `${period.first} till ${period.last}` : "ingen daterad bokning"} <span className="text-xs text-slate-800">({number(period.dated_rows)} daterade rader)</span></dd>
        {COUNT_LABELS.map(([key, label]) => <div key={key} className="contents"><dt className="text-slate-800">{label}</dt><dd>{number(manifest.counts[key])}</dd></div>)}
      </dl>
      <div>
        <h3 className="mb-1 font-semibold">Byggt av</h3>
        <ul className="space-y-1">{Object.entries(manifest.sources).map(([role, source]) => <li key={role}><code className="text-xs">{source.filename}</code> <span className="text-xs text-slate-800">{formatBytes(source.bytes)}, ändrad {formatWhen(source.modified)}{source.sha256 ? `, sha256 ${source.sha256.slice(0, 12)}…` : ""}</span></li>)}</ul>
      </div>
      <div>
        <h3 className="mb-1 font-semibold">Datakvalitet och täckning</h3>
        <p>{quality.critical_findings > 0 ? <span className="text-amber-900">{quality.critical_findings} kritiska av {quality.findings} kvalitetsfynd.</span> : `${quality.findings} kvalitetsfynd, inga kritiska.`} Efterfrågan har tentandsunderlag för {quality.demand_coverage_percent === null ? "okänd andel" : `${String(quality.demand_coverage_percent).replace(".", ",")} procent`} av Ladok-aktiviteterna; {number(quality.unresolved_activities)} aktiviteter är ej avgjorda i omfattningen{quality.scope_complete === false ? " och omfattningen är därför inte komplett för hela populationen" : ""}.</p>
        <p className="mt-1 text-xs text-slate-800">Detaljerna finns i rapporterna <code>data_quality.json</code>, <code>demand_scope.md</code> och <code>optimization_readiness.md</code> under användarprofilens <code>reports</code>.</p>
      </div>
    </CardContent>
  </Card>
}
