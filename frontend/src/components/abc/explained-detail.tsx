import type { ReactNode } from "react"
import { Badge } from "@/components/ui/badge"
import type { AbcExplained, ExplainedDetail, ExplainedExamChange, ExplainedItem, ExplainedRoom, ExplainedSession } from "@/lib/abcTypes"
import { changeText, examsFor, hours, realizationView, roomNamer, ROOM_STATUS_TEXT, signedCount, signedHours, signedKr, tagText } from "@/lib/abcExplainView"
import { formatKr } from "@/lib/jointFormat"

type Explained = AbcExplained & ExplainedDetail

export const TH = "p-1.5 text-left text-xs font-semibold text-slate-900"
export const TD = "p-1.5 align-top"
const NUM = "p-1.5 text-right align-top tabular-nums"
const TONE = { ok: "bg-emerald-100 text-emerald-950", warn: "bg-amber-100 text-amber-950", bad: "bg-red-100 text-red-950" }

/** Det som förklarar en kostnadspost: berörda lokaler, bokningar, personalpass och de tentor som ändrats. */
export function ItemDetail({ item, explained }: { item: ExplainedItem; explained: Explained }) {
  return <div className="space-y-3 rounded-md border bg-slate-50 p-3" aria-label={`Förklaring av ${item.label}`}>
    {item.drivers.length > 0 && <ul className="list-disc space-y-0.5 pl-5 text-sm">{item.drivers.map(driver => <li key={driver.text}>{driver.text}</li>)}</ul>}
    {item.parts && <PartsTable item={item}/>}
    {item.key === "rooms" && <RoomsTable explained={explained}/>}
    {item.key === "external" && <ExternalBookings explained={explained}/>}
    {item.key === "staff" && <StaffDetail explained={explained}/>}
    <ExamChanges title="Tentor som ändrats och förklarar posten" rows={examsFor(item.key, explained)} explained={explained}/>
  </div>
}

function PartsTable({ item }: { item: ExplainedItem }) {
  return <table className="w-full text-sm"><thead><tr className="border-b"><th className={TH}>Del</th><th className={`${TH} text-right`}>Före</th><th className={`${TH} text-right`}>Efter</th><th className={`${TH} text-right`}>Skillnad</th></tr></thead>
    <tbody>{item.parts?.map(part => <tr key={part.key} className="border-b last:border-0"><td className={TD}>{part.label}</td><td className={NUM}>{formatKr(part.left_ore)}</td>
      <td className={NUM}>{formatKr(part.right_ore)}</td><td className={NUM}>{signedKr(part.difference_ore)}</td></tr>)}</tbody></table>
}

function RoomsTable({ explained }: { explained: Explained }) {
  const realization = new Map(explained.realization.items.map(item => [item.room_id, item.realization]))
  const rows = explained.rooms.filter(room => room.fixed_difference_ore !== 0 || room.status !== "kept" || room.booked_minutes_difference !== 0)
  return <div><p className="mb-1 text-xs font-semibold">Namngivna lokaler: före, efter och skillnad</p>
    {rows.length === 0 ? <p className="text-xs">Alla lokaler används som förut.</p> :
      <div className="max-h-96 overflow-auto"><table className="w-full text-xs"><thead><tr className="border-b"><th className={TH}>Lokal</th><th className={TH}>Läge</th>
        <th className={`${TH} text-right`}>Tillfällen före → efter</th><th className={`${TH} text-right`}>Bokad tid före → efter</th><th className={`${TH} text-right`}>Hyra före</th>
        <th className={`${TH} text-right`}>Hyra efter</th><th className={`${TH} text-right`}>Skillnad</th><th className={TH}>Kan hyran avvecklas?</th></tr></thead>
        <tbody>{rows.map(room => <RoomRow key={room.room_id} room={room} realization={realization.get(room.room_id)} explained={explained}/>)}</tbody></table></div>}
  </div>
}

function RoomRow({ room, realization, explained }: { room: ExplainedRoom; realization?: { status: string; reason: string; contract: { name: string; origin: string } | null }; explained: Explained }) {
  const view = realization ? realizationView(realization.status) : null
  return <tr className="border-b last:border-0">
    <td className={TD}>{room.name}{room.kind === "external" && <Badge className="ml-1">extern</Badge>}{room.reserved_only && <span className="ml-1 text-slate-700" title="Salen används genom en fast bokning utanför de valda tentorna">(fast bokad)</span>}</td>
    <td className={TD}>{ROOM_STATUS_TEXT[room.status]}</td>
    <td className={NUM}>{room.left.sessions} → {room.right.sessions}</td>
    <td className={NUM}>{hours(room.left.booked_minutes)} → {hours(room.right.booked_minutes)}</td>
    <td className={NUM}>{formatKr(room.left.fixed_ore + room.left.external_ore)}</td><td className={NUM}>{formatKr(room.right.fixed_ore + room.right.external_ore)}</td>
    <td className={NUM}>{explained.available ? signedKr(room.difference_ore) : "–"}</td>
    <td className={TD}>{view && realization ? <span><span className={`rounded px-1.5 py-0.5 ${TONE[view.tone]}`}>{view.label}</span>
      <span className="mt-1 block text-slate-800">{realization.reason}</span>{realization.contract && <span className="block text-slate-700">Avtal: {realization.contract.name} ({realization.contract.origin})</span>}</span>
      : room.status === "added" ? "Ökad kostnad, ingen besparing" : "–"}</td></tr>
}

function bookingRow(session: ExplainedSession) {
  return <tr key={`${session.room_id}-${session.date}-${session.start}`} className="border-b last:border-0"><td className={TD}>{session.date}</td><td className={TD}>{session.start}–{session.end}</td>
    <td className={TD}>{session.room}</td><td className={NUM}>{session.participants}</td><td className={TD}>{session.exams.join(", ")}</td><td className={NUM}>{formatKr(session.external_ore)}</td></tr>
}

function BookingList({ title, rows }: { title: string; rows: ExplainedSession[] }) {
  if (rows.length === 0) return null
  return <div><p className="mb-1 text-xs font-semibold">{title}</p><div className="max-h-60 overflow-auto"><table className="w-full text-xs"><thead><tr className="border-b">
    <th className={TH}>Datum</th><th className={TH}>Tid</th><th className={TH}>Lokal</th><th className={`${TH} text-right`}>Tentander</th><th className={TH}>Tentor</th><th className={`${TH} text-right`}>Debitering</th></tr></thead>
    <tbody>{rows.map(bookingRow)}</tbody></table></div></div>
}

function ExternalBookings({ explained }: { explained: Explained }) {
  const { external } = explained.sessions
  return <div className="space-y-2"><p className="text-sm">Externa bokningar: <strong>{external.left}</strong> före, <strong>{external.right}</strong> efter.
    {" "}Undvikta: {formatKr(external.avoided_ore)}. Tillkommande: {formatKr(external.added_ore)}.</p>
    <BookingList title="Externa bokningar som undviks" rows={external.avoided}/><BookingList title="Externa bokningar som tillkommer" rows={external.added}/></div>
}

function SessionRow({ before, after }: { before?: ExplainedSession; after?: ExplainedSession }) {
  const any = (after ?? before) as ExplainedSession
  return <tr className="border-b last:border-0"><td className={TD}>{any.date} {any.start}</td><td className={TD}>{any.room}</td>
    <td className={TD}>{before ? before.exams.join(", ") : "–"} → {after ? after.exams.join(", ") : "–"}</td>
    <td className={NUM}>{before ? `${before.staff} pass, ${hours(before.paid_minutes)}` : "–"}</td><td className={NUM}>{after ? `${after.staff} pass, ${hours(after.paid_minutes)}` : "–"}</td>
    <td className={NUM}>{signedHours((after?.paid_minutes ?? 0) - (before?.paid_minutes ?? 0))}</td></tr>
}

function StaffDetail({ explained }: { explained: Explained }) {
  const { staffing, sessions } = explained
  const rows = [
    ["Betalda pass (vaktpositioner)", staffing.left.passes, staffing.right.passes, signedCount(staffing.difference.passes)],
    ["Betald tid", hours(staffing.left.paid_minutes), hours(staffing.right.paid_minutes), signedHours(staffing.difference.paid_minutes)],
    ["…varav arbetad tid (förberedelse, tentamen, avslut)", hours(staffing.left.worked_minutes), hours(staffing.right.worked_minutes), signedHours(staffing.difference.worked_minutes)],
    ["…varav tillägg till kortaste betalda pass", hours(staffing.left.minimum_top_up_minutes), hours(staffing.right.minimum_top_up_minutes), signedHours(staffing.difference.minimum_top_up_minutes)],
    ["…varav betald restid", hours(staffing.left.travel_minutes), hours(staffing.right.travel_minutes), signedHours(staffing.difference.travel_minutes)],
    ["Vaktpool (samtidiga vakter)", staffing.left.pool, staffing.right.pool, signedCount(staffing.difference.pool)],
  ] as [string, string | number, string | number, string][]
  const changed: { before?: ExplainedSession; after?: ExplainedSession }[] = [
    ...sessions.removed.map(before => ({ before })), ...sessions.added.map(after => ({ after })), ...sessions.changed.map(item => ({ before: item.before, after: item.after }))]
  return <div className="space-y-3">
    <p className="text-xs text-slate-800">{staffing.unit}</p>
    <table className="w-full text-sm"><thead><tr className="border-b"><th className={TH}>Mått</th><th className={`${TH} text-right`}>Före</th><th className={`${TH} text-right`}>Efter</th><th className={`${TH} text-right`}>Skillnad</th></tr></thead>
      <tbody>{rows.map(([label, left, right, diff]) => <tr key={label} className="border-b last:border-0"><td className={TD}>{label}</td><td className={NUM}>{left}</td><td className={NUM}>{right}</td><td className={NUM}>{diff}</td></tr>)}</tbody></table>
    {staffing.per_day.length > 0 && <details><summary className="cursor-pointer text-sm font-medium">Betald tid per dag där den ändras ({staffing.per_day.length} av {staffing.days_compared} dagar)</summary>
      <div className="mt-1 max-h-60 overflow-auto"><table className="w-full text-xs"><thead><tr className="border-b"><th className={TH}>Dag</th><th className={`${TH} text-right`}>Pass före → efter</th><th className={`${TH} text-right`}>Betald tid före → efter</th><th className={`${TH} text-right`}>Skillnad</th></tr></thead>
        <tbody>{staffing.per_day.map(day => <tr key={day.date} className="border-b last:border-0"><td className={TD}>{day.date}</td><td className={NUM}>{day.left_passes} → {day.right_passes}</td>
          <td className={NUM}>{hours(day.left_paid_minutes)} → {hours(day.right_paid_minutes)}</td><td className={NUM}>{signedHours(day.difference_paid_minutes)}</td></tr>)}</tbody></table></div></details>}
    {changed.length > 0 && <details><summary className="cursor-pointer text-sm font-medium">Salstillfällen med ändrade personalpass ({sessions.counts.removed} utgår, {sessions.counts.added} tillkommer, {sessions.counts.changed} ändras)</summary>
      <div className="mt-1 max-h-72 overflow-auto"><table className="w-full text-xs"><thead><tr className="border-b"><th className={TH}>Tid</th><th className={TH}>Lokal</th><th className={TH}>Tentor före → efter</th>
        <th className={`${TH} text-right`}>Före</th><th className={`${TH} text-right`}>Efter</th><th className={`${TH} text-right`}>Skillnad</th></tr></thead>
        <tbody>{changed.map((item, index) => <SessionRow key={index} before={item.before} after={item.after}/>)}</tbody></table></div>
      {sessions.truncated && <p className="text-xs">Listan är avkortad; summorna ovan gäller alla.</p>}</details>}
    {(staffing.observed_staffing.left.length > 0 || staffing.observed_staffing.right.length > 0) && <ObservedStaffing explained={explained}/>}
  </div>
}

function ObservedStaffing({ explained }: { explained: Explained }) {
  const rows = [...explained.staffing.observed_staffing.left, ...explained.staffing.observed_staffing.right]
  return <div className="rounded-md border border-amber-700 bg-amber-50 p-2 text-xs"><p className="font-semibold">Registrerad bemanning i resursdatan (visas skilt från den beräknade)</p>
    <ul className="list-disc pl-5">{rows.map((row, index) => <li key={index}>{row.date}, {row.room_id}: {row.staff_count} vakter{row.paid_minutes ? `, ${hours(row.paid_minutes)}` : ""} – ursprung: {row.origin === "observed" ? "observerad" : row.origin === "simulated" ? "simulerad (inte en observation)" : row.origin}</li>)}</ul></div>
}

/** Tentor som byter datum, klockslag eller sal, med före- och efteruppgifter. */
export function ExamChanges({ title, rows, explained }: { title: string; rows: ExplainedExamChange[]; explained: Explained }) {
  const roomName = roomNamer(explained)
  if (rows.length === 0) return null
  const where = (side: ExplainedExamChange["before"]): ReactNode => <>{side.date} {side.start}<br/>{side.rooms.length ? side.rooms.join(", ") : "–"}</>
  return <details><summary className="cursor-pointer text-sm font-medium">{title} ({rows.length})</summary>
    <div className="mt-1 max-h-80 overflow-auto"><table className="w-full text-xs"><thead><tr className="border-b"><th className={TH}>Tentamen</th><th className={TH}>Före</th><th className={TH}>Efter</th><th className={TH}>Ändrat</th><th className={TH}>Förklarar</th></tr></thead>
      <tbody>{rows.map(row => <tr key={row.exam_event_id} className="border-b last:border-0"><td className={TD}>{row.course ?? row.exam_event_id}{row.participants ? <span className="block text-slate-700">{row.participants} tentander</span> : null}</td>
        <td className={TD}>{where(row.before)}</td><td className={TD}>{where(row.after)}</td><td className={TD}>{row.changes.map(changeText).join(", ")}</td>
        <td className={TD}>{row.tags.map(tag => tagText(tag, roomName)).join("; ") || "–"}</td></tr>)}</tbody></table></div></details>
}
