import { Plus, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { validateLadder, type LadderRow } from "@/lib/paramValues"

type Props = { draft: unknown; onChange: (draft: unknown) => void; disabled: boolean; label: string; describedBy?: string }

/** Bemanningstrappan: "upp till X deltagare kräver Y vakter". Trösklarna måste stiga för varje rad. */
export function StaffingLadderInput({ draft, onChange, disabled, label, describedBy }: Props) {
  const rows = (Array.isArray(draft) ? draft : []) as LadderRow[]
  const check = validateLadder(rows)
  const update = (index: number, patch: Partial<LadderRow>) => onChange(rows.map((row, i) => i === index ? { ...row, ...patch } : row))
  const add = () => {
    const last = Number(rows.at(-1)?.max)
    onChange([...rows, { max: Number.isInteger(last) ? String(last + 50) : "", staff: rows.at(-1)?.staff ?? "1" }])
  }
  return <div className="space-y-2" role="group" aria-label={label} aria-describedby={describedBy}>
    <table className="w-full max-w-lg text-sm">
      <caption className="sr-only">{label}: upp till hur många deltagare som kräver hur många vakter</caption>
      <thead><tr className="text-left text-xs text-slate-800"><th scope="col" className="pb-1 pr-2 font-medium">Upp till (deltagare)</th><th scope="col" className="pb-1 pr-2 font-medium">Antal vakter</th><th scope="col" className="pb-1"><span className="sr-only">Åtgärd</span></th></tr></thead>
      <tbody>
        {rows.map((row, index) => {
          const error = check.rowErrors[index]
          return <tr key={index} className="align-top">
            <td className="pb-1.5 pr-2">
              <input className="field w-28 text-right tabular-nums" type="text" inputMode="numeric" aria-label={`Rad ${index + 1}: antal deltagare, upp till`} aria-invalid={!!error} value={row.max} disabled={disabled} onChange={event => update(index, { max: event.target.value })}/>
            </td>
            <td className="pb-1.5 pr-2">
              <input className="field w-20 text-right tabular-nums" type="text" inputMode="numeric" aria-label={`Rad ${index + 1}: antal vakter`} aria-invalid={!!error} value={row.staff} disabled={disabled} onChange={event => update(index, { staff: event.target.value })}/>
            </td>
            <td className="pb-1.5">
              <Button type="button" size="sm" variant="outline" disabled={disabled || rows.length <= 1} aria-label={`Ta bort rad ${index + 1}`} onClick={() => onChange(rows.filter((_, i) => i !== index))}><X size={14} aria-hidden="true"/><span className="ml-1">Ta bort</span></Button>
              {error && <p className="mt-1 text-xs text-red-800">{error}</p>}
            </td>
          </tr>
        })}
      </tbody>
    </table>
    <Button type="button" size="sm" variant="outline" disabled={disabled} onClick={add}><Plus size={14} className="mr-1" aria-hidden="true"/>Lägg till rad</Button>
    <p className="text-xs text-slate-800">Varje rad gäller upp till angivet antal deltagare. Antalet deltagare måste stiga för varje rad.</p>
  </div>
}
