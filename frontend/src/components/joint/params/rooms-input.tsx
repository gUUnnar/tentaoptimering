import { useId } from "react"
import { TriangleAlert } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { JointOptions, ParameterInfo } from "@/lib/jointTypes"
import { digitalText, groupRooms, groupSummary, roomsDraft, roomSummary, selectedRoomIds, unknownRoomIds } from "@/lib/paramOptions"
import { toDraft } from "@/lib/paramValues"

type Props = { param: ParameterInfo; draft: unknown; onChange: (draft: unknown) => void; disabled: boolean; label: string; describedBy?: string; options: JointOptions }

/** Salar som får användas, som kryssrutor per byggnad. Alla markerade är samma sak som en tom lista (alla salar). */
export function RoomsInput({ param, draft, onChange, disabled, label, describedBy, options }: Props) {
  const id = useId()
  const rooms = options.rooms
  const selected = selectedRoomIds(draft, rooms)
  const summary = roomSummary(rooms, selected)
  const unknown = unknownRoomIds(draft, rooms)
  const groups = groupRooms(rooms)
  const original = toDraft(param)
  const choose = (chosen: string[]) => onChange(roomsDraft(rooms, chosen, original))
  const toggle = (roomId: string) => choose(selected.includes(roomId) ? selected.filter(item => item !== roomId) : [...selected, roomId])
  const setGroup = (ids: string[], on: boolean) => choose(on ? [...new Set([...selected, ...ids])] : selected.filter(item => !ids.includes(item)))

  return <div role="group" aria-label={label} aria-describedby={describedBy} className="space-y-2">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <p role="status" aria-live="polite" className="text-sm font-semibold text-slate-900">{summary.text}</p>
      <div className="flex gap-2">
        <Button type="button" size="sm" variant="outline" disabled={disabled || summary.all} onClick={() => choose(rooms.map(room => room.room_id))}>Markera alla</Button>
        <Button type="button" size="sm" variant="outline" disabled={disabled || summary.none} onClick={() => choose([])}>Avmarkera alla</Button>
      </div>
    </div>
    {summary.none && <p className="flex items-start gap-1.5 text-sm font-medium text-red-800"><TriangleAlert size={16} className="mt-0.5 shrink-0" aria-hidden="true"/>Minst en sal måste vara vald.</p>}
    {!summary.none && !summary.all && <p className="flex items-start gap-1.5 text-xs text-amber-950"><TriangleAlert size={14} className="mt-0.5 shrink-0" aria-hidden="true"/>Borttagna salar kan göra körningen ogenomförbar om de kvarvarande inte rymmer alla tentor. Körningen kontrollerar det och redovisar då vad som saknas.</p>}
    {unknown.length > 0 && <p className="text-xs text-red-800">Sal-id som inte finns i underlaget (tas bort om du ändrar valet): {unknown.join(", ")}.</p>}
    <div className="max-h-[26rem] space-y-2 overflow-y-auto pr-1">
      {groups.map((group, index) => {
        const ids = group.rooms.map(room => room.room_id)
        const titleId = `${id}-g${index}`
        return <div key={group.key} role="group" aria-labelledby={titleId} className="rounded-md border border-slate-300 bg-white p-2">
          <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
            <p id={titleId} className="text-sm font-semibold text-slate-900">{group.title} <span className="font-normal text-slate-800">({groupSummary(group, selected)})</span></p>
            <div className="flex gap-1.5">
              <Button type="button" size="sm" variant="outline" disabled={disabled} aria-label={`Markera alla salar i ${group.title}`} onClick={() => setGroup(ids, true)}>Markera alla</Button>
              <Button type="button" size="sm" variant="outline" disabled={disabled} aria-label={`Avmarkera alla salar i ${group.title}`} onClick={() => setGroup(ids, false)}>Ingen</Button>
            </div>
          </div>
          <ul className="grid gap-x-4 gap-y-0.5 sm:grid-cols-2">
            {group.rooms.map(room => <li key={room.room_id}>
              <label className="flex items-start gap-2 rounded px-1 py-1 text-sm hover:bg-slate-50">
                <input type="checkbox" className="mt-1" checked={selected.includes(room.room_id)} disabled={disabled} onChange={() => toggle(room.room_id)}/>
                <span>
                  <span className="break-all font-mono text-xs font-medium text-slate-900" title={room.label}>{room.room_id}</span>
                  <span className="block text-xs text-slate-800">{room.capacity === null ? "Platser okänt" : `${room.capacity} platser`} · {digitalText(room.digital)}</span>
                </span>
              </label>
            </li>)}
          </ul>
        </div>
      })}
    </div>
  </div>
}
