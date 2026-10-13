import { useState } from "react"
import { CircleAlert, Search, TriangleAlert } from "lucide-react"
import { Button } from "@/components/ui/button"
import { linkIsUnclear, linkLabel } from "@/lib/bookingView"
import { useExam, useExamSearch } from "@/lib/useBookings"

type Props = { orderId: string; onSelect: (orderId: string) => void }

/** Sök en bokad tentamen på id, kurskod eller kursnamn och se alla dess salar, tider och bokade platser. */
export function ExamPanel({ orderId, onSelect }: Props) {
  const [text, setText] = useState("")
  const [submitted, setSubmitted] = useState("")
  const search = useExamSearch(submitted, null)
  const exam = useExam(orderId)
  return <section aria-label="Tentamensbokning" className="space-y-3">
    <form className="flex items-end gap-2" onSubmit={event => { event.preventDefault(); setSubmitted(text) }}>
      <div className="flex-1"><label className="label" htmlFor="exam-search">Sök tentamen (id, kurskod eller kursnamn)</label>
        <input id="exam-search" className="field" value={text} onChange={event => setText(event.target.value)} placeholder="till exempel 1BA103"/></div>
      <Button type="submit" size="sm" variant="outline" disabled={!text.trim()}><Search size={14} className="mr-1" aria-hidden="true"/>Sök</Button>
    </form>
    {search.status === "error" && <p role="alert" className="flex items-start gap-1.5 text-sm text-red-900"><CircleAlert size={16} className="mt-0.5 shrink-0" aria-hidden="true"/>{search.error}</p>}
    {search.status === "ready" && search.data && <div role="status">
      <p className="text-xs text-slate-800">{search.data.total === 0 ? "Inga bokade tentamina hittades." : `${search.data.total} bokade tentamina${search.data.truncated ? ` (de ${search.data.exams.length} första visas)` : ""}.`}</p>
      <ul className="mt-1 max-h-56 divide-y overflow-auto rounded border text-sm">
        {search.data.exams.map(hit => <li key={hit.exam_order_id}>
          <button type="button" onClick={() => onSelect(hit.exam_order_id)} aria-pressed={hit.exam_order_id === orderId}
            className={`block w-full px-2 py-1.5 text-left hover:bg-slate-100 ${hit.exam_order_id === orderId ? "bg-sky-50" : ""}`}>
            <span className="font-medium">{hit.course_codes}</span> {hit.course_name}
            <span className="block text-xs text-slate-700">{hit.first_date}{hit.last_date !== hit.first_date ? `–${hit.last_date}` : ""} · {hit.rooms} {hit.rooms === 1 ? "lokal" : "lokaler"} · {hit.booked_places} platser{hit.all_cancelled ? " · avbokad" : ""} · id {hit.exam_order_id}</span>
          </button></li>)}
      </ul>
    </div>}
    {orderId && exam.status === "loading" && <p className="text-sm text-slate-800" role="status">Hämtar bokningen …</p>}
    {orderId && exam.status === "error" && <p role="alert" className="text-sm text-red-900">{exam.error}</p>}
    {exam.status === "ready" && exam.data && <div className="space-y-2 rounded-md border p-3" aria-label="Vald tentamensbokning">
      <div><div className="text-sm font-semibold">{exam.data.course_codes} {exam.data.course_name}</div>
        <div className="text-xs text-slate-800">{exam.data.exam_type || "Typ saknas"} · id {exam.data.exam_order_id} · {exam.data.booked_places} bokade platser i {exam.data.rooms} {exam.data.rooms === 1 ? "lokal" : "lokaler"}</div></div>
      <table className="w-full text-sm">
        <thead><tr className="text-left text-xs text-slate-700"><th className="py-1 pr-2 font-medium">Datum</th><th className="pr-2 font-medium">Tid</th><th className="pr-2 font-medium">Lokal</th><th className="pr-2 text-right font-medium">Platser</th><th className="font-medium">Status</th></tr></thead>
        <tbody>{exam.data.placements.map(item => <tr key={item.placement_id} className={`border-t ${item.cancelled ? "text-slate-600 line-through" : ""}`}>
          <td className="py-1 pr-2">{item.date ?? "saknas"}</td><td className="pr-2">{item.start && item.end ? `${item.start}–${item.end}` : "saknas"}</td>
          <td className="pr-2">{item.room ? `${item.address} – ${item.room}` : item.address ? `${item.address} (sal ej angiven)` : "saknas"}</td>
          <td className="pr-2 text-right tabular-nums">{item.booked_places}{item.capacity ? ` av ${item.capacity}` : ""}</td><td>{item.status}</td></tr>)}</tbody>
      </table>
      {exam.data.ladok_link_unclear && <p className="flex items-start gap-1.5 rounded bg-amber-50 p-2 text-xs text-amber-950"><TriangleAlert size={14} className="mt-0.5 shrink-0" aria-hidden="true"/>
        Kopplingen till Ladok är inte säker: {[...new Set(exam.data.placements.filter(item => linkIsUnclear(item.ladok_link)).map(item => linkLabel(item.ladok_link)))].join(", ").toLowerCase()}. Den visas här i stället för att gissas.</p>}
      <p className="text-xs text-slate-800">{exam.data.attendance.note} {exam.data.simulated_note}</p>
    </div>}
  </section>
}
