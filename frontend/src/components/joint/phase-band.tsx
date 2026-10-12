import { Ban, CircleCheck, CircleDashed, Loader2, SkipForward } from "lucide-react"
import { cn } from "@/lib/utils"
import { formatDuration } from "@/lib/jointFormat"
import { stepViews, type JointState, type StepState } from "@/lib/jointState"

const LOOK: Record<StepState, { text: string; box: string }> = {
  pending: { text: "Väntar", box: "border-dashed border-slate-400 bg-white text-slate-800" },
  active: { text: "Pågår", box: "border-sky-700 bg-sky-50 text-sky-900" },
  done: { text: "Klar", box: "border-emerald-700 bg-emerald-50 text-emerald-900" },
  skipped: { text: "Hoppades över", box: "border-slate-300 bg-slate-100 text-slate-800" },
}

function StepIcon({ state, cancelled }: { state: StepState; cancelled: boolean }) {
  if (state === "active") return <Loader2 size={16} className="animate-spin motion-reduce:animate-none" aria-hidden="true"/>
  if (state === "done") return cancelled ? <Ban size={16} aria-hidden="true"/> : <CircleCheck size={16} aria-hidden="true"/>
  if (state === "skipped") return <SkipForward size={16} aria-hidden="true"/>
  return <CircleDashed size={16} aria-hidden="true"/>
}

/** Körningens steg i klartext, med förbrukad tid per steg och en mening om vad steget gör. */
export function PhaseBand({ state, nowT }: { state: JointState; nowT: number }) {
  const steps = stepViews(state, nowT)
  const cancelled = state.finished?.cancelled === true
  return <ol className="grid gap-2 sm:grid-cols-5" aria-label="Körningens steg">
    {steps.map((step, index) => {
      const look = LOOK[step.state]
      return <li key={step.id} className={cn("rounded-md border-2 p-2.5", look.box)} aria-current={step.state === "active" ? "step" : undefined}>
        <div className="flex items-center gap-1.5 text-xs font-semibold"><StepIcon state={step.state} cancelled={cancelled && step.state === "done" && index === steps.length - 1}/><span>{index + 1}. {step.label}</span></div>
        <div className="mt-1 text-xs">{step.id === "finalize" && step.state === "done" ? (cancelled ? "Stoppad" : "Klart") : look.text}</div>
        <div className="mt-0.5 text-sm font-semibold tabular-nums">{step.state === "pending" || step.state === "skipped" ? "–" : formatDuration(step.seconds)}</div>
        <p className="mt-1 text-[11px] leading-snug">{step.help}</p>
        {step.repeats > 1 && <div className="text-[11px]">{step.repeats} omgångar</div>}
      </li>
    })}
  </ol>
}
