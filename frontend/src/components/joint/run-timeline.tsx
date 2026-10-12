import { useMemo, useState } from "react"
import { ChevronDown, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { formatDuration } from "@/lib/jointFormat"
import { STEP_INFO, STEP_ORDER } from "@/lib/jointSteps"
import { buildTimeline, type Timeline, type TimelineBlock, type TimelineSegment } from "@/lib/jointTimeline"
import type { JointEvent } from "@/lib/jointTypes"
import { BLOCK_STATUS_TEXT, BlockStatusIcon, STEP_LOOK } from "./timeline-look"
import { TimelineDetail } from "./timeline-detail"

const FOCUS = "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700"

function SegmentButton({ segment, block, selected, onSelect }: { segment: TimelineSegment; block: TimelineBlock; selected: boolean; onSelect: () => void }) {
  const look = STEP_LOOK[segment.step]
  const info = STEP_INFO[segment.step]
  const running = segment.status === "running"
  const failed = segment.failedDates.length
  const label = `${block.round !== null ? `${block.label}, ` : ""}${info.label}: ${formatDuration(segment.seconds)}, ${running ? "pågår" : segment.status === "stopped" ? "avbröts" : "klar"}${failed ? `, ${failed} ${failed === 1 ? "dag" : "dagar"} gick inte` : ""}`
  return <div className="flex min-w-0 flex-col" style={{ flexGrow: segment.share, flexBasis: 0, minWidth: "2.75rem" }}>
    <span className="flex h-4 items-center gap-0.5 text-[11px] font-bold leading-4 text-sky-900" aria-hidden={!running}>{running && <><ChevronDown size={12} aria-hidden="true"/>Nu</>}</span>
    <button type="button" title={label} aria-label={label} aria-pressed={selected} onMouseEnter={onSelect} onFocus={onSelect} onClick={onSelect}
      className={cn("flex h-16 w-full flex-col items-start justify-between overflow-hidden rounded-md border-2 p-1 text-left text-[11px] leading-tight", FOCUS, look.box,
        running && "animate-pulse motion-reduce:animate-none", segment.status === "stopped" && "border-dashed", selected && "ring-2 ring-slate-900")}>
      <span className="flex w-full items-center gap-1 font-semibold"><look.Icon size={13} className="shrink-0" aria-hidden="true"/><span className="truncate">{info.short}</span></span>
      <span className="tabular-nums">{formatDuration(segment.seconds)}</span>
      {failed > 0 && <span className="flex items-center gap-0.5 font-semibold text-red-900"><X size={12} aria-hidden="true"/>{failed}</span>}
    </button>
  </div>
}

function Placeholder({ block, selected, onSelect }: { block: TimelineBlock; selected: boolean; onSelect: () => void }) {
  const label = `${block.label}: ${BLOCK_STATUS_TEXT[block.status]}${block.note ? `. ${block.note}` : ""}`
  return <div className="flex min-w-0 flex-1 flex-col"><span className="h-4"/>
    <button type="button" title={label} aria-label={label} aria-pressed={selected} onMouseEnter={onSelect} onFocus={onSelect} onClick={onSelect}
      className={cn("flex h-16 w-full flex-col items-start justify-between overflow-hidden rounded-md border-2 border-dashed border-slate-400 bg-white p-1 text-left text-[11px] leading-tight text-slate-900", FOCUS, selected && "ring-2 ring-slate-900")}>
      <span className="flex items-center gap-1 font-semibold"><BlockStatusIcon status={block.status} size={13}/>{BLOCK_STATUS_TEXT[block.status]}</span>
    </button>
  </div>
}

function Legend() {
  return <section aria-label="Teckenförklaring: vad varje steg gör">
    <h4 className="text-xs font-semibold">Vad varje steg gör</h4>
    <ul className="mt-1 grid gap-x-4 gap-y-1.5 text-xs text-slate-900 sm:grid-cols-2 xl:grid-cols-3">
      {STEP_ORDER.map(step => {
        const look = STEP_LOOK[step]
        return <li key={step} className="flex items-start gap-1.5">
          <span className={cn("mt-0.5 inline-flex shrink-0 items-center gap-1 rounded border px-1 py-0.5 font-semibold", look.box)}><look.Icon size={12} aria-hidden="true"/>{STEP_INFO[step].short}</span>
          <span>{STEP_INFO[step].help}</span>
        </li>
      })}
    </ul>
  </section>
}

/** Körningens steg i den ordning de körs: ett block per varv, bredd efter tid, med detaljer vid hovring, fokus och klick. */
export function RunTimeline({ events, nowT }: { events: JointEvent[]; nowT: number }) {
  const timeline: Timeline = useMemo(() => buildTimeline(events, nowT), [events, nowT])
  const [selected, setSelected] = useState<string | null>(null)
  const current = timeline.blocks.flatMap(block => block.segments).find(segment => segment.status === "running")
  const shownId = selected ?? current?.id ?? null
  return <div className="space-y-3">
    <p className="text-sm font-medium text-slate-900" role="status" aria-live="polite">{timeline.summary || "Körningen har inte kommit till första varvet än."}</p>
    <div className="overflow-x-auto pb-1">
      <ol className="flex min-w-full gap-2" aria-label="Körningens steg i tidsordning">
        {timeline.blocks.map(block => <li key={block.id} className="flex flex-col" style={{ flexGrow: block.share, flexBasis: 0, minWidth: block.segments.length ? `${block.segments.length * 2.75 + 0.5}rem` : "6.5rem" }}>
          <div className="mb-0.5 flex flex-wrap items-center gap-x-1.5 text-xs font-semibold text-slate-900">
            <BlockStatusIcon status={block.status}/>{block.label}
            <span className="font-normal tabular-nums text-slate-800">{block.segments.length ? `· ${formatDuration(block.seconds)}` : `· ${BLOCK_STATUS_TEXT[block.status].toLowerCase()}`}</span>
          </div>
          <div className="flex flex-1 gap-1">
            {block.segments.length
              ? block.segments.map(segment => <SegmentButton key={segment.id} segment={segment} block={block} selected={shownId === segment.id} onSelect={() => setSelected(segment.id)}/>)
              : <Placeholder block={block} selected={shownId === block.id} onSelect={() => setSelected(block.id)}/>}
          </div>
        </li>)}
      </ol>
    </div>
    <TimelineDetail timeline={timeline} selectedId={shownId}/>
    <Legend/>
  </div>
}
