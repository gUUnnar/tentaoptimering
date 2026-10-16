import { Notice } from "@/components/ui/notice"
import type { FixedBookings } from "@/lib/precheckApi"
import { actionText, bookingTime, fixedBookingsSummary } from "@/lib/fixedBookingsView"

const TH = "p-1.5 text-left text-xs font-semibold"
const TD = "p-1.5 align-top"

/**
 * Övriga redan lagda bokningar i perioden: varför de inte är tentor i urvalet, vilka salar och tider de tar och vad som ska hända med dem.
 * Valet görs med parametrarna under Lokaler (Behåll fast är förvalet); ett annat val gör körningen till en egen körning (C).
 */
export function FixedBookingsCard({ data }: { data: FixedBookings }) {
  if (data.status !== "read") return <p className="text-xs text-slate-800">{data.note ?? "Övriga bokningar kunde inte läsas, så ingen hänsyn tas till dem."}</p>
  return <div className="space-y-2 rounded-md border p-3" aria-label="Övriga redan lagda bokningar">
    <p className="text-sm font-semibold">Övriga redan lagda bokningar i perioden</p>
    <p className="text-xs">{fixedBookingsSummary(data)}</p>
    <table className="w-full text-xs"><thead><tr className="border-b"><th className={TH}>Orsak</th><th className={`${TH} text-right`}>Bokningar</th><th className={`${TH} text-right`}>Platser</th><th className={TH}>Åtgärd</th></tr></thead>
      <tbody>{data.groups.map(group => <tr key={group.group} className="border-b last:border-0"><td className={TD}><strong>{group.label}</strong><span className="block text-slate-800">{group.why}</span></td>
        <td className={`${TD} text-right tabular-nums`}>{group.bookings}</td><td className={`${TD} text-right tabular-nums`}>{group.booked_places}</td>
        <td className={TD}>{actionText(group.action)}<span className="block text-slate-700">Ändras med parametern ”{group.action_parameter}” under Lokaler.</span></td></tr>)}</tbody></table>
    {data.unidentified_bookings > 0 && <Notice tone="warning" title={`${data.unidentified_bookings} bokningar utan identifierad sal (${data.unidentified_booked_places} platser): okänd upptagenhet`}>
      <p>De anger bara adress eller saknar adress och kan därför inte spärra någon sal. Deras upptagenhet är okänd, inte noll.</p></Notice>}
    {data.bookings.length > 0 && <details><summary className="cursor-pointer text-sm font-medium">Visa bokningarna ({data.bookings.length}{data.truncated ? ", avkortad lista" : ""})</summary>
      <div className="mt-1 max-h-72 overflow-auto"><table className="w-full text-xs"><thead><tr className="border-b"><th className={TH}>Datum</th><th className={TH}>Tid</th><th className={TH}>Sal</th><th className={`${TH} text-right`}>Platser</th><th className={TH}>Kurs</th><th className={TH}>Orsak</th><th className={TH}>Åtgärd</th></tr></thead>
        <tbody>{data.bookings.map(item => <tr key={item.reservation_id} className="border-b last:border-0"><td className={TD}>{item.date}</td><td className={TD}>{bookingTime(item)}</td><td className={TD}>{item.room}</td>
          <td className={`${TD} text-right tabular-nums`}>{item.booked_places}</td><td className={TD}>{item.course}</td><td className={TD}>{data.groups.find(group => group.group === item.group)?.label ?? item.group}</td><td className={TD}>{actionText(item.action)}</td></tr>)}</tbody></table></div></details>}
  </div>
}
