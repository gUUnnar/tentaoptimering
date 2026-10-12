import type { ReactNode } from "react"
import { CircleCheck, CircleHelp, CircleMinus, CircleX, Lightbulb } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { DECISION_TEXT, DASH, formatCount, formatDuration, formatKr } from "@/lib/jointFormat"
import type { WarmStartDecisionName, WarmStartRecord } from "@/lib/jointTypes"
import { Chip, VerdictChip } from "./status-chip"

const DECISION_LOOK: Record<WarmStartDecisionName, { className: string; icon: ReactNode }> = {
  accepted: { className: "status-pass", icon: <CircleCheck size={14} aria-hidden="true"/> },
  rejected: { className: "status-fail", icon: <CircleX size={14} aria-hidden="true"/> },
  hint_only: { className: "bg-sky-100 text-sky-900", icon: <Lightbulb size={14} aria-hidden="true"/> },
  not_used: { className: "bg-slate-200 text-slate-800", icon: <CircleMinus size={14} aria-hidden="true"/> },
  not_recorded: { className: "status-neutral", icon: <CircleHelp size={14} aria-hidden="true"/> },
}

const requestedText = (requested: string) => requested === "auto" ? "Automatiskt" : requested === "none" ? "Ingen varmstart" : `Specifik körning ${requested}`

export function WarmStartCard({ record }: { record: WarmStartRecord | null }) {
  if (!record) return <Card><CardHeader><CardTitle>Varmstartsbeslut</CardTitle></CardHeader><CardContent className="text-sm text-slate-700">Körningen saknar beslutsfil för varmstart. Det betyder inte att ingen varmstart användes, bara att beslutet inte finns registrerat.</CardContent></Card>
  const decision = DECISION_TEXT[record.decision] ?? { label: record.decision, help: "Okänt beslut." }
  const look = DECISION_LOOK[record.decision] ?? DECISION_LOOK.not_recorded
  const re = record.recheck
  return <Card>
    <CardHeader><CardTitle>Varmstartsbeslut</CardTitle></CardHeader>
    <CardContent className="space-y-4 text-sm">
      <div className="space-y-1.5">
        <div className="flex flex-wrap items-center gap-2"><Chip icon={look.icon} className={look.className}>{decision.label}</Chip><span className="text-xs text-slate-700">Begärt: {requestedText(record.requested)}</span></div>
        <p>{record.explanation}</p>
        <p className="text-xs text-slate-700">{decision.help} Varmstarten kontrolleras alltid på nytt mot de nya reglerna.</p>
      </div>

      {record.source && <dl className="grid gap-x-6 gap-y-1 sm:grid-cols-2" aria-label="Källkörning">
        <Item label="Källkörning" value={<span className="font-mono text-xs">{record.source.run_id}</span>}/>
        <Item label="Kostnad i källkörningen" value={formatKr(record.source.cost_ore)}/>
        <Item label="Teknisk status nu (omkontrollerad)" value={<VerdictChip status={record.source.technical_validation_now}/>}/>
        <Item label="Resultatets SHA-256" value={<span className="font-mono text-[11px] break-all" title={record.source.result_sha256}>{record.source.result_sha256.slice(0, 16)}…</span>}/>
      </dl>}

      <div>
        <h4 className="text-xs font-semibold">Ändrade parametrar sedan källkörningen</h4>
        {record.changed_parameters.length ? <ul className="mt-1 flex flex-wrap gap-1.5">{record.changed_parameters.map(name => <li key={name} className="rounded border bg-slate-50 px-1.5 py-0.5 font-mono text-[11px]">{name}</li>)}</ul>
          : <p className="mt-1 text-xs text-slate-700">Inga ändrade parametrar redovisade.</p>}
      </div>

      {re && <div className="space-y-2">
        <h4 className="text-xs font-semibold">Omkontroll mot de nya reglerna</h4>
        <dl className="grid gap-x-6 gap-y-1 sm:grid-cols-2">
          <Item label="Status" value={re.status}/>
          <Item label="Avbruten" value={re.interrupted ? "Ja, kontrollen avbröts" : "Nej"}/>
          <Item label="Återanvända tentor" value={formatCount(re.exams_reused)}/>
          <Item label="Tentor utan startpass" value={formatCount(re.exams_without_start)}/>
          <Item label="Tentor med ej längre tillåtet pass" value={formatCount(re.exams_not_allowed)}/>
          <Item label="Dagar kontrollerade / underkända" value={`${formatCount(re.days_checked)} / ${formatCount(re.days_failed)}`}/>
          <Item label="Kontrolltid" value={formatDuration(re.check_seconds)}/>
          <Item label="Verifierad kostnad efter omkontroll" value={formatKr(re.verified_cost_ore)}/>
          <Item label="Tentor som ledtråd" value={formatCount(re.hint_exams)}/>
          <Item label="Första lösning" value={`${formatDuration(re.first_solution_seconds)}${re.first_solution_source ? ` (${re.first_solution_source})` : ""}`}/>
          <Item label="Slutlig kostnad" value={`${formatKr(re.final_cost_ore)}${re.final_source ? ` (${re.final_source})` : ""}`}/>
        </dl>
        {re.reasons.length > 0 && <div><h5 className="text-xs font-semibold">Skäl</h5><ul className="mt-1 list-disc pl-5 text-xs">{re.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul></div>}
        {re.notes.length > 0 && <div><h5 className="text-xs font-semibold">Anteckningar</h5><ul className="mt-1 list-disc pl-5 text-xs text-slate-700">{re.notes.map(note => <li key={note}>{note}</li>)}</ul></div>}
      </div>}

      <div>
        <h4 className="text-xs font-semibold">Körinställningar</h4>
        <p className="mt-1 text-xs text-slate-700">Trådar {formatCount(record.execution.threads)} · minne {record.execution.memory_mb === null ? "ingen gräns" : `${formatCount(record.execution.memory_mb)} MB`} · parallella dagkontroller {record.execution.parallel_day_checks ? "på" : "av"} · trådar per kontroll {formatCount(record.execution.workers_per_check)}</p>
      </div>
    </CardContent>
  </Card>
}

function Item({ label, value }: { label: string; value: ReactNode }) {
  return <div className="flex items-baseline justify-between gap-3 border-b border-slate-100 py-0.5"><dt className="text-xs text-slate-700">{label}</dt><dd className="text-right text-xs font-medium">{value ?? DASH}</dd></div>
}
