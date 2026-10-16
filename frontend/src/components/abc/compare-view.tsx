import { useMemo, type ReactNode } from "react"
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { InfoTip } from "@/components/ui/info-tip"
import { Notice } from "@/components/ui/notice"
import type { AbcCompare, AbcHeader, AbcRoomUsage, AbcUnplaced } from "@/lib/abcTypes"
import { costSideText, percentOf, utilizationSeries } from "@/lib/abcView"
import { changeRows } from "@/lib/jointCompare"
import { formatKr } from "@/lib/jointFormat"
import { ExplainedSavings } from "./explained-savings"

const number = new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 0 })
const DASH = "–"
const n = (value: number | null | undefined) => value === null || value === undefined ? DASH : number.format(value)
const signed = (value: number | null) => value === null ? DASH : value > 0 ? `+${number.format(value)}` : number.format(value)
const share = (value: number | null) => value === null ? DASH : `${Math.round(value * 100)} %`

const TH = "p-1.5 text-left text-xs font-semibold text-slate-900"
const TD = "p-1.5 align-top"

/** Jämförelse av två alternativ (A, B eller C). Det som inte går att jämföra sägs, det beräknas inte. */
export function CompareView({ result }: { result: AbcCompare }) {
  const changes = useMemo(() => changeRows(result.parameter_changes), [result.parameter_changes])
  const series = useMemo(() => utilizationSeries(result.utilization.left, result.utilization.right), [result.utilization])
  return <div className="space-y-4">
    <div className="grid gap-3 md:grid-cols-2"><Side header={result.left} title="Vänster (referens)"/><Side header={result.right} title="Höger (jämfört mot vänster)"/></div>
    {result.reasons.length > 0 && <Notice tone="warning" title={result.comparable ? "Jämförelsen har begränsningar" : "Jämförelsen går inte att göra fullt ut"} open>
      <ul className="list-disc pl-5">{result.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul></Notice>}

    {result.explained && <ExplainedSavings explained={result.explained}/>}

    <Section title="Nyckeltal" tip="Antal tentamina och salar, och vaktpoolen för körningar. Den faktiska bokningen har ingen vaktpool i underlaget.">
      <table className="w-full text-sm"><thead><tr className="border-b"><th className={TH}>Mått</th><th className={`${TH} text-right`}>{result.left.name}</th><th className={`${TH} text-right`}>{result.right.name}</th><th className={`${TH} text-right`}>Skillnad</th></tr></thead>
        <tbody>{result.metrics.map(row => <tr key={row.key} className="border-b last:border-0"><td className={TD}>{row.label}</td>
          <td className={`${TD} text-right tabular-nums`}>{n(row.left)}</td><td className={`${TD} text-right tabular-nums`}>{n(row.right)}</td><td className={`${TD} text-right tabular-nums`}>{signed(row.delta)}</td></tr>)}</tbody></table>
    </Section>

    <Section title="Verksamhetens önskemål" tip="Hur många tentamina som ligger på önskat datum, reservdatum 1, reservdatum 2 eller ett annat datum. Önskemålen är bara datum; klockslag anges inte i underlaget.">
      <table className="w-full text-sm"><thead><tr className="border-b"><th className={TH}>Datum</th><th className={`${TH} text-right`}>{result.left.name}</th><th className={`${TH} text-right`}>{result.right.name}</th></tr></thead>
        <tbody>{result.wish_distribution.map(row => <tr key={row.key} className="border-b last:border-0"><td className={TD}>{row.label}</td>
          <td className={`${TD} text-right tabular-nums`}>{n(row.left)}{pct(row.left, result.left.scope.exam_count)}</td>
          <td className={`${TD} text-right tabular-nums`}>{n(row.right)}{pct(row.right, result.right.scope.exam_count)}</td></tr>)}</tbody></table>
    </Section>

    {result.changes && <Section title="Ändrad tid eller sal" tip={result.changes.note}>
      <p className="text-sm">Av {n(result.changes.compared)} jämförda tentamina: <strong>{n(result.changes.unchanged)}</strong> oförändrade, <strong>{n(result.changes.time_changed)}</strong> med ändrat datum eller starttid,
        {" "}<strong>{n(result.changes.room_changed)}</strong> med ändrad sal. Salbyte kan inte avgöras för {n(result.changes.rooms_not_comparable)} (saknad sal i bokningen eller sal utanför lokalregistret).</p>
      {result.changes.list.length > 0 && <details className="mt-2"><summary className="cursor-pointer text-sm font-medium">Visa ändrade tentamina ({result.changes.list_truncated ? `de första ${result.changes.list.length}` : result.changes.list.length})</summary>
        <div className="mt-2 max-h-80 overflow-auto"><table className="w-full text-xs"><thead><tr className="border-b"><th className={TH}>Tentamen</th><th className={TH}>Vänster</th><th className={TH}>Höger</th></tr></thead>
          <tbody>{result.changes.list.map(item => <tr key={item.exam_event_id} className="border-b last:border-0">
            <td className={TD}>{item.course ?? item.exam_event_id}</td><td className={TD}>{item.left.date} {item.left.start}<br/>{item.left.rooms.join(", ") || DASH}</td>
            <td className={TD}>{item.right.date} {item.right.start}<br/>{item.right.rooms.join(", ") || DASH}</td></tr>)}</tbody></table></div></details>}
    </Section>}

    <Section title="Kostnad" tip="Historisk kostnad, modellberäknad kostnad och teoretisk skillnad är olika saker och blandas aldrig.">
      <div className="grid gap-3 md:grid-cols-2">{[result.cost.left, result.cost.right].map((side, index) => {
        const text = costSideText(side)
        return <div key={index} className="rounded-md border p-3"><p className="text-xs font-semibold">{text.kindLabel}</p><p className="text-lg font-bold">{text.value}</p>
          {side.kind === "model" && side.available && side.components.length > 0 && <ul className="mt-1 text-xs">{side.components.map(item => <li key={item.key}>{item.label}: {formatKr(item.ore)}</li>)}</ul>}
          {text.note && <p className="mt-1 text-xs text-slate-800">{text.note}</p>}</div>
      })}</div>
      {result.cost.model_difference && <p className="mt-2 text-sm"><strong>{formatKr(result.cost.model_difference.ore)}</strong> – {result.cost.model_difference.label}.</p>}
      {result.cost.interpretation && <p className="mt-2 text-sm">{result.cost.interpretation}</p>}
      {result.cost.savings_requirements.length > 0 && <div className="mt-2 rounded-md bg-slate-50 p-3 text-sm"><p className="font-semibold">Vad skulle behöva förändras för att kostnaden ska kunna minska?</p>
        <ul className="list-disc pl-5">{result.cost.savings_requirements.map(item => <li key={item}>{item}</li>)}</ul></div>}
    </Section>

    <Section title="Lokalutnyttjande" tip="Per sal: antal tillfällen, tid i bruk (överlapp räknas en gång), högsta samtidiga antal platser och dess andel av känd kapacitet. A visar bokade platser, körningar tilldelade tentander.">
      <div className="grid gap-4 lg:grid-cols-2"><RoomTable title={result.left.name} rows={result.rooms.left}/><RoomTable title={result.right.name} rows={result.rooms.right}/></div>
      {(result.rooms.only_left.length > 0 || result.rooms.only_right.length > 0) && <p className="mt-2 text-xs text-slate-800">
        Bara vänster: {result.rooms.only_left.join(", ") || DASH}. Bara höger: {result.rooms.only_right.join(", ") || DASH}.</p>}
    </Section>

    {series.length > 0 && <Section title="Kapacitetsutnyttjande över tid" tip="Högsta samtidiga antal platser en dag i salar med känd kapacitet, i procent av de salarnas kapacitet. Salar utan känd kapacitet ingår inte. Över 100 % betyder att bokningen avviker från registrets kapacitet.">
      <div role="img" aria-label="Kapacitetsutnyttjande per dag" className="h-64"><ResponsiveContainer width="100%" height="100%">
        <LineChart data={series} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}><CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1"/>
          <XAxis dataKey="date" fontSize={11} minTickGap={24}/><YAxis tickFormatter={(v: number) => `${Math.round(v * 100)} %`} fontSize={11} width={48}/>
          <Tooltip formatter={(v: number, name: string) => [share(v), name]}/><Legend/>
          <Line name={result.left.name} dataKey="left" stroke="#0c4a6e" strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false}/>
          <Line name={result.right.name} dataKey="right" stroke="#b45309" strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false}/></LineChart></ResponsiveContainer></div>
    </Section>}

    {(result.unplaced.left.length > 0 || result.unplaced.right.length > 0) && <Section title="Tentamina som inte placeras" tip="Orsaken är den som körningen eller bokningen själv registrerade. Inget har gissats.">
      <div className="grid gap-3 md:grid-cols-2"><Unplaced title={result.left.name} items={result.unplaced.left}/><Unplaced title={result.right.name} items={result.unplaced.right}/></div></Section>}

    <Section title="Parametrar som skiljer" tip="Bara parametrar som har olika värden i de två körningarna.">
      {result.parameter_note && <p className="text-sm">{result.parameter_note}</p>}
      {!result.parameter_note && (changes.length === 0 ? <p className="text-sm">Inga parametrar skiljer: körningarna har samma inställningar.</p> :
        <table className="w-full text-sm"><thead><tr className="border-b"><th className={TH}>Parameter</th><th className={TH}>Vänster</th><th className={TH}>Höger</th></tr></thead>
          <tbody>{changes.map(row => <tr key={row.id} className="border-b last:border-0"><td className={TD}>{row.label}</td><td className={TD}>{row.oldText}</td><td className={TD}>{row.newText}</td></tr>)}</tbody></table>)}
    </Section>

    {result.notes.length > 0 && <Notice tone="warning" title={`Datakvalitet och begränsningar (${result.notes.length})`}><ul className="list-disc pl-5">{result.notes.map(note => <li key={note}>{note}</li>)}</ul></Notice>}
  </div>
}

const pct = (value: number | null, total: number | undefined) => {
  const p = percentOf(value, total)
  return p === null ? "" : ` (${p} %)`
}

function Side({ header, title }: { header: AbcHeader; title: string }) {
  return <Card><CardContent className="space-y-1 pt-4">
    <p className="text-xs text-slate-800">{title}</p>
    <p className="flex flex-wrap items-center gap-2 font-semibold"><Badge className="bg-sky-100 text-sky-950">{header.kind}</Badge>{header.name}</p>
    <p className="text-xs text-slate-800">{n(header.scope.exam_count)} tentamina{header.scope.participants ? `, ${n(header.scope.participants)} tentander` : ""}</p>
    {!header.available && <p className="text-xs text-red-900">{header.unavailable_reason}</p>}
    {header.stale && !header.stale.current && <p className="text-xs text-amber-900">{header.stale.reason}</p>}
  </CardContent></Card>
}

function Section({ title, tip, children }: { title: string; tip: string; children: ReactNode }) {
  return <Card><CardHeader><CardTitle className="flex items-center gap-1.5">{title}<InfoTip label={`Om ${title}`}>{tip}</InfoTip></CardTitle></CardHeader><CardContent>{children}</CardContent></Card>
}

function RoomTable({ title, rows }: { title: string; rows: AbcRoomUsage[] }) {
  return <div><p className="mb-1 text-sm font-semibold">{title}</p>
    {rows.length === 0 ? <p className="text-xs text-slate-800">Ingen lokalanvändning att visa.</p> :
      <div className="max-h-72 overflow-auto"><table className="w-full text-xs"><thead><tr className="border-b"><th className={TH}>Plats</th><th className={`${TH} text-right`}>Kap.</th><th className={`${TH} text-right`}>Tillf.</th><th className={`${TH} text-right`}>Tid (h)</th><th className={`${TH} text-right`}>Topp</th><th className={`${TH} text-right`}>Andel</th></tr></thead>
        <tbody>{rows.map(row => <tr key={row.label} className="border-b last:border-0"><td className={TD}>{row.label}{!row.in_model_register && row.kind !== "address_only" && <span className="ml-1 text-amber-900" title="Finns inte i lokalregistrets kapacitetsuppgifter">*</span>}</td>
          <td className={`${TD} text-right tabular-nums`}>{n(row.capacity)}</td><td className={`${TD} text-right tabular-nums`}>{n(row.sessions)}</td><td className={`${TD} text-right tabular-nums`}>{(row.booked_minutes / 60).toFixed(1).replace(".", ",")}</td>
          <td className={`${TD} text-right tabular-nums`}>{n(row.peak_seats)}</td><td className={`${TD} text-right tabular-nums`}>{share(row.peak_share)}</td></tr>)}</tbody></table></div>}
  </div>
}

function Unplaced({ title, items }: { title: string; items: AbcUnplaced[] }) {
  return <div><p className="mb-1 text-sm font-semibold">{title}</p>{items.length === 0 ? <p className="text-xs">Alla tentamina placeras.</p> :
    <ul className="max-h-60 list-disc space-y-1 overflow-auto pl-5 text-xs">{items.slice(0, 50).map((item, index) => <li key={`${item.exam_event_id}-${index}`}>{item.exam_event_id ?? item.applies_to}: {item.reason}</li>)}
      {items.length > 50 && <li>… och {items.length - 50} till</li>}</ul>}</div>
}
