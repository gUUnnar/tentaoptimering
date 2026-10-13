import type { ReactNode } from "react"
import { Ban, Check, CheckCheck, CircleCheck, CircleDashed, CircleHelp, CircleMinus, CircleX, Clock, Loader2, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { VERDICT_TEXT } from "@/lib/jointFormat"
import type { DayStatus } from "@/lib/jointTypes"

// Status visas alltid med både ikon och text; färg är bara förstärkning.

const ICON = 14
export type DayCellStatus = DayStatus | "pending" | "running"

export const DAY_STYLE: Record<DayCellStatus, string> = {
  pending: "border-dashed border-slate-400 bg-white text-slate-700",
  running: "border-sky-700 bg-sky-50 text-sky-900",
  optimal: "border-emerald-700 bg-emerald-100 text-emerald-900",
  feasible: "border-teal-700 bg-teal-50 text-teal-900",
  infeasible: "border-red-700 bg-red-100 text-red-900",
  unknown: "border-amber-700 bg-amber-100 text-amber-900",
}

export function DayStatusIcon({ status }: { status: DayCellStatus }) {
  switch (status) {
    case "optimal": return <CheckCheck size={ICON} aria-hidden="true"/>
    case "feasible": return <Check size={ICON} aria-hidden="true"/>
    case "infeasible": return <X size={ICON} aria-hidden="true"/>
    case "unknown": return <Clock size={ICON} aria-hidden="true"/>
    case "running": return <Loader2 size={ICON} className="animate-spin motion-reduce:animate-none" aria-hidden="true"/>
    default: return <CircleDashed size={ICON} aria-hidden="true"/>
  }
}

export function Chip({ icon, className, children }: { icon?: ReactNode; className?: string; children: ReactNode }) {
  return <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium", className)}>{icon}{children}</span>
}

const VERDICT_STYLE: Record<string, string> = {
  pass: "status-pass", fail: "status-fail", not_evaluated: "status-neutral", not_applicable: "bg-slate-200 text-slate-800",
}

/** Dom (pass/fail/not_evaluated/not_applicable). Okänt eller saknat värde behandlas som not_evaluated, aldrig som godkänt. */
export function VerdictChip({ status }: { status: string | null | undefined }) {
  const key = status && status in VERDICT_STYLE ? status : "not_evaluated"
  const icon = key === "pass" ? <CircleCheck size={ICON} aria-hidden="true"/> : key === "fail" ? <CircleX size={ICON} aria-hidden="true"/>
    : key === "not_applicable" ? <CircleMinus size={ICON} aria-hidden="true"/> : <CircleHelp size={ICON} aria-hidden="true"/>
  const label = status && !(status in VERDICT_STYLE) ? `Okänt värde "${status}" (behandlas som ej utvärderad)` : VERDICT_TEXT[key]
  return <Chip icon={icon} className={VERDICT_STYLE[key]}>{label}</Chip>
}

export function JobStatusChip({ status }: { status: string }) {
  const map: Record<string, { text: string; className: string; icon: ReactNode }> = {
    running: { text: "Körningen pågår", className: "bg-sky-100 text-sky-900", icon: <Loader2 size={ICON} className="animate-spin motion-reduce:animate-none" aria-hidden="true"/> },
    completed: { text: "Klar", className: "status-pass", icon: <CircleCheck size={ICON} aria-hidden="true"/> },
    failed: { text: "Misslyckades", className: "status-fail", icon: <CircleX size={ICON} aria-hidden="true"/> },
    cancelled: { text: "Stoppad", className: "status-neutral", icon: <Ban size={ICON} aria-hidden="true"/> },
  }
  const item = map[status] ?? { text: status, className: "bg-slate-200 text-slate-800", icon: <CircleHelp size={ICON} aria-hidden="true"/> }
  return <Chip icon={item.icon} className={item.className}>{item.text}</Chip>
}
