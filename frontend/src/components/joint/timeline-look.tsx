import { Ban, CalendarCheck, CircleCheck, CircleDashed, History, Layers, Loader2, ShieldCheck, SkipForward, Undo2, Wrench, type LucideIcon } from "lucide-react"
import type { BlockStatus, SegmentStatus } from "@/lib/jointTimeline"
import type { PhaseName } from "@/lib/jointTypes"

// Utseende för tidslinjens steg. Varje steg har egen färg OCH egen ikon och text; färgen är bara förstärkning.

type IconType = LucideIcon

export const STEP_LOOK: Record<PhaseName, { box: string; Icon: IconType }> = {
  warm_start_check: { box: "border-indigo-700 bg-indigo-50 text-indigo-950", Icon: History },
  relaxation: { box: "border-sky-700 bg-sky-50 text-sky-950", Icon: Layers },
  day_checks: { box: "border-teal-700 bg-teal-50 text-teal-950", Icon: CalendarCheck },
  repair: { box: "border-amber-700 bg-amber-50 text-amber-950", Icon: Wrench },
  history: { box: "border-violet-700 bg-violet-50 text-violet-950", Icon: Undo2 },
  finalize: { box: "border-emerald-700 bg-emerald-50 text-emerald-950", Icon: ShieldCheck },
}

export const SEGMENT_STATUS_TEXT: Record<SegmentStatus, string> = { running: "Pågår", done: "Klar", stopped: "Avbröts" }
export const BLOCK_STATUS_TEXT: Record<BlockStatus, string> = {
  pending: "Väntar", running: "Pågår", done: "Klar", skipped: "Hoppades över", stopped: "Avbröts",
}

export function BlockStatusIcon({ status, size = 14 }: { status: BlockStatus; size?: number }) {
  switch (status) {
    case "running": return <Loader2 size={size} className="animate-spin motion-reduce:animate-none" aria-hidden="true"/>
    case "done": return <CircleCheck size={size} aria-hidden="true"/>
    case "skipped": return <SkipForward size={size} aria-hidden="true"/>
    case "stopped": return <Ban size={size} aria-hidden="true"/>
    default: return <CircleDashed size={size} aria-hidden="true"/>
  }
}
