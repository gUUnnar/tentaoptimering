import { useId } from "react"
import { CircleAlert, Info, TriangleAlert } from "lucide-react"
import { Button } from "@/components/ui/button"
import { checkText, coverageText, partialText, periodInputError, periodPresets, sameChoice, type PeriodChoice } from "@/lib/period"
import type { PeriodState } from "@/lib/usePeriod"
import { InfoTip } from "@/components/ui/info-tip"

type Props = {
  state: PeriodState
  /** Vald period, eller null när scenariots egen period gäller. */
  choice: PeriodChoice | null
  onChange: (choice: PeriodChoice | null) => void
  /** Skäl till att scenariot inte tar periodval (till exempel namngivna tentor); valet visas då spärrat. */
  disabledReason?: string | null
}

/**
 * Välj planeringsperiod direkt i gränssnittet: valfria datum inom underlagets täckning, en dag, en vecka eller allt.
 * Täckningen och kontrollen kommer från servern; perioden räknas aldrig som hel termin, och en period utanför
 * underlaget avvisas med skälet. Varje period planeras explorativt (se anmärkningen), vilket alltid visas här.
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
    <div>
      <h2 className="flex items-center gap-1.5 text-base font-bold">2. Välj planeringsperiod
        <InfoTip label="Om planeringsperioden">Välj datum eller en genväg för att planera en kortare period. En kort period ger en mycket snabb körning med samma motor och kontroller. Utan val gäller scenariots egen period.</InfoTip></h2>
      <p className="mt-0.5 text-xs text-slate-800">{choice ? "Du planerar för perioden nedan." : "Scenariots egen period gäller."}</p>
    </div>
    {disabledReason && <p className="flex items-start gap-1.5 text-sm text-slate-900"><Info size={14} className="mt-0.5 shrink-0" aria-hidden="true"/>{disabledReason}</p>}
    {state.loadError && <p role="alert" className="flex items-start gap-1.5 text-sm text-red-900"><CircleAlert size={16} className="mt-0.5 shrink-0" aria-hidden="true"/>Kunde inte hämta underlagets täckning: {state.loadError}</p>}
    {coverage && <p className="flex items-start gap-1.5 text-xs text-slate-900"><Info size={14} className="mt-0.5 shrink-0" aria-hidden="true"/>
      <span>{coverageText(coverage)}{coverage.bookings && <> Lokalbokningar finns {coverage.bookings.first}–{coverage.bookings.last} men ger ingen efterfrågan och kan inte optimeras utan deltagarantal.</>}</span>
    </p>}
    <div className="flex flex-wrap items-end gap-3">
      <div><label className="label" htmlFor={fromId}>Från och med</label>
        <input id={fromId} type="date" className="field" value={shown.from} disabled={!demand} onChange={event => set({ from: event.target.value })}/></div>
      <div><label className="label" htmlFor={toId}>Till och med</label>
        <input id={toId} type="date" className="field" value={shown.to} disabled={!demand} onChange={event => set({ to: event.target.value })}/></div>
      <div className="flex flex-wrap gap-1.5" role="group" aria-label="Genvägar för period">
        {periodPresets(disabledReason ? null : coverage).map(preset =>
          <Button key={preset.id} type="button" size="sm" variant={sameChoice(choice, preset.choice) ? "default" : "outline"} onClick={() => onChange(preset.choice)}>{preset.label}</Button>)}
        {choice && <Button type="button" size="sm" variant="ghost" onClick={() => onChange(null)}>Använd scenariots period</Button>}
      </div>
    </div>
    {inputError && <p role="alert" className="text-sm text-red-900">{inputError}</p>}
    {choice && !inputError && <div role="status" aria-live="polite" className="space-y-1 text-sm">
      {!check && <p className="text-slate-800">Kontrollerar perioden …</p>}
      {check && <p className={check.can_plan ? "font-medium" : "font-medium text-red-900"}>{checkText(check)}</p>}
      {check?.can_plan && check.partial && <label className="flex items-start gap-2 rounded-md border-2 border-amber-600 bg-amber-50 p-2 text-sm text-amber-950">
        <input type="checkbox" className="mt-1" checked={choice.accept === true} onChange={event => onChange({ ...choice, accept: event.target.checked })}/>
        <span><strong>Godkänn den kortare perioden.</strong> {partialText(check)}</span></label>}
      {check?.warnings.map(text => <p key={text} className="flex items-start gap-1.5 text-xs text-amber-900"><TriangleAlert size={14} className="mt-0.5 shrink-0" aria-hidden="true"/>{text}</p>)}
    </div>}
    {coverage && <p className="flex items-center gap-1.5 rounded-md bg-slate-100 p-2 text-xs text-slate-900"><strong>{coverage.planning_basis.label}</strong><InfoTip label="Om planeringsunderlaget">{coverage.planning_basis.note}</InfoTip></p>}
  </section>
}
