import { useEffect, useId, useState } from "react"
import { ChevronLeft, ChevronRight, CircleAlert, Info, TriangleAlert } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { BookingItem } from "@/lib/bookingTypes"
import { defaultRange, flagList, linkIsShown, linkIsUnclear, linkLabel, rangeError, stepRange, summaryMeasures, type Range } from "@/lib/bookingView"
import { addDays } from "@/lib/dates"
import { useLocation, useLocations } from "@/lib/useBookings"
import { DayTimeline } from "./day-timeline"
import { ExamPanel } from "./exam-panel"
import { Findings } from "./findings"
import { OverviewView } from "./overview-view"

/**
 * Lokaler och bokningar: välj en lokal och ett datumintervall och se vad som var bokat, och öppna en tentamen för att se
 * alla dess lokaler och tider. Läser historiska bokningar direkt ur underlaget; ingen optimeringskörning behövs och inget
 * här ändras. Bokat är inte detsamma som verklig närvaro, och dagar utan bokning är inte "lediga".
 */
export default function RoomsPage({ reloadKey }: { reloadKey?: unknown }) {
  const selectId = useId()
  const locations = useLocations(reloadKey)
  const [locationKey, setLocationKey] = useState("")
  const [range, setRange] = useState<Range>({ from: "", to: "" })
  const [orderId, setOrderId] = useState("")
  const [placementId, setPlacementId] = useState("")
  const [view, setView] = useState<"room" | "period">("room")
  const [overviewRange, setOverviewRange] = useState<Range>({ from: "", to: "" })
  const [address, setAddress] = useState<string | null>(null)
  const data = useLocation(locationKey, range)

  const list = locations.data?.locations ?? []
  const current = list.find(item => item.location_key === locationKey)
  useEffect(() => {
    if (!list.length || locationKey) return
    const first = list.find(item => item.room) ?? list[0]
    setLocationKey(first.location_key); setRange(defaultRange(first))
  }, [list, locationKey])
  const coverageFirst = locations.data?.coverage.first
  useEffect(() => { if (coverageFirst && !overviewRange.from) setOverviewRange({ from: coverageFirst, to: addDays(coverageFirst, 6) }) }, [coverageFirst, overviewRange.from])

  const choose = (key: string) => {
    const next = list.find(item => item.location_key === key)
    if (!next) return
    setLocationKey(key); setRange(defaultRange(next)); setPlacementId("")
  }
  const open = (item: BookingItem) => { setPlacementId(item.placement_id); setOrderId(item.exam_order_id) }
  const error = rangeError(range)
  const result = data.data

  if (locations.status === "error") return <p role="alert" className="flex items-start gap-1.5 text-sm text-red-900"><CircleAlert size={16} className="mt-0.5 shrink-0" aria-hidden="true"/>{locations.error}</p>
  return <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_26rem]">
    <div className="min-w-0 space-y-4">
      <div className="flex gap-1.5" role="group" aria-label="Vy">
        <Button type="button" size="sm" variant={view === "room" ? "default" : "outline"} aria-pressed={view === "room"} onClick={() => setView("room")}>En lokal</Button>
        <Button type="button" size="sm" variant={view === "period" ? "default" : "outline"} aria-pressed={view === "period"} onClick={() => setView("period")}>Dag eller period, per adress</Button>
      </div>
      {view === "period" ? <OverviewView range={overviewRange} onRange={setOverviewRange} address={address} onAddress={setAddress} addresses={locations.data?.addresses ?? []}
        selectedPlacement={placementId} onOpen={open} onOpenExam={id => { setOrderId(id); setPlacementId("") }}/> : <>
      <Card><CardContent className="space-y-3 pt-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[18rem] flex-1"><label className="label" htmlFor={selectId}>Lokal</label>
            <select id={selectId} className="field" value={locationKey} onChange={event => choose(event.target.value)} disabled={!list.length}>
              {!list.length && <option value="">{locations.status === "loading" ? "Hämtar lokaler …" : "Inga lokaler i underlaget"}</option>}
              {list.map(item => <option key={item.location_key} value={item.location_key}>{item.label}{item.capacity ? ` (${item.capacity} platser)` : ""} · {item.bookings} bokningar</option>)}
            </select></div>
          <div><label className="label" htmlFor={`${selectId}-from`}>Från och med</label><input id={`${selectId}-from`} type="date" className="field" value={range.from} onChange={event => setRange({ ...range, from: event.target.value })}/></div>
          <div><label className="label" htmlFor={`${selectId}-to`}>Till och med</label><input id={`${selectId}-to`} type="date" className="field" value={range.to} onChange={event => setRange({ ...range, to: event.target.value })}/></div>
          <div className="flex gap-1.5">
            <Button type="button" size="sm" variant="outline" disabled={!!error} onClick={() => setRange(stepRange(range, -1))} aria-label="Föregående intervall"><ChevronLeft size={14} aria-hidden="true"/></Button>
            <Button type="button" size="sm" variant="outline" disabled={!!error} onClick={() => setRange(stepRange(range, 1))} aria-label="Nästa intervall"><ChevronRight size={14} aria-hidden="true"/></Button>
          </div>
        </div>
        {error && <p role="alert" className="text-sm text-red-900">{error}</p>}
        {locations.data && <p className="flex items-start gap-1.5 text-xs text-slate-900"><Info size={14} className="mt-0.5 shrink-0" aria-hidden="true"/>
          <span>Bokningsunderlaget täcker {locations.data.coverage.first}–{locations.data.coverage.last} ({locations.data.coverage.rows} rader, {locations.data.coverage.cancelled} avbokade{locations.data.coverage.without_date ? `, ${locations.data.coverage.without_date} utan datum` : ""}). Det är historiska bokningar, ingen simulering.</span></p>}
        {current?.identification === "address_only" && <p className="flex items-start gap-1.5 text-xs text-amber-900"><TriangleAlert size={14} className="mt-0.5 shrink-0" aria-hidden="true"/>Bokningarna anger bara adressen (sal saknas i uttaget). Orsaken är okänd och ingen sal har antagits, så platserna sätts inte mot någon salskapacitet.</p>}
      </CardContent></Card>

      {data.status === "error" && <p role="alert" className="text-sm text-red-900">{data.error}</p>}
      {data.status === "loading" && !result && <p className="text-sm text-slate-800" role="status">Hämtar bokningar …</p>}
      {result && <>
        {result.notes.map(note => <p key={note} className="flex items-start gap-1.5 rounded-md bg-amber-50 p-2 text-sm text-amber-950"><TriangleAlert size={16} className="mt-0.5 shrink-0" aria-hidden="true"/>{note}</p>)}
        <Card><CardHeader><CardTitle>Bokat {result.date_from} – {result.date_to}</CardTitle></CardHeader><CardContent>
          <dl className="grid gap-3 sm:grid-cols-3">
            {summaryMeasures(result.summary, result.measures).map(measure => <div key={measure.label} className="rounded-md border p-2.5">
              <dt className="text-xs text-slate-900">{measure.label}</dt><dd className="mt-0.5 text-base font-semibold tabular-nums">{measure.value}</dd>
              <p className="mt-0.5 text-[11px] text-slate-800">{measure.hint}</p></div>)}
          </dl></CardContent></Card>
        <Findings quality={result.data_quality}/>
        <Card><CardHeader><CardTitle>Tidslinje</CardTitle></CardHeader><CardContent>
          <DayTimeline bookings={result.bookings} days={result.days} selected={placementId} onOpen={open}/></CardContent></Card>
        <Card><CardHeader><CardTitle>Bokningar ({result.bookings.length})</CardTitle></CardHeader><CardContent>
          {result.bookings.length === 0 ? <p className="text-sm text-slate-800">Inga bokningar i intervallet.</p> :
            <table className="w-full text-sm"><thead><tr className="text-left text-xs text-slate-700">
              <th className="py-1 pr-2 font-medium">Datum</th><th className="pr-2 font-medium">Tid</th><th className="pr-2 font-medium">Tentamen</th><th className="pr-2 text-right font-medium">Platser</th><th className="font-medium">Status</th></tr></thead>
              <tbody>{result.bookings.map(item => <tr key={item.placement_id} className={`border-t ${item.cancelled ? "text-slate-600" : ""} ${item.placement_id === placementId ? "bg-sky-50" : ""}`}>
                <td className="py-1 pr-2">{item.date ?? "saknas"}</td><td className="pr-2">{item.start && item.end ? `${item.start}–${item.end}` : "saknas"}</td>
                <td className="pr-2"><button type="button" onClick={() => open(item)} className="text-left text-sky-900 underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-700">{item.course_codes} {item.course_name}</button>
                  {linkIsShown(item.link_certainty) && <span className={`ml-1.5 rounded px-1 text-[11px] ${linkIsUnclear(item.link_certainty) ? "bg-amber-100 text-amber-950" : "bg-slate-100 text-slate-800"}`} title={item.link_text}>{linkLabel(item.link_certainty)}</span>}</td>
                <td className="pr-2 text-right tabular-nums">{item.booked_places}{item.capacity ? ` av ${item.capacity}` : ""}</td><td>{item.status}</td></tr>)}</tbody></table>}
        </CardContent></Card>
      </>}
      </>}
    </div>
    <Card className="h-fit"><CardHeader><CardTitle>Tentamensbokning</CardTitle></CardHeader><CardContent><ExamPanel orderId={orderId} onSelect={id => { setOrderId(id); setPlacementId("") }}/></CardContent></Card>
  </div>
}
