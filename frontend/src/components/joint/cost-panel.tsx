import { CartesianGrid, Line, LineChart, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Flag, Info } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { costStatement, formatDuration, formatGap, formatKr, sourceLabel } from "@/lib/jointFormat"
import { bestIncumbent, costSeries, currentBoundOre, currentCostOre, firstIncumbent, gapFraction, type JointState } from "@/lib/jointState"

const MKR = 100_000_000
const tick = (value: number) => `${value.toFixed(2).replace(".", ",")}`

export function CostPanel({ state, nowT }: { state: JointState; nowT: number }) {
  const cost = currentCostOre(state)
  const bound = currentBoundOre(state)
  const gap = gapFraction(cost, bound)
  const statement = costStatement(cost, bound, state.finished?.outcome === "optimal")
  const first = firstIncumbent(state)
  const data = costSeries(state, nowT)
  const values = data.flatMap(p => [p.upper, p.lower]).filter((v): v is number => v !== undefined)
  const domain: [number, number] | undefined = values.length ? [Math.min(...values) * 0.99, Math.max(...values) * 1.01] : undefined
  const label = `Kostnad över tid. ${cost === null ? "Ingen kontrollerad lösning ännu." : `Verifierad kostnad ${formatKr(cost)}.`} ${bound === null ? "Ingen undre gräns bevisad ännu." : `Undre gräns ${formatKr(bound)}.`}`
  return <Card>
    <CardHeader><CardTitle>Kostnad över tid</CardTitle></CardHeader>
    <CardContent className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-3">
        <Figure title="Verifierad kapacitetskostnad (årlig, valt urval)" value={formatKr(cost)} hint={bestIncumbent(state)?.source ? `Lägsta kostnad hittills som är kontrollerad. Från: ${sourceLabel(bestIncumbent(state)!.source)}` : "Ingen kontrollerad lösning ännu"}/>
        <Figure title="Undre gräns" value={formatKr(bound)} hint={state.bounds.length ? `Lägsta kostnad som bevisats möjlig (varv ${state.bounds.at(-1)!.round})` : "Ingen gräns bevisad ännu"}/>
        <Figure title="Gap" value={formatGap(gap)} hint="Hur långt verifierad kostnad ligger över undre gräns, i procent av kostnaden"/>
      </div>
      <div className={statement.proven ? "rounded-md bg-emerald-50 p-3 text-sm text-emerald-900" : "rounded-md bg-amber-50 p-3 text-sm text-amber-900"} role="status">
        <div className="flex items-start gap-2"><Info size={16} className="mt-0.5 shrink-0" aria-hidden="true"/><div><div><strong>{statement.proven ? "Kostnad" : "Kostnadsintervall"}: {statement.headline}</strong></div><div className="mt-0.5 text-xs">{statement.note}</div></div></div>
      </div>
      <div role="img" aria-label={label} className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 12, right: 24, bottom: 18, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1"/>
            <XAxis dataKey="t" type="number" domain={[0, "dataMax"]} tickFormatter={(v: number) => `${Math.round(v)} s`} label={{ value: "Tid sedan körningens start", position: "insideBottom", offset: -8, fontSize: 12 }} fontSize={12}/>
            <YAxis domain={domain ?? ["auto", "auto"]} tickFormatter={tick} width={52} fontSize={12} label={{ value: "Mkr", angle: -90, position: "insideLeft", fontSize: 12 }}/>
            <Tooltip formatter={(v: number, name: string) => [formatKr(v * MKR), name]} labelFormatter={(v: number) => `Efter ${formatDuration(v)}`}/>
            <Line name="Verifierad kostnad" dataKey="upper" type="stepAfter" stroke="#0c4a6e" strokeWidth={2.5} dot={false} connectNulls isAnimationActive={false}/>
            <Line name="Undre gräns" dataKey="lower" type="stepAfter" stroke="#047857" strokeWidth={2.5} strokeDasharray="7 4" dot={false} connectNulls isAnimationActive={false}/>
            {first && <ReferenceDot x={first.t} y={first.cost_ore / MKR} r={6} fill="#b45309" stroke="#ffffff" strokeWidth={2} isFront ifOverflow="extendDomain"/>}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <ul className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-800" aria-label="Teckenförklaring">
        <li className="flex items-center gap-1.5"><svg width="28" height="8" aria-hidden="true"><line x1="0" y1="4" x2="28" y2="4" stroke="#0c4a6e" strokeWidth="3"/></svg>Verifierad kostnad (övre gräns), heldragen linje</li>
        <li className="flex items-center gap-1.5"><svg width="28" height="8" aria-hidden="true"><line x1="0" y1="4" x2="28" y2="4" stroke="#047857" strokeWidth="3" strokeDasharray="7 4"/></svg>Undre gräns (bevisad), streckad linje</li>
        <li className="flex items-center gap-1.5"><svg width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="6" fill="#b45309"/></svg>Första kontrollerade lösning</li>
      </ul>
      {first ? <p className="flex items-start gap-1.5 text-xs text-slate-800"><Flag size={14} className="mt-0.5 shrink-0" aria-hidden="true"/><span>Första kontrollerade lösning efter <strong>{formatDuration(first.t)}</strong>, {formatKr(first.cost_ore)}, från: <strong>{sourceLabel(first.source)}</strong>.</span></p>
        : <p className="text-xs text-slate-800">Ingen kontrollerad lösning har hittats ännu. En placering som inte är kontrollerad räknas inte som lösning.</p>}
      <details className="text-xs"><summary className="cursor-pointer rounded font-medium text-sky-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-700">Visa kostnadshändelser som tabell</summary>
        <table className="mt-2 w-full"><caption className="sr-only">Kontrollerade lösningar och bevisade undre gränser</caption>
          <thead><tr className="text-left text-slate-800"><th scope="col" className="p-1">Tid</th><th scope="col">Händelse</th><th scope="col">Värde</th><th scope="col">Källa / varv</th></tr></thead>
          <tbody>
            {[...state.incumbents.map(p => ({ t: p.t, kind: "Ny verifierad kostnad", value: formatKr(p.cost_ore), extra: `${sourceLabel(p.source)} · ${p.changed_exams} flyttade tentor` })),
              ...state.bounds.map(p => ({ t: p.t, kind: "Ny undre gräns", value: formatKr(p.lower_ore), extra: `varv ${p.round}` }))]
              .sort((a, b) => a.t - b.t).map((row, i) => <tr className="border-t" key={i}><td className="p-1 tabular-nums">{formatDuration(row.t)}</td><td>{row.kind}</td><td className="tabular-nums">{row.value}</td><td>{row.extra}</td></tr>)}
          </tbody></table>
        {!state.incumbents.length && !state.bounds.length && <p className="mt-1 text-slate-800">Inga händelser ännu.</p>}
      </details>
    </CardContent>
  </Card>
}

function Figure({ title, value, hint }: { title: string; value: string; hint: string }) {
  return <div className="rounded-md border p-3"><div className="text-xs text-slate-800">{title}</div><div className="mt-1 text-xl font-semibold tabular-nums">{value}</div><div className="mt-0.5 text-[11px] text-slate-800">{hint}</div></div>
}
