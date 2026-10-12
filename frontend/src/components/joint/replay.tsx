import { useEffect, useId, useMemo, useState } from "react"
import { ChevronDown, ChevronRight, Pause, Play, SkipBack, SkipForward, StepBack, StepForward } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatDuration } from "@/lib/jointFormat"
import { foldEvents } from "@/lib/jointState"
import type { JointEvent } from "@/lib/jointTypes"
import { RunPanels } from "./run-panels"

const SPEEDS = [1, 5, 20, 60]
const TICK_MS = 200

const INTRO = "Spela upp hur körningen gick till: när första lösningen kom, när den undre gränsen förbättrades och vilka dagar som misslyckades. Inget körs om."

/** "Förlopp i efterhand": hopfälld som standard. Uppspelningen monteras först när den fälls ut. */
export function Replay({ events, costVisible = true }: { events: JointEvent[]; costVisible?: boolean }) {
  const id = useId()
  const [open, setOpen] = useState(false)
  return <section aria-label="Förlopp i efterhand">
    <Card>
      <CardHeader>
        <CardTitle>Förlopp i efterhand</CardTitle>
        <p className="text-xs text-slate-800">{INTRO}</p>
      </CardHeader>
      <CardContent>
        {events.length === 0
          ? <p className="text-sm text-slate-700">Körningen har inga sparade händelser att spela upp.</p>
          : <Button type="button" size="sm" variant="outline" aria-expanded={open} aria-controls={`${id}-body`} onClick={() => setOpen(value => !value)}>
            {open ? <ChevronDown size={14} className="mr-1" aria-hidden="true"/> : <ChevronRight size={14} className="mr-1" aria-hidden="true"/>}{open ? "Dölj förloppet" : "Visa förloppet"}
          </Button>}
      </CardContent>
    </Card>
    <div id={`${id}-body`} hidden={!open} className="mt-3">{open && events.length > 0 && <ReplayBody events={events} costVisible={costVisible}/>}</div>
  </section>
}

function ReplayBody({ events, costVisible }: { events: JointEvent[]; costVisible: boolean }) {
  const id = useId()
  const endT = events.length ? Math.max(...events.map(event => event.t)) : 0
  const [position, setPosition] = useState(endT)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(20)

  useEffect(() => { setPosition(endT); setPlaying(false) }, [events, endT])

  useEffect(() => {
    if (!playing) return
    const timer = window.setInterval(() => {
      setPosition(current => {
        const next = current + (TICK_MS / 1000) * speed
        if (next >= endT) { setPlaying(false); return endT }
        return next
      })
    }, TICK_MS)
    return () => window.clearInterval(timer)
  }, [playing, speed, endT])

  const visible = useMemo(() => events.filter(event => event.t <= position + 1e-9), [events, position])
  const state = useMemo(() => foldEvents(visible), [visible])
  const times = useMemo(() => [...new Set(events.map(event => event.t))].sort((a, b) => a - b), [events])
  const previous = () => { setPlaying(false); setPosition([...times].reverse().find(t => t < position - 1e-9) ?? 0) }
  const next = () => { setPlaying(false); setPosition(times.find(t => t > position + 1e-9) ?? endT) }
  const play = () => { if (position >= endT) setPosition(0); setPlaying(value => !value) }

  return <div className="space-y-3">
    <Card>
      <CardHeader><CardTitle>Spela upp förloppet</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => { setPlaying(false); setPosition(0) }} aria-label="Till början"><SkipBack size={14} aria-hidden="true"/></Button>
          <Button size="sm" variant="outline" onClick={previous} aria-label="Föregående händelse"><StepBack size={14} aria-hidden="true"/></Button>
          <Button size="sm" onClick={play} aria-pressed={playing}>{playing ? <Pause size={14} className="mr-1" aria-hidden="true"/> : <Play size={14} className="mr-1" aria-hidden="true"/>}{playing ? "Pausa" : "Spela upp"}</Button>
          <Button size="sm" variant="outline" onClick={next} aria-label="Nästa händelse"><StepForward size={14} aria-hidden="true"/></Button>
          <Button size="sm" variant="outline" onClick={() => { setPlaying(false); setPosition(endT) }} aria-label="Till slutet"><SkipForward size={14} aria-hidden="true"/></Button>
          <label className="ml-2 flex items-center gap-1.5 text-xs" htmlFor={`${id}-speed`}>Hastighet
            <select id={`${id}-speed`} className="field !w-auto" value={speed} onChange={e => setSpeed(Number(e.target.value))}>{SPEEDS.map(s => <option key={s} value={s}>{s}×</option>)}</select>
          </label>
        </div>
        <div>
          <label className="label" htmlFor={`${id}-pos`}>Tidpunkt i körningen: {formatDuration(position)} av {formatDuration(endT)}</label>
          <input id={`${id}-pos`} type="range" min={0} max={endT} step={0.1} value={Math.min(position, endT)} className="w-full accent-sky-800"
            aria-valuetext={`${formatDuration(position)} av ${formatDuration(endT)}`}
            onChange={e => { setPlaying(false); setPosition(Number(e.target.value)) }}/>
          <p className="text-xs text-slate-700">Tangentbord: pilar flyttar markören, knapparna hoppar mellan händelser. {visible.length} av {events.length} händelser visas.</p>
        </div>
      </CardContent>
    </Card>
    <RunPanels state={state} events={visible} nowT={position} costVisible={costVisible}/>
  </div>
}
