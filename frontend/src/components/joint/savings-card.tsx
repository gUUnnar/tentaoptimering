import { Loader2, TrendingDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { InfoTip } from "@/components/ui/info-tip"
import { formatKr } from "@/lib/jointFormat"
import type { SavingsReady } from "@/lib/savingsApi"
import { savingsHeadline } from "@/lib/savingsView"
import { useSavings } from "@/lib/useSavings"

const WHAT = <>
  <span className="block font-semibold">Besparingspotential</span>
  <span className="block">Skillnaden i modellens årliga kapacitetskostnad mellan en <strong>referensoptimering med låsta datum</strong> (samma scenario, data och kostnadsantaganden, men ingen tentamen flyttas från sitt bokade tillfälle; sal och bemanning optimeras) och den här körningen, där tentorna får flyttas.</span>
  <span className="block">Referensen är en modellberäkning. Den är <strong>inte</strong> den faktiska bokningen (A), som aldrig optimeras.</span>
  <span className="block">Det är en <strong>teoretisk</strong> potential för de valda tentorna, räknad med scenariots proxypriser. Den är inte en verifierad, realiserbar besparing: avtal, uppsägningstider och vilka kostnader som faktiskt kan undvikas ingår inte.</span>
</>

/** Det viktigaste resultatet: besparingspotentialen mot en referensoptimering med låsta datum. Referensen löses vid behov och sparas. */
export function SavingsCard({ runId }: { runId: string }) {
  const { state, error, running, start } = useSavings(runId)
  if (!state) return error ? <Card><CardContent className="pt-4 text-sm text-slate-900" role="status">Besparingspotentialen kan inte hämtas: {error}</CardContent></Card> : null
  return <Card>
    <CardContent className="space-y-2 pt-4">
      <div className="flex items-center gap-1.5 text-base font-bold"><TrendingDown size={16} aria-hidden="true"/>Besparingspotential, teoretisk
        <InfoTip label="Vad är besparingspotential?">{WHAT}</InfoTip></div>
      {state.state === "ready" && <Ready state={state}/>}
      {state.state === "missing" && !running && <div className="flex flex-wrap items-center gap-3">
        <Button type="button" onClick={() => void start()}>Beräkna besparingspotential</Button>
        <span className="text-sm text-slate-800">Jämför med en optimering där de bokade datumen är låsta (inte den faktiska bokningen).</span></div>}
      {running && <p className="flex items-center gap-2 text-sm" role="status"><Loader2 size={15} className="animate-spin" aria-hidden="true"/>Beräknar referensen med låsta datum …</p>}
      {state.state === "unavailable" && <p className="text-sm text-slate-800" role="status">{state.reason}</p>}
      {state.job?.status === "failed" && !running && <p className="text-sm text-red-900" role="alert">Beräkningen av referensen med låsta datum misslyckades: {state.job.error}</p>}
      {error && <p className="text-sm text-red-900" role="alert">{error}</p>}
    </CardContent>
  </Card>
}

function Ready({ state }: { state: SavingsReady }) {
  const head = savingsHeadline(state)
  return <>
    <div className="text-3xl font-bold tabular-nums">{head.positive ? head.amount : "Ingen besparing mot låsta datum"}</div>
    <p className="text-sm text-slate-900">{head.versus}</p>
    {head.range && <p className="text-xs text-slate-800">{head.range}</p>}
    {state.components.length > 0 && <details className="text-sm">
      <summary className="cursor-pointer text-xs font-medium underline">Var kommer skillnaden från?</summary>
      <table className="mt-2 w-full max-w-xl text-sm">
        <thead><tr className="border-b text-left text-xs text-slate-900"><th className="p-1.5">Kostnad per år</th><th className="p-1.5 text-right">Låsta datum</th><th className="p-1.5 text-right">Denna körning</th><th className="p-1.5 text-right">Skillnad</th></tr></thead>
        <tbody>{state.components.map(row => <tr key={row.key} className="border-b">
          <th scope="row" className="p-1.5 text-left font-medium">{row.label}</th>
          <td className="p-1.5 text-right tabular-nums">{formatKr(row.baseline_ore)}</td><td className="p-1.5 text-right tabular-nums">{formatKr(row.run_ore)}</td>
          <td className="p-1.5 text-right font-semibold tabular-nums">{formatKr((row.baseline_ore ?? 0) - (row.run_ore ?? 0))}</td></tr>)}</tbody>
      </table>
      <p className="mt-1.5 text-xs text-slate-800">Flyttade tentor: {state.run.changed_exams ?? "okänt"} av {state.run.exams_total ?? "okänt"}. Vaktpool: {state.baseline.staff_pool_size ?? "okänt"} med låsta datum, {state.run.staff_pool_size ?? "okänt"} i den här körningen.</p>
    </details>}
  </>
}
