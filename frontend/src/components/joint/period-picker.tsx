import { useId } from "react"
import { CircleAlert, TriangleAlert } from "lucide-react"
import { Button } from "@/components/ui/button"
import { checkText, partialText, periodInputError, periodPresets, sameChoice, type PeriodChoice } from "@/lib/period"
import type { PeriodState } from "@/lib/usePeriod"

type Props = {
  state: PeriodState
  /** Vald period, eller null när scenariots egen period gäller. */
  choice: PeriodChoice | null
  onChange: (choice: PeriodChoice | null) => void
  /** Skäl till att scenariot inte tar periodval (till exempel namngivna tentor); valet visas då spärrat. */
  disabledReason?: string | null
}

/**
 * Planeringsperioden på en rad: från och till inom underlagets täckning samt genvägar (en dag, en vecka, en månad, allt).
 * Täckning och förklaringar visas inte här utan i raden om scenariot. Kontrollen kommer från servern; en period utanför
 * underlaget avvisas med skälet, och en delvis täckt period måste godkännas.
 */
export function PeriodPicker({ state, choice, onChange, disabledReason }: Props) {
  const fromId = useId()
  const toId = useId()
  const { coverage, check } = state
  const demand = coverage && !disabledReason ? coverage.demand : null
  const shown = choice ?? (demand ? { from: demand.first, to: demand.last } : { from: "", to: "" })
  const inputError = choice ? periodInputError(choice) : null
  const set = (patch: Partial<PeriodChoice>) => onChange({ ...shown, ...patch, accept: false }) // ett ändrat datum kräver ett nytt godkännande

  return <section aria-label="Planeringsperiod" className="space-y-2.5">
    <div className="flex flex-wrap items-end gap-3">
      <h2 className="pb-1.5">Period</h2>
      <div><label className="label" htmlFor={fromId}>Från</label>
        <input id={fromId} type="date" className="field" value={shown.from} disabled={!demand} onChange={event => set({ from: event.target.value })}/></div>
      <div><label className="label" htmlFor={toId}>Till</label>
        <input id={toId} type="date" className="field" value={shown.to} disabled={!demand} onChange={event => set({ to: event.target.value })}/></div>
      <div className="flex flex-wrap gap-1.5" role="group" aria-label="Genvägar för period">
        {periodPresets(disabledReason ? null : coverage).map(preset =>
          <Button key={preset.id} type="button" size="sm" variant={sameChoice(choice, preset.choice) ? "default" : "outline"} onClick={() => onChange(preset.choice)}>{preset.label}</Button>)}
        {choice && <Button type="button" size="sm" variant="ghost" onClick={() => onChange(null)}>Scenariots period</Button>}
      </div>
    </div>
    {disabledReason && <p className="text-sm text-slate-900">{disabledReason}</p>}
    {state.loadError && <p role="alert" className="flex items-start gap-1.5 text-sm text-red-900"><CircleAlert size={16} className="mt-0.5 shrink-0" aria-hidden="true"/>Kunde inte hämta underlagets täckning: {state.loadError}</p>}
    {inputError && <p role="alert" className="text-sm text-red-900">{inputError}</p>}
    {choice && !inputError && <div role="status" aria-live="polite" className="space-y-1 text-sm">
      {!check && <p className="text-slate-800">Kontrollerar perioden …</p>}
      {check && !check.can_plan && <p className="font-medium text-red-900">{checkText(check)}</p>}
      {check?.can_plan && check.partial && <label className="flex items-start gap-2 rounded-md border border-amber-700 bg-amber-50 p-2 text-sm text-amber-950">
        <input type="checkbox" className="mt-1" checked={choice.accept === true} onChange={event => onChange({ ...choice, accept: event.target.checked })}/>
        <span><strong>Godkänn den kortare perioden.</strong> {partialText(check)}</span></label>}
      {check?.warnings.map(text => <p key={text} className="flex items-start gap-1.5 text-xs text-amber-900"><TriangleAlert size={14} className="mt-0.5 shrink-0" aria-hidden="true"/>{text}</p>)}
    </div>}
  </section>
}
