import { useId, useState, type FormEvent } from "react"
import { Save } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ApiError, jointApi } from "@/lib/jointApi"
import type { JointScenario } from "@/lib/jointTypes"

type Props = {
  baseId: string
  baseName: string
  parameters: Record<string, unknown>
  changeCount: number
  disabledReason: string | null
  onSaved: (scenario: JointScenario) => void
}

/** Sparar ändringarna som ett nytt scenario. Originalscenariot ändras aldrig. */
export function SaveScenario({ baseId, baseName, parameters, changeCount, disabledReason, onSaved }: Props) {
  const id = useId()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [nameError, setNameError] = useState("")

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!name.trim()) { setNameError("Ange ett namn på det nya scenariot."); return }
    setBusy(true); setError(""); setNameError("")
    try {
      const saved = await jointApi.saveScenario({ name: name.trim(), description: description.trim(), base: baseId, parameters })
      setOpen(false); setName(""); setDescription("")
      onSaved(saved)
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) setNameError("Det finns redan ett scenario med det namnet. Välj ett annat namn.")
      else setError((caught as Error).message)
    } finally { setBusy(false) }
  }

  if (!open) {
    return <div>
      <Button type="button" variant="outline" disabled={disabledReason !== null} onClick={() => setOpen(true)} aria-describedby={`${id}-why`}><Save size={15} className="mr-1" aria-hidden="true"/>Spara ändringarna som nytt scenario</Button>
      <p id={`${id}-why`} className="mt-1 text-xs text-slate-800">{disabledReason ?? `Sparar ${changeCount} ${changeCount === 1 ? "ändring" : "ändringar"} som ett eget scenario. Originalet "${baseName}" ändras inte.`}</p>
    </div>
  }
  return <form onSubmit={submit} className="space-y-3 rounded-md border bg-white p-3" aria-label="Spara som nytt scenario">
    <p className="text-sm font-semibold">Spara som nytt scenario</p>
    <p className="text-xs text-slate-900">Det nya scenariot byggs på "{baseName}" med dina {changeCount} {changeCount === 1 ? "ändring" : "ändringar"}. <strong>Originalscenariot ändras aldrig.</strong></p>
    <div>
      <label className="label" htmlFor={`${id}-name`}>Namn</label>
      <input id={`${id}-name`} className="field max-w-md" value={name} onChange={event => setName(event.target.value)} aria-invalid={!!nameError} aria-describedby={nameError ? `${id}-name-err` : undefined} autoFocus/>
      {nameError && <p id={`${id}-name-err`} role="alert" className="mt-1 text-xs text-red-800">{nameError}</p>}
    </div>
    <div>
      <label className="label" htmlFor={`${id}-desc`}>Beskrivning (valfri)</label>
      <textarea id={`${id}-desc`} className="field max-w-xl" rows={2} value={description} onChange={event => setDescription(event.target.value)}/>
    </div>
    {error && <p role="alert" className="text-sm text-red-800">{error}</p>}
    <div className="flex gap-2">
      <Button type="submit" disabled={busy}>{busy ? "Sparar …" : "Spara scenario"}</Button>
      <Button type="button" variant="outline" disabled={busy} onClick={() => { setOpen(false); setError(""); setNameError("") }}>Avbryt</Button>
    </div>
  </form>
}
