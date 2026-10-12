import type { ReactNode } from "react"
import { Cpu, MemoryStick, Timer } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCount, formatDuration } from "@/lib/jointFormat"
import type { JointState } from "@/lib/jointState"

export function ResourceBox({ state, elapsedT }: { state: JointState; elapsedT: number }) {
  const r = state.resources
  return <Card>
    <CardHeader><CardTitle>Resurser</CardTitle></CardHeader>
    <CardContent>
      <dl className="space-y-2 text-sm">
        <Row icon={<Timer size={15} aria-hidden="true"/>} label="Förbrukad tid" value={formatDuration(elapsedT)}/>
        <Row icon={<Cpu size={15} aria-hidden="true"/>} label="Beräkningstrådar" value={r ? formatCount(r.threads) : "Ej rapporterat"}/>
        <Row icon={<MemoryStick size={15} aria-hidden="true"/>} label="Minne" value={r ? (r.memory_mb === null ? "Ingen gräns satt" : `${formatCount(r.memory_mb)} MB`) : "Ej rapporterat"}/>
        <Row icon={<Cpu size={15} aria-hidden="true"/>} label="Dagar som kontrolleras samtidigt" value={r ? formatCount(r.parallel_checks) : "Ej rapporterat"}/>
        <Row icon={<Cpu size={15} aria-hidden="true"/>} label="Trådar per dagkontroll" value={r ? formatCount(r.workers_per_check) : "Ej rapporterat"}/>
      </dl>
    </CardContent>
  </Card>
}

function Row({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return <div className="flex items-center justify-between gap-3"><dt className="flex items-center gap-1.5 text-slate-900">{icon}{label}</dt><dd className="font-semibold tabular-nums">{value}</dd></div>
}
