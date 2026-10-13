import { useUnderlay } from "@/lib/useUnderlay"
import { PreparationCard } from "./preparation-card"
import { SourceDirCard } from "./source-dir-card"

type Props = { active: boolean; onPrepared: () => void }

/** Sidan "Underlag": välj källdatakatalog och förbered underlaget som optimeringen kräver. */
export default function UnderlayPage({ active, onPrepared }: Props) {
  const underlay = useUnderlay(active, onPrepared)
  const why = underlay.busy ? null
    : !underlay.loaded ? "Hämtar inställningar …"
    : !underlay.savedDir ? "Välj och spara en källdatakatalog först."
    : !underlay.dirSaved ? "Spara sökvägen först; förberedelsen använder den sparade katalogen."
    : null
  return <div className="max-w-4xl space-y-4">
    <p className="max-w-3xl text-sm text-slate-900">Här väljer du var källfilerna ligger och förbereder det underlag som optimeringen räknar på. Gör det innan du kör en optimering.</p>
    <SourceDirCard value={underlay.sourceDir} saved={underlay.savedDir} onChange={underlay.setSourceDir} onSave={() => void underlay.save()}
      disabled={underlay.busy} notice={underlay.notice} appDataDir={underlay.appDataDir}/>
    <PreparationCard progress={underlay.progress} error={underlay.prepareError} status={underlay.status}
      canPrepare={!underlay.busy && underlay.loaded && underlay.dirSaved} why={why} onPrepare={() => void underlay.prepare()}/>
  </div>
}
