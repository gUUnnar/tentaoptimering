import { useEffect, useId, useMemo, useState } from "react"
import { Play, TriangleAlert } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { abcApi, ACTUAL_REF } from "@/lib/abcApi"
import type { AbcCompare, AbcProfile, AbcRun, AbcWishes } from "@/lib/abcTypes"
import { KIND_EXPLANATION, KIND_TITLE, compareOptions, latestOfKind, outcomeText, wishLines } from "@/lib/abcView"
import { CompareView } from "./compare-view"

type Props = {
  /** Räknas upp när körningar eller underlag har ändrats. */
  reloadKey: number
  busy: boolean
  onRunBase: () => void
  onNewRun: (basedOnRunId: string | null) => void
  onOpenResult: (runId: string) => void
  /** Begäran från Resultat om att jämföra en körning (som höger sida, mot A). */
  compareRequest: { ref: string; nonce: number } | null
}

type Load<T> = { status: "loading" | "ready" | "error"; value: T | null; error: string }
const loading = <T,>(): Load<T> => ({ status: "loading", value: null, error: "" })

const dateText = (iso: string | null) => iso ? iso.slice(0, 16).replace("T", " ") : ""

/** Översikt över A (faktisk bokning), B (grundoptimering) och C (egna körningar) samt jämförelse av två valfria alternativ. */
export function AbcPage({ reloadKey, busy, onRunBase, onNewRun, onOpenResult, compareRequest }: Props) {
  const [runs, setRuns] = useState<Load<AbcRun[]>>(loading())
  const [wishes, setWishes] = useState<Load<AbcWishes>>(loading())
  const [actual, setActual] = useState<Load<AbcProfile>>(loading())
  const [left, setLeft] = useState(ACTUAL_REF)
  const [right, setRight] = useState("")
  const [compare, setCompare] = useState<Load<AbcCompare> | null>(null)
  const id = useId()

  useEffect(() => {
    let stale = false
    abcApi.runs().then(value => { if (!stale) setRuns({ status: "ready", value, error: "" }) }).catch(error => { if (!stale) setRuns({ status: "error", value: null, error: (error as Error).message }) })
    abcApi.wishes().then(value => { if (!stale) setWishes({ status: "ready", value, error: "" }) }).catch(error => { if (!stale) setWishes({ status: "error", value: null, error: (error as Error).message }) })
    abcApi.profile(ACTUAL_REF).then(value => { if (!stale) setActual({ status: "ready", value, error: "" }) }).catch(error => { if (!stale) setActual({ status: "error", value: null, error: (error as Error).message }) })
    return () => { stale = true }
  }, [reloadKey])

  const list = runs.value ?? []
  const base = useMemo(() => latestOfKind(list, "B"), [list])
  const own = useMemo(() => list.filter(run => run.kind === "C"), [list])
  const options = useMemo(() => compareOptions(list), [list])

  useEffect(() => { if (compareRequest) { setLeft(ACTUAL_REF); setRight(compareRequest.ref) } }, [compareRequest])

  // Förval: A mot senaste B, annars mot senaste körningen.
  useEffect(() => {
    if (right || !list.length) return
    setRight((base ?? list[0]).run_id)
  }, [list, base, right])

  useEffect(() => {
    if (!left || !right || left === right) { setCompare(null); return }
    let stale = false
    setCompare(loading())
    abcApi.compare(left, right).then(value => { if (!stale) setCompare({ status: "ready", value, error: "" }) })
      .catch(error => { if (!stale) setCompare({ status: "error", value: null, error: (error as Error).message }) })
    return () => { stale = true }
  }, [left, right, reloadKey])

  return <div className="space-y-4">
    <div className="grid gap-3 lg:grid-cols-3">
      <Card><CardHeader><CardTitle>{KIND_TITLE.A}</CardTitle></CardHeader><CardContent className="space-y-2 text-sm">
        <p>{KIND_EXPLANATION.A}</p>
        {actual.status === "loading" && <p role="status">Hämtar bokningen …</p>}
        {actual.status === "error" && <p className="text-red-900" role="alert">{actual.error}</p>}
        {actual.value && <ul className="space-y-0.5 text-xs">
          <li>{actual.value.scope.exam_count} tentamina i Uppsala, {actual.value.scope.booked} med bokning</li>
          <li>{actual.value.metrics.rooms_used} namngivna salar, varav {actual.value.metrics.rooms_outside_model_register} utanför lokalregistret</li>
          <li>{actual.value.metrics.addresses_without_room} adresser anger bara adress (sal saknas)</li></ul>}
        {actual.value?.notes.map(note => <p key={note} className="flex items-start gap-1 text-xs text-amber-900"><TriangleAlert size={13} className="mt-0.5 shrink-0" aria-hidden="true"/>{note}</p>)}
      </CardContent></Card>

      <Card><CardHeader><CardTitle>{KIND_TITLE.B}</CardTitle></CardHeader><CardContent className="space-y-2 text-sm">
        <p>{KIND_EXPLANATION.B}</p>
        {base ? <p className="text-xs"><strong>{base.name}</strong><br/>{outcomeText(base)}{base.current_underlay === false ? " · byggd på ett äldre underlag" : ""}</p> : <p className="text-xs">Ingen grundoptimering är körd än.</p>}
        <div className="flex flex-wrap gap-2">
          <Button type="button" size="sm" disabled={busy} onClick={onRunBase}><Play size={13} className="mr-1" aria-hidden="true"/>{base ? "Kör B igen" : "Kör B"}</Button>
          {base && <Button type="button" size="sm" variant="outline" onClick={() => onOpenResult(base.run_id)}>Visa resultat</Button>}
        </div>
      </CardContent></Card>

      <Card><CardHeader><CardTitle>{KIND_TITLE.C}</CardTitle></CardHeader><CardContent className="space-y-2 text-sm">
        <p>{KIND_EXPLANATION.C}</p>
        <p className="text-xs">{own.length === 0 ? "Inga egna körningar än." : `${own.length} egna ${own.length === 1 ? "körning" : "körningar"} sparade.`}</p>
        <Button type="button" size="sm" disabled={busy} onClick={() => onNewRun(null)}>Ny egen körning från B</Button>
      </CardContent></Card>
    </div>

    <Card><CardHeader><CardTitle>Verksamhetens önskemål i underlaget</CardTitle></CardHeader><CardContent className="space-y-1 text-sm">
      {wishes.status === "loading" && <p role="status">Hämtar …</p>}
      {wishes.status === "error" && <p className="text-red-900" role="alert">{wishes.error}</p>}
      {wishes.value && wishLines(wishes.value).map(line => <p key={line}>{line}</p>)}
      <p className="text-xs text-slate-800">Motiveringarna bevaras som de är och tolkas inte. Önskemålen anger datum, inte klockslag.</p>
    </CardContent></Card>

    <Card><CardHeader><CardTitle>Körningar</CardTitle></CardHeader><CardContent>
      {runs.status === "error" && <p className="text-sm text-red-900" role="alert">{runs.error}</p>}
      {runs.status === "ready" && list.length === 0 && <p className="text-sm">Inga körningar än. Kör B eller starta en egen körning.</p>}
      {list.length > 0 && <div className="max-h-80 overflow-auto"><table className="w-full text-sm"><thead><tr className="border-b"><th className="p-1.5 text-left text-xs">Namn</th><th className="p-1.5 text-left text-xs">Typ</th><th className="p-1.5 text-left text-xs">Resultat</th><th className="p-1.5 text-left text-xs">Startad</th><th className="p-1.5"/></tr></thead>
        <tbody>{list.map(run => <tr key={run.run_id} className="border-b last:border-0">
          <td className="p-1.5">{run.name}{run.current_underlay === false && <span className="ml-2 text-xs text-amber-900">äldre underlag</span>}</td>
          <td className="p-1.5"><Badge>{run.kind}</Badge></td><td className="p-1.5 text-xs">{outcomeText(run)}</td><td className="p-1.5 text-xs">{dateText(run.created_at)}</td>
          <td className="flex justify-end gap-1 p-1.5"><Button type="button" size="sm" variant="outline" onClick={() => onOpenResult(run.run_id)}>Resultat</Button>
            <Button type="button" size="sm" variant="outline" disabled={busy} onClick={() => onNewRun(run.run_id)}>Utgå från denna</Button></td></tr>)}</tbody></table></div>}
    </CardContent></Card>

    <Card><CardHeader><CardTitle>Jämför</CardTitle></CardHeader><CardContent className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div><label className="label" htmlFor={`${id}-l`}>Referens (vänster)</label>
          <select id={`${id}-l`} className="field min-w-[18rem]" value={left} onChange={event => setLeft(event.target.value)}>{options.map(item => <option key={item.ref} value={item.ref}>{item.label}</option>)}</select></div>
        <div><label className="label" htmlFor={`${id}-r`}>Jämförs med (höger)</label>
          <select id={`${id}-r`} className="field min-w-[18rem]" value={right} onChange={event => setRight(event.target.value)}>
            <option value="">Välj …</option>{options.map(item => <option key={item.ref} value={item.ref}>{item.label}</option>)}</select></div>
      </div>
      {left === right && right && <p className="text-sm" role="status">Välj två olika alternativ.</p>}
      {compare?.status === "loading" && <p className="text-sm" role="status">Hämtar jämförelsen … (A läses ur bokningarna och kan ta några sekunder)</p>}
      {compare?.status === "error" && <p className="flex items-start gap-1.5 rounded-md bg-red-50 p-2 text-sm text-red-900" role="alert"><TriangleAlert size={16} className="mt-0.5 shrink-0" aria-hidden="true"/>{compare.error}</p>}
      {compare?.value && <CompareView result={compare.value}/>}
    </CardContent></Card>
  </div>
}
