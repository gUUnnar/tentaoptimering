import { CircleCheck, CircleHelp, Loader2 } from "lucide-react"
import { InfoTip } from "@/components/ui/info-tip"
import { Notice } from "@/components/ui/notice"
import { FixedBookingsCard } from "./fixed-bookings"
import { precheckTitle, precheckTone } from "@/lib/precheckView"
import type { PrecheckState } from "@/lib/usePrecheck"

/** Utfallet av förkontrollen: ett hinder som varning med skälen hopfällda, annars en rad med ikon och skälen bakom ⓘ. */
export function PrecheckResult({ state }: { state: PrecheckState }) {
  if (state.status === "running") return <p className="flex items-center gap-2 text-sm" role="status"><Loader2 size={15} className="animate-spin" aria-hidden="true"/>Kontrollerar om tentorna går att placera (högst 20 s) …</p>
  if (state.status === "error") return <Notice tone="error" title="Förkontrollen kunde inte genomföras." open><p>{state.error}</p></Notice>
  if (state.status !== "done" || !state.result) return null
  const { result } = state
  const fixed = result.fixed_bookings ? <FixedBookingsCard data={result.fixed_bookings}/> : null
  if (precheckTone(result.verdict) === "blocker") {
    return <div className="space-y-2"><Notice tone="error" title={precheckTitle(result)}>{result.reasons.map(reason => <p key={reason}>{reason}</p>)}</Notice>{fixed}</div>
  }
  const Icon = result.verdict === "possible" ? CircleCheck : CircleHelp
  return <div className="space-y-2"><p className="flex items-center gap-2 text-sm" role="status">
    <Icon size={16} className={result.verdict === "possible" ? "text-emerald-700" : "text-amber-700"} aria-hidden="true"/>{precheckTitle(result)}
    {result.reasons.length > 0 && <InfoTip label="Mer om förkontrollen">{result.reasons.map(reason => <span key={reason} className="block">{reason}</span>)}</InfoTip>}
  </p>{fixed}</div>
}
