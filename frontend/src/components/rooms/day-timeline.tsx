import { groupByDay, placeBars, timelineScale, toMinutes } from "@/lib/bookingView"
import type { BookingItem, DaySummary } from "@/lib/bookingTypes"
import { weekdayName } from "@/lib/dates"
import { formatMinutes } from "@/lib/bookingView"

type Props = { bookings: BookingItem[]; days: Record<string, DaySummary>; selected: string; onOpen: (item: BookingItem) => void }

const LANE_HEIGHT = 30

/**
 * Tidslinje per dag för en lokal: varje bokning är en stapel från start- till sluttid. Överlappande bokningar ligger i
 * egna rader. Avbokade bokningar visas streckade och räknas inte. Dagar utan bokning visas inte som lediga, eftersom
 * underlaget bara säger vad som var bokat.
 */
export function DayTimeline({ bookings, days, selected, onOpen }: Props) {
  const scale = timelineScale(bookings)
  const hours = Array.from({ length: (scale.to - scale.from) / 60 + 1 }, (_, index) => scale.from / 60 + index)
  const grouped = groupByDay(bookings)
  const untimed = bookings.filter(item => toMinutes(item.start) === null || toMinutes(item.end) === null)
  if (!grouped.length) return <p className="text-sm text-slate-800">Inga bokningar i det här intervallet i underlaget.</p>
  return <div className="space-y-3" aria-label="Tidslinje per dag">
    <div className="ml-28 flex text-[11px] text-slate-700" aria-hidden="true">
      {hours.slice(0, -1).map(hour => <div key={hour} className="flex-1 border-l border-slate-200 pl-0.5">{String(hour).padStart(2, "0")}</div>)}
    </div>
    {grouped.map(([date, rows]) => {
      const { bars, lanes } = placeBars(rows, scale)
      const day = days[date]
      return <div key={date} className="flex gap-2">
        <div className="w-26 shrink-0 text-xs" style={{ width: "6.5rem" }}>
          <div className="font-medium">{date}</div>
          <div className="text-slate-700">{weekdayName(date)}</div>
          {day && <div className="text-slate-700">{formatMinutes(day.booked_minutes)} bokat</div>}
        </div>
        <div className="relative flex-1 rounded border bg-slate-50" style={{ height: lanes * LANE_HEIGHT + 4 }}>
          {hours.slice(1, -1).map(hour => <div key={hour} className="absolute inset-y-0 border-l border-slate-200" style={{ left: `${((hour * 60 - scale.from) / (scale.to - scale.from)) * 100}%` }}/>)}
          {bars.map(({ item, left, width, lane }) => {
            const active = item.placement_id === selected
            return <button key={item.placement_id} type="button" onClick={() => onOpen(item)} aria-pressed={active}
              aria-label={`${item.course_codes} ${item.course_name}, ${item.start}–${item.end}, ${item.booked_places} platser${item.cancelled ? ", avbokad" : ""}`}
              title={`${item.course_codes} ${item.course_name}\n${item.start}–${item.end}, ${item.booked_places} platser${item.cancelled ? "\nAvbokad" : ""}`}
              className={`absolute overflow-hidden whitespace-nowrap rounded border px-1 text-left text-[11px] leading-[22px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-700 ${
                item.cancelled ? "border-dashed border-slate-500 bg-white text-slate-600 line-through" : active ? "border-sky-900 bg-sky-800 text-white" : "border-sky-700 bg-sky-100 text-sky-950 hover:bg-sky-200"}`}
              style={{ left: `${left}%`, width: `${width}%`, top: lane * LANE_HEIGHT + 3, height: LANE_HEIGHT - 6 }}>
              {item.course_codes} · {item.booked_places}
            </button>
          })}
        </div>
      </div>
    })}
    {untimed.length > 0 && <p className="text-xs text-amber-900">{untimed.length} bokningar saknar klockslag och visas bara i tabellen.</p>}
  </div>
}
