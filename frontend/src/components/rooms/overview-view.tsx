import { useId } from "react"
import { Info, TriangleAlert } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { AddressEntry, BookingItem } from "@/lib/bookingTypes"
import { formatMinutes, overviewMeasures, percent, rangeError, stepRange, type Range } from "@/lib/bookingView"
import { addDays } from "@/lib/dates"
import { useOverview } from "@/lib/useBookings"
import { DayTimeline } from "./day-timeline"

type Props = {
  range: Range
  onRange: (range: Range) => void
  /** null = alla adresser; "" = bokningar utan adress. */
  address: string | null
  onAddress: (address: string | null) => void
  addresses: AddressEntry[]
  selectedPlacement: string
  onOpen: (item: BookingItem) => void
  onOpenExam: (orderId: string) => void
}

const SPANS: { label: string; days: number }[] = [{ label: "En dag", days: 1 }, { label: "En vecka", days: 7 }, { label: "En månad", days: 28 }]

/**
 * Vilka lokaler som varit bokade under en dag eller period, för vilka tentamina och i vilken omfattning, per adress och sal.
 * Bokningar som bara anger adress ligger kvar under sin adress som "sal ej angiven" och hänförs aldrig till en sal. Läser
 * historiska bokningar direkt; ingen körning behövs.
 */
export function OverviewView({ range, onRange, address, onAddress, addresses, selectedPlacement, onOpen, onOpenExam }: Props) {
  const id = useId()
  const error = rangeError(range)
  const data = useOverview(range, address)
  const result = data.data
  const unnamed = result?.totals.unspecified_room_placements ?? 0

  return <div className="space-y-4">
    <Card><CardContent className="space-y-3 pt-4">
      <div className="flex flex-wrap items-end gap-3">
        <div><label className="label" htmlFor={`${id}-from`}>Från och med</label><input id={`${id}-from`} type="date" className="field" value={range.from} onChange={event => onRange({ ...range, from: event.target.value })}/></div>
        <div><label className="label" htmlFor={`${id}-to`}>Till och med</label><input id={`${id}-to`} type="date" className="field" value={range.to} onChange={event => onRange({ ...range, to: event.target.value })}/></div>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Längd på perioden">
          {SPANS.map(span => <Button key={span.label} type="button" size="sm" variant="outline" disabled={!range.from} onClick={() => onRange({ from: range.from, to: addDays(range.from, span.days - 1) })}>{span.label}</Button>)}
          <Button type="button" size="sm" variant="outline" disabled={!!error} onClick={() => onRange(stepRange(range, -1))} aria-label="Föregående period">←</Button>
          <Button type="button" size="sm" variant="outline" disabled={!!error} onClick={() => onRange(stepRange(range, 1))} aria-label="Nästa period">→</Button>
        </div>
        <div className="min-w-[14rem] flex-1"><label className="label" htmlFor={`${id}-address`}>Adress</label>
          <select id={`${id}-address`} className="field" value={address === null ? "*" : address} onChange={event => onAddress(event.target.value === "*" ? null : event.target.value)}>
            <option value="*">Alla adresser</option>
            {addresses.map(item => <option key={item.address} value={item.address}>{item.label} · {item.bookings} bokningar{item.unspecified_room_bookings ? `, ${item.unspecified_room_bookings} utan sal` : ""}</option>)}
          </select></div>
      </div>
      {error && <p role="alert" className="text-sm text-red-900">{error}</p>}
    </CardContent></Card>

    {data.status === "error" && <p role="alert" className="text-sm text-red-900">{data.error}</p>}
    {data.status === "loading" && !result && <p className="text-sm text-slate-800" role="status">Hämtar bokningar …</p>}
    {result && <>
      {result.notes.filter(note => !note.startsWith("En tentamen som")).map(note => <p key={note} className="flex items-start gap-1.5 rounded-md bg-amber-50 p-2 text-sm text-amber-950"><TriangleAlert size={16} className="mt-0.5 shrink-0" aria-hidden="true"/>{note}</p>)}
      <Card><CardHeader><CardTitle>Bokat {result.date_from} – {result.date_to}{result.address !== null ? ` · ${result.address || "Adress saknas"}` : ""}</CardTitle></CardHeader><CardContent>
        <dl className="grid gap-3 sm:grid-cols-3">
          {overviewMeasures(result.totals, result.measures).map(measure => <div key={measure.label} className="rounded-md border p-2.5">
            <dt className="text-xs text-slate-900">{measure.label}</dt><dd className="mt-0.5 text-base font-semibold tabular-nums">{measure.value}</dd>
            <p className="mt-0.5 text-[11px] text-slate-800">{measure.hint}</p></div>)}
        </dl>
        {unnamed > 0 && <p className="mt-2 flex items-start gap-1.5 text-xs text-slate-900"><Info size={14} className="mt-0.5 shrink-0" aria-hidden="true"/>{unnamed} av {result.totals.placements} bokningsrader anger bara adress. De syns under sin adress som "sal ej angiven" och ingår i alla summor.</p>}
      </CardContent></Card>

      <Card><CardHeader><CardTitle>Lokaler</CardTitle></CardHeader><CardContent>
        {result.addresses.length === 0 ? <p className="text-sm text-slate-800">Inga bokningar i perioden i underlaget. Det betyder inte att lokalerna var lediga.</p> :
          <table className="w-full text-sm"><thead><tr className="text-left text-xs text-slate-700">
            <th className="py-1 pr-2 font-medium">Adress / sal</th><th className="pr-2 text-right font-medium">Tentamina</th><th className="pr-2 text-right font-medium">Rader</th>
            <th className="pr-2 text-right font-medium">Bokad tid</th><th className="pr-2 text-right font-medium">Bokade platser</th><th className="text-right font-medium">Högsta samtidiga</th></tr></thead>
            <tbody>{result.addresses.map(item => [
              <tr key={item.address} className="border-t bg-slate-50 font-medium">
                <td className="py-1 pr-2"><button type="button" onClick={() => onAddress(item.address)} className="text-left text-sky-900 underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-700" title="Visa alla bokningar på adressen">{item.label}</button></td>
                <td className="pr-2 text-right tabular-nums">{item.exam_orders}</td><td className="pr-2 text-right tabular-nums">{item.placements}</td>
                <td className="pr-2 text-right tabular-nums" title={result.measures.booked_time}>{formatMinutes(item.booked_minutes)}</td>
                <td className="pr-2 text-right tabular-nums">{item.booked_places}</td><td className="text-right tabular-nums">{item.peak_places}</td></tr>,
              ...item.rooms.map(room => <tr key={`${item.address}|${room.label}`} className="border-t text-slate-900">
                <td className="py-1 pl-4 pr-2">{room.room ?? "sal ej angiven"}{room.capacity ? <span className="text-xs text-slate-700"> ({room.capacity} platser)</span> : null}</td>
                <td className="pr-2 text-right tabular-nums">{room.exam_orders}</td><td className="pr-2 text-right tabular-nums">{room.placements}</td>
                <td className="pr-2 text-right tabular-nums">{formatMinutes(room.booked_minutes)}</td><td className="pr-2 text-right tabular-nums">{room.booked_places}</td>
                <td className="text-right tabular-nums">{room.peak_places}{room.peak_share_of_capacity !== null ? ` (${percent(room.peak_share_of_capacity)})` : ""}</td></tr>)])}</tbody></table>}
        <p className="mt-2 text-[11px] text-slate-800">{result.notes.find(note => note.startsWith("En tentamen som"))} {result.measures.booked_time}</p>
      </CardContent></Card>

      {result.bookings && <Card><CardHeader><CardTitle>Tidslinje för {result.address || "Adress saknas"}</CardTitle></CardHeader><CardContent>
        <DayTimeline bookings={result.bookings} days={{}} selected={selectedPlacement} onOpen={onOpen}/></CardContent></Card>}

      <Card><CardHeader><CardTitle>Tentamina ({result.exams_total})</CardTitle></CardHeader><CardContent>
        {result.exams.length === 0 ? <p className="text-sm text-slate-800">Inga tentamina i perioden.</p> :
          <ul className="divide-y text-sm">{result.exams.map(exam => <li key={exam.exam_order_id} className="py-1.5">
            <button type="button" onClick={() => onOpenExam(exam.exam_order_id)} className="text-left text-sky-900 underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-700">{exam.course_codes} {exam.course_name}</button>
            <span className="text-xs text-slate-700"> · {exam.first_date}{exam.last_date !== exam.first_date ? `–${exam.last_date}` : ""} · {exam.booked_places} platser</span>
            <span className="block text-xs text-slate-800">{exam.places.map(place => `${place.label} (${place.booked_places})`).join("; ")}</span></li>)}</ul>}
        {result.exams_truncated && <p className="mt-1 text-xs text-slate-800">De {result.exams.length} första av {result.exams_total} visas. Välj en kortare period eller en adress för att se resten.</p>}
      </CardContent></Card>
    </>}
  </div>
}
