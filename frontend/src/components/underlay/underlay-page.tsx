import { useUnderlay } from "@/lib/useUnderlay"
import { PreparationCard } from "./preparation-card"
import { SourceDirCard } from "./source-dir-card"
import { SummaryCard } from "./summary-card"

type Props = { active: boolean; onPrepared: () => void; onOpenJoint: () => void }

/** Sidan "Underlag": välj källdatakatalog, förbered underlaget som optimeringen kräver och se vad det innehåller. */
export default function UnderlayPage({ active, onPrepared, onOpenJoint }: Props) {
  const underlay = useUnderlay(active, onPrepared)
  const savedReady = underlay.state?.source.ready ?? false
  const why = underlay.busy ? null
    : !underlay.loaded ? "Hämtar inställningar …"
    : !underlay.savedDir ? "Välj och spara en källdatakatalog först."
    : !underlay.dirSaved ? "Spara sökvägen först; förberedelsen använder den sparade katalogen."
    : !savedReady ? "Den sparade katalogen saknar källfiler (se listan ovan)."
    : null
  const manifest = underlay.state?.underlay.manifest ?? null
  return <div className="max-w-4xl space-y-4">
    <p className="max-w-3xl text-sm text-slate-900">Här väljer du var källfilerna ligger och förbereder det underlag som optimeringen räknar på. Gör det innan du kör en optimering.</p>
    <SourceDirCard value={underlay.sourceDir} saved={underlay.savedDir} onChange={underlay.setSourceDir} onSave={() => void underlay.save()} onBrowse={() => void underlay.browse()}
      disabled={underlay.busy} choosing={underlay.choosing} notice={underlay.notice} appDataDir={underlay.appDataDir} check={underlay.check}/>
    <PreparationCard underlay={underlay.state?.underlay ?? null} job={underlay.state?.job ?? null} running={underlay.running} starting={underlay.starting}
      stateError={underlay.stateError} startError={underlay.startError} canPrepare={!underlay.busy && underlay.loaded && underlay.dirSaved && savedReady}
      why={why} onPrepare={() => void underlay.prepare()} onOpenJoint={onOpenJoint}/>
    {manifest && <SummaryCard manifest={manifest}/>}
  </div>
}
