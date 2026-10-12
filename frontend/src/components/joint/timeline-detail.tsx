import type { Timeline } from "@/lib/jointTimeline"
import { previousRoundFailed, segmentDetail } from "@/lib/jointTimelineDetail"
import { BLOCK_STATUS_TEXT } from "./timeline-look"

/** Detaljer om det valda segmentet: tid, hur många dagar som är klara, hur många som misslyckades och vad det ledde till. */
export function TimelineDetail({ timeline, selectedId }: { timeline: Timeline; selectedId: string | null }) {
  const box = "min-h-[3.5rem] rounded-md bg-slate-50 p-2.5 text-xs text-slate-900"
  const block = timeline.blocks.find(item => item.id === selectedId || item.segments.some(segment => segment.id === selectedId))
  const segment = block?.segments.find(item => item.id === selectedId)
  if (!block) return <div className={box} aria-live="polite">Peka på, markera eller klicka ett steg i tidslinjen för tid, antal klara dagar och vad som hände.</div>
  if (!segment) {
    return <div className={box} aria-live="polite">
      <p className="text-sm font-semibold">{block.label}: {BLOCK_STATUS_TEXT[block.status]}</p>
      <p className="mt-0.5">{block.note ?? (block.status === "pending" ? "Steget har inte börjat." : "")}</p>
    </div>
  }
  const detail = segmentDetail(segment, block, previousRoundFailed(timeline, segment.round))
  return <div className={box} aria-live="polite">
    <p className="text-sm font-semibold">{detail.heading}</p>
    <p className="mt-0.5"><strong>{detail.statusText}.</strong> Tid: <span className="tabular-nums">{detail.timeText}</span>.</p>
    <p className="mt-0.5">{detail.help}</p>
    {block.note && <p className="mt-0.5">{block.note}</p>}
    {detail.notes.map(note => <p key={note} className="mt-0.5">{note}</p>)}
    {detail.checks.length > 0 && <ul className="mt-1.5 space-y-1.5">
      {detail.checks.map(check => <li key={check.kind} className="border-t border-slate-200 pt-1">
        <p><strong>{check.title}:</strong> <span className="tabular-nums">{check.counts}</span>.</p>
        <p className="text-slate-800">{check.explanation}</p>
        {check.consequence && <p className="font-medium text-red-900">Det ledde till: {check.consequence}</p>}
      </li>)}
    </ul>}
  </div>
}
