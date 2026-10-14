import { useId } from "react"
import { TriangleAlert } from "lucide-react"
import { referenceFirst } from "@/lib/jointScenarioInfo"
import type { JointScenario } from "@/lib/jointTypes"

type Props = { scenarios: JointScenario[]; value: string; onChange: (id: string) => void; loadError: string }

/** Välj scenario. */
export function ScenarioSelect({ scenarios, value, onChange, loadError }: Props) {
  const id = useId()
  const bundled = referenceFirst(scenarios.filter(item => item.origin !== "user"))
  const own = scenarios.filter(item => item.origin === "user")
  return <div>
    <label className="label" htmlFor={id}>Scenario</label>
    <select id={id} className="field max-w-xl" value={value} onChange={event => onChange(event.target.value)} disabled={!scenarios.length}>
      {!scenarios.length && <option value="">Inga scenarier tillgängliga</option>}
      {bundled.length > 0 && <optgroup label="Inbyggda scenarier">{bundled.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</optgroup>}
      {own.length > 0 && <optgroup label="Egna sparade scenarier">{own.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</optgroup>}
    </select>
    {loadError && <p className="mt-2 flex items-start gap-1.5 text-sm text-red-900" role="alert"><TriangleAlert size={16} className="mt-0.5 shrink-0" aria-hidden="true"/>Kunde inte hämta scenarier: {loadError}</p>}
  </div>
}
