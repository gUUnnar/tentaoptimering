/** Kort förklaring i klartext av hur resultatet ska läsas; visas bakom en ⓘ-ikon (se `InfoTip`). */
export function HowToRead() {
  return <>
    <span className="block font-semibold">Så läser du resultatet</span>
    <span className="block">Kostnaden är <strong>modellens årliga kapacitetskostnad</strong> (lokaler och vaktpool) för de valda tentorna, inte kostnaden för perioden, inte faktisk kostnad och inte en besparing.</span>
    <span className="block"><strong>Verifierad kostnad</strong> är den lägsta kostnad som hittats och kontrollerats. <strong>Undre gräns</strong> är den lägsta kostnad som bevisats möjlig. Först när de är lika är den bevisad.</span>
    <span className="block">En skillnad mellan två körningar går bara att tolka om den är större än osäkerheten. En mindre skillnad kan bero på att sökningen inte hunnit klart.</span>
    <span className="block"><strong>Teknisk eftervalidering</strong> visar att placeringen följer de regler modellen kan uttrycka, inte att schemat går att genomföra. Det avgör <strong>verksamhetsmässig verifiering</strong>, som normalt är ej bedömd.</span>
  </>
}
