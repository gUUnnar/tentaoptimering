import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { DAY_STATUS_HELP, DAY_STATUS_TEXT, formatDuration, kindLabel } from "@/lib/jointFormat"
import { activeBatch, dayCounts, dayGrid, dayKinds, type DayGridCell, type JointState } from "@/lib/jointState"
import { DAY_STYLE, DayStatusIcon, type DayCellStatus } from "./status-chip"

const ORDER: DayCellStatus[] = ["pending", "running", "optimal", "feasible", "infeasible", "unknown"]
const cellStatus = (cell: DayGridCell): DayCellStatus => cell.kind === "pending" ? (cell.running ? "running" : "pending") : cell.cell.status

export function shortDate(date: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date)
  return match ? `${Number(match[3])}/${Number(match[2])}` : date
}

function describe(cell: DayGridCell, kind: string): string {
  const status = cellStatus(cell)
  if (cell.kind === "pending") return `${DAY_STATUS_TEXT[status]}: ${DAY_STATUS_HELP[status]}`
  return `${cell.cell.date} · ${DAY_STATUS_TEXT[status]} · ${formatDuration(cell.cell.seconds)} · ${kindLabel(kind)}. ${DAY_STATUS_HELP[status]}`
}

/** Räknaren för samtidiga kontroller och trådar per kontroll, hämtad ur den aktiva batchen (annars resursrapporten). */
export function ConcurrencyBadge({ state }: { state: JointState }) {
  const batch = activeBatch(state)
  const parallel = batch?.parallel ?? state.resources?.parallel_checks ?? null
  const workers = batch?.workers_per_check ?? state.resources?.workers_per_check ?? null
  const idle = batch === null
  return <div className="rounded-md border bg-slate-50 px-3 py-2 text-sm" aria-live="polite">
    <span className="text-slate-700">Kontroller som körs samtidigt: </span>
    <strong className="tabular-nums">{idle ? 0 : parallel ?? "–"}</strong>
    <span className="text-slate-700"> · trådar per kontroll: </span>
    <strong className="tabular-nums">{workers ?? "–"}</strong>
    {idle && parallel !== null && <span className="ml-2 text-xs text-slate-700">(inga kontroller pågår; senaste inställning {parallel} samtidiga)</span>}
  </div>
}

function KindGrid({ state, kind }: { state: JointState; kind: string }) {
  const cells = dayGrid(state, kind)
  const counts = dayCounts(cells)
  const batch = state.batches[kind]
  const [selected, setSelected] = useState<number | null>(null)
  const done = batch?.done ?? (state.days[kind]?.length ?? 0)
  const total = batch?.total ?? cells.length
  return <section aria-label={kindLabel(kind)} className="space-y-2">
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <h4 className="text-sm font-semibold">{kindLabel(kind)}</h4>
      <div className="flex items-center gap-2 text-xs text-slate-700">
        <span className="tabular-nums">{done} av {total} klara</span>
        <div role="progressbar" aria-label={`${kindLabel(kind)}: ${done} av ${total} klara`} aria-valuemin={0} aria-valuemax={total} aria-valuenow={done} className="h-2 w-28 overflow-hidden rounded-full bg-slate-200"><div className="h-full bg-sky-800" style={{ width: total ? `${(done / total) * 100}%` : "0%" }}/></div>
      </div>
    </div>
    <ul className="flex flex-wrap gap-1.5" aria-label={`Dagar, ${kindLabel(kind)}`}>
      {cells.map((cell, index) => {
        const status = cellStatus(cell)
        const text = describe(cell, kind)
        return <li key={cell.kind === "known" ? cell.cell.date : `p${index}`}>
          <button type="button" title={text} aria-label={text} aria-pressed={selected === index}
            onMouseEnter={() => setSelected(index)} onFocus={() => setSelected(index)} onClick={() => setSelected(index)}
            className={cn("flex h-12 w-[4.25rem] flex-col items-center justify-center rounded-md border-2 text-[11px] leading-tight focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700", DAY_STYLE[status], selected === index && "ring-2 ring-slate-900")}>
            <DayStatusIcon status={status}/>
            <span className="mt-0.5 tabular-nums">{cell.kind === "known" ? shortDate(cell.cell.date) : status === "running" ? "pågår" : "väntar"}</span>
          </button>
        </li>
      })}
      {!cells.length && <li className="text-xs text-slate-700">Inga dagar rapporterade ännu.</li>}
    </ul>
    <p className="min-h-[2.25rem] rounded-md bg-slate-50 px-2 py-1 text-xs text-slate-800" aria-live="polite">{selected !== null && cells[selected] ? describe(cells[selected], kind) : "Välj en ruta (mus eller tangentbord) för detaljer."}</p>
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs" aria-label="Teckenförklaring och antal">
      {ORDER.map(status => <li key={status} className="flex items-center gap-1"><span className={cn("inline-flex items-center gap-1 rounded border px-1.5 py-0.5", DAY_STYLE[status])}><DayStatusIcon status={status}/>{DAY_STATUS_TEXT[status]}</span><span className="tabular-nums">{counts[status]}</span></li>)}
    </ul>
  </section>
}

export function DayGrids({ state }: { state: JointState }) {
  const kinds = dayKinds(state)
  return <Card>
    <CardHeader><CardTitle>Dagkontroller</CardTitle></CardHeader>
    <CardContent className="space-y-5">
      <ConcurrencyBadge state={state}/>
      {kinds.length ? kinds.map(kind => <KindGrid key={kind} state={state} kind={kind}/>) : <p className="text-sm text-slate-700">Inga dagkontroller har börjat ännu.</p>}
      <p className="text-xs text-slate-700">Rutan "pågår" är en uppskattning: gränssnittet får ingen händelse när en dag påbörjas och visar därför de närmast väntande dagarna, högst så många som kontrollerna kan köra samtidigt.</p>
    </CardContent>
  </Card>
}
