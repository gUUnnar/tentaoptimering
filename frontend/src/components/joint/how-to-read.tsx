import { BookOpen } from "lucide-react"

/** Kort förklaring i klartext av hur resultatet ska läsas. */
export function HowToRead() {
  return <section aria-label="Så läser du resultatet" className="rounded-lg border-2 border-sky-700 bg-sky-50 p-4 text-sm text-sky-950">
    <h3 className="flex items-center gap-2 font-semibold"><BookOpen size={16} aria-hidden="true"/>Så läser du resultatet</h3>
    <ul className="mt-2 list-disc space-y-1 pl-5">
      <li>Kostnaden är <strong>modellens kostnad</strong> för terminen, inte faktisk kostnad och inte en besparing.</li>
      <li><strong>Verifierad kostnad</strong> är den lägsta kostnad som hittats och kontrollerats. <strong>Undre gräns</strong> är den lägsta kostnad som bevisats möjlig. Den lägsta möjliga kostnaden i modellen ligger mellan dem. Först när de är lika är den bevisad.</li>
      <li>När du jämför två körningar går en skillnad i kostnad bara att tolka om den är större än osäkerheten. En mindre skillnad kan lika gärna bero på att sökningen inte hunnit klart.</li>
      <li><strong>Teknisk eftervalidering</strong> visar att placeringen följer de regler modellen kan uttrycka. Den visar <strong>inte</strong> att schemat går att genomföra i verksamheten. Det avgör <strong>verksamhetsmässig verifiering</strong>, som i nuläget normalt är "ej bedömd".</li>
    </ul>
  </section>
}
