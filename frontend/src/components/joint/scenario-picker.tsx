import { useId } from "react"
import { TriangleAlert } from "lucide-react"
import { referenceFirst } from "@/lib/jointScenarioInfo"
import type { JointScenario } from "@/lib/jointTypes"

type Props = { scenarios: JointScenario[]; value: string; onChange: (id: string) => void; loadError: string }

/**
 * Välj utgångspunkt för en körning: grundoptimeringen (B), en egen sparad parameteruppsättning eller en tidigare körning.
 * Test- och utvecklingsscenarier erbjuds inte. Det valda är bara en startpunkt: alla parametrar går att ändra fritt därefter.
 */
export function ScenarioSelect({ scenarios, value, onChange, loadError }: Props) {
  const id = useId()
  const visible = scenarios.filter(item => !item.hidden)
  const bundled = referenceFirst(visible.filter(item => item.origin === "bundled" || item.origin === undefined))
  const own = visible.filter(item => item.origin === "user")
  const runs = visible.filter(item => item.origin === "run")
  return <div>
    <label className="label" htmlFor={id}>Utgångspunkt</label>
    <select id={id} className="field max-w-xl" value={value} onChange={event => onChange(event.target.value)} disabled={!visible.length}>
      {!visible.length && <option value="">Ingen utgångspunkt tillgänglig</option>}
      {bundled.length > 0 && <optgroup label="Grundoptimering">{bundled.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</optgroup>}
      {own.length > 0 && <optgroup label="Egna sparade parameteruppsättningar">{own.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</optgroup>}
      {runs.length > 0 && <optgroup label="Tidigare körningar (deras parametrar)">{runs.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</optgroup>}
    </select>
    {loadError && <p className="mt-2 flex items-start gap-1.5 text-sm text-red-900" role="alert"><TriangleAlert size={16} className="mt-0.5 shrink-0" aria-hidden="true"/>Kunde inte hämta scenarier: {loadError}</p>}
  </div>
}
