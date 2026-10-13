import { useEffect, useId, useState } from "react"
import { TriangleAlert } from "lucide-react"
import { jointApi } from "@/lib/jointApi"
import type { SavedRun } from "@/lib/jointTypes"
import { moveText, placeText } from "@/lib/bookingView"
import { useCompare } from "@/lib/useBookings"

/**
 * Den ursprungliga bokningen bredvid tentamens placering i en vald körning. Bokningen är historisk och orörd; körningen är en
 * simulering. Kopplingen mellan dem (bokning till Ladok-aktivitet) är provisorisk och visas som sådan. Där koppling saknas görs
 * ingen jämförelse.
 */
export function ComparePanel({ orderId }: { orderId: string }) {
  const selectId = useId()
  const [runs, setRuns] = useState<SavedRun[]>([])
  const [runsError, setRunsError] = useState("")
  const [runId, setRunId] = useState("")
  useEffect(() => { jointApi.listRuns().then(setRuns).catch(error => setRunsError((error as Error).message)) }, [])
  const compare = useCompare(orderId, runId)
  const data = compare.data

  return <section aria-label="Jämförelse mot körning" className="space-y-2 border-t pt-3">
    <div><label className="label" htmlFor={selectId}>Jämför med placering i körning</label>
      <select id={selectId} className="field" value={runId} onChange={event => setRunId(event.target.value)}>
        <option value="">Ingen körning vald</option>
        {runs.map(run => <option key={run.run_id} value={run.run_id}>{run.run_id}</option>)}
      </select>
      {runsError && <p role="alert" className="mt-1 text-xs text-red-900">Kunde inte hämta körningar: {runsError}</p>}
      {!runs.length && !runsError && <p className="mt-1 text-xs text-slate-800">Det finns inga sparade körningar att jämföra med.</p>}</div>
    {compare.status === "loading" && <p className="text-sm text-slate-800" role="status">Jämför …</p>}
    {compare.status === "error" && <p role="alert" className="text-sm text-red-900">{compare.error}</p>}
    {data && <div className="space-y-2 text-sm" aria-label="Resultat av jämförelsen">
      {data.status !== "compared" && <p className="rounded-md bg-slate-100 p-2" role="status"><strong>{data.status === "no_link" ? "Ingen koppling." : "Ingår inte i körningen."}</strong> {data.reason}</p>}
      {data.link.unclear && <p className="flex items-start gap-1.5 rounded bg-amber-50 p-2 text-xs text-amber-950"><TriangleAlert size={14} className="mt-0.5 shrink-0" aria-hidden="true"/>
        Kopplingen mellan bokning och Ladok är provisorisk och inte säker ({data.link.texts.join(" ")}).</p>}
      {data.demands.map(demand => <div key={demand.exam_demand_id} className="grid gap-2 rounded-md border p-2 sm:grid-cols-2">
        <div><div className="text-xs font-semibold">Bokning (historisk)</div>
          <ul className="mt-1 space-y-0.5 text-xs">{data.booking.map((item, index) => <li key={index} className={item.status === "Avbokad" ? "line-through text-slate-600" : ""}>
            {item.date ?? "datum saknas"} {item.start && item.end ? `${item.start}–${item.end}` : ""} · {item.label} · {item.booked_places} bokade platser{item.status === "Avbokad" ? " (avbokad)" : ""}</li>)}</ul></div>
        <div><div className="text-xs font-semibold">Körning (simulering) {data.run_id}</div>
          <ul className="mt-1 space-y-0.5 text-xs">
            <li>{demand.simulated ? `${demand.simulated.date} kl. ${demand.simulated.start}` : "ingen tid"}{demand.duration_minutes ? `, ${demand.duration_minutes} min` : ""}</li>
            {demand.simulated_rooms.map(room => <li key={room.room_id}>{room.label} · {room.participants} deltagare</li>)}
            <li className="text-slate-800">{demand.participants} anmälda enligt Ladok{demand.movable ? "" : " (får inte flyttas)"}</li></ul></div>
        <div className="sm:col-span-2 space-y-0.5 border-t pt-1.5 text-xs">
          <p className={demand.moved ? "font-medium text-amber-950" : ""}>{moveText(demand)}</p>
          <p>{placeText(demand)}</p></div>
      </div>)}
      {data.status === "compared" && <p className="text-xs text-slate-800">Körningen: {data.run.outcome ?? "okänt utfall"}{data.run.technical_placement_complete === false ? ", ofullständig placering" : ""}. {data.notes.join(" ")}</p>}
    </div>}
  </section>
}
