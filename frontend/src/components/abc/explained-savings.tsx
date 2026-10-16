import { useState } from "react"
import { CircleCheck, TriangleAlert } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { InfoTip } from "@/components/ui/info-tip"
import { Notice } from "@/components/ui/notice"
import type { AbcExplained, ExplainedDetail, ExplainedItem } from "@/lib/abcTypes"
import { COST_KIND_TEXT, ORIGIN_TEXT, STAFF_ORIGIN_TEXT, direction, hasDetail, headline, itemsReconcile, realizationView, signedKr, splitSentence } from "@/lib/abcExplainView"
import { formatKr } from "@/lib/jointFormat"
import { ExamChanges, ItemDetail, TD, TH } from "./explained-detail"

type Explained = AbcExplained & ExplainedDetail

const ARROW = { down: "text-emerald-900", up: "text-red-900", same: "text-slate-800" }

/** Totalskillnaden mellan två alternativ i kronor, uppdelad på kostnadsposter som går att fälla ut ner till lokaler, bokningar och personalpass. */
export function ExplainedSavings({ explained }: { explained: AbcExplained }) {
  if (!hasDetail(explained)) {
    return <Card><CardHeader><CardTitle>Förklarad skillnad</CardTitle></CardHeader><CardContent>
      <Notice tone="warning" title="Skillnaden kan inte förklaras" open><ul className="list-disc pl-5">{explained.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul></Notice></CardContent></Card>
  }
  return <div className="space-y-4" data-testid="explained-savings">
    {explained.data_quality.flags.length > 0 && <Notice tone="warning" title={explained.data_quality.simulated ? "Resultatet bygger på simulerade uppgifter" : "Läs resultatet med dessa förbehåll"} open>
      <ul className="list-disc pl-5">{explained.data_quality.flags.map(flag => <li key={flag.key + flag.text}>{flag.text}</li>)}</ul></Notice>}
    {explained.reasons.length > 0 && <Notice tone="warning" title="Ingen totalskillnad redovisas" open><ul className="list-disc pl-5">{explained.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul></Notice>}
    <Total explained={explained}/>
    <Items explained={explained}/>
    <Realization explained={explained}/>
    <Kinds explained={explained}/>
    <Card><CardHeader><CardTitle className="flex items-center gap-1.5">Alla tentor som ändrats<InfoTip label="Om ändrade tentor">Före- och efteruppgifter per tentamen, med den kostnadspost respektive förändring som förklarar dem.</InfoTip></CardTitle></CardHeader>
      <CardContent><p className="mb-2 text-sm">Av {explained.exams.compared} tentor har {explained.exams.changed_count} ändrat datum, klockslag eller sal ({explained.exams.time_changed} byter datum eller tid, {explained.exams.room_changed} byter sal).</p>
        <ExamChanges title="Visa ändrade tentor" rows={explained.exams.changed} explained={explained}/>{explained.exams.truncated && <p className="text-xs">Listan är avkortad.</p>}</CardContent></Card>
  </div>
}

function Total({ explained }: { explained: Explained }) {
  const difference = explained.total.difference_ore
  const reconciled = itemsReconcile(explained)
  const left = explained.basis.left, right = explained.basis.right
  return <Card><CardHeader><CardTitle className="flex items-center gap-1.5">{headline(explained)}
    <InfoTip label="Om totalskillnaden">{explained.total.label} Skillnaden är modellberäknad. Den är inte faktisk kostnad och inte en verifierad besparing.</InfoTip></CardTitle></CardHeader>
    <CardContent className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-3">
        <Figure label={left.name} value={explained.available ? formatKr(explained.total.left_ore) : "–"} note={explained.available ? COST_KIND_TEXT[left.cost_kind] ?? left.cost_kind : "Inte jämförbart underlag"}/>
        <Figure label={right.name} value={explained.available ? formatKr(explained.total.right_ore) : "–"} note={explained.available ? COST_KIND_TEXT[right.cost_kind] ?? right.cost_kind : "Inte jämförbart underlag"}/>
        <Figure label="Skillnad (höger minus vänster)" value={difference === null ? "–" : signedKr(difference)} note="Modellberäknad, inte en verifierad besparing" strong/>
      </div>
      {explained.summary && <p className="text-sm">{explained.summary}</p>}
      <p className="text-sm">{splitSentence(explained)}</p>
      <p className={`flex items-center gap-1 text-xs ${reconciled ? "text-emerald-900" : "text-red-900"}`}>{reconciled ? <CircleCheck size={14} aria-hidden="true"/> : <TriangleAlert size={14} aria-hidden="true"/>}
        {reconciled ? "Kostnadsposternas skillnader summerar till totalskillnaden." : "Kostnadsposterna redovisas utan totalskillnad."}</p>
      <div className="grid gap-2 text-xs md:grid-cols-2">{[left, right].map(side => <div key={side.name} className="rounded-md bg-slate-50 p-2"><p className="font-semibold">{side.name}</p>
        <p>Kostnad: {COST_KIND_TEXT[side.cost_kind] ?? side.cost_kind}{side.priced_by === "the_other_alternative" ? ", prissatt med det andra alternativets regler och priser" : ""}.</p>
        <p>Resursdata: {side.resource_data ? `${side.resource_data.pack_id} (${side.resource_data.origins.map(origin => ORIGIN_TEXT[origin] ?? origin).join(", ")})` : "ingen (kostnad per plats)"}.</p>
        <p>Bemanning: {STAFF_ORIGIN_TEXT[side.staffing_origin] ?? side.staffing_origin}.</p></div>)}</div>
      {explained.notes.map(note => <p key={note} className="text-xs text-slate-800">{note}</p>)}
    </CardContent></Card>
}

function Figure({ label, value, note, strong }: { label: string; value: string; note: string; strong?: boolean }) {
  return <div className="rounded-md border p-3"><p className="text-xs font-semibold">{label}</p><p className={`${strong ? "text-xl" : "text-lg"} font-bold tabular-nums`}>{value}</p><p className="text-xs text-slate-800">{note}</p></div>
}

function Items({ explained }: { explained: Explained }) {
  const [open, setOpen] = useState<ExplainedItem["key"] | null>(null)
  const money = (ore: number | null, signed = false) => !explained.available || ore === null ? "–" : signed ? signedKr(ore) : formatKr(ore)
  const selected = explained.items.find(item => item.key === open) ?? null
  return <Card><CardHeader><CardTitle className="flex items-center gap-1.5">Kostnadsposter<InfoTip label="Om kostnadsposter">Hyrda lokaler, externa bokningar och personal (betald tid). Välj en post för att se vilka lokaler, bokningar, personalpass och tentor som förklarar den.</InfoTip></CardTitle></CardHeader>
    <CardContent className="space-y-3">
      <table className="w-full text-sm"><thead><tr className="border-b"><th className={TH}>Post</th><th className={`${TH} text-right`}>Före</th><th className={`${TH} text-right`}>Efter</th><th className={`${TH} text-right`}>Skillnad</th>
        <th className={`${TH} text-right`}>varav ändrat utnyttjande</th><th className={`${TH} text-right`}>varav priser och antaganden</th><th className="p-1.5"/></tr></thead>
        <tbody>{explained.items.map(item => <tr key={item.key} className="border-b last:border-0">
          <td className={TD}>{item.label}</td><td className={`${TD} text-right tabular-nums`}>{money(item.left_ore)}</td><td className={`${TD} text-right tabular-nums`}>{money(item.right_ore)}</td>
          <td className={`${TD} text-right font-semibold tabular-nums ${ARROW[direction(item)]}`}>{money(item.difference_ore, true)}</td>
          <td className={`${TD} text-right tabular-nums`}>{money(item.usage_ore, true)}</td><td className={`${TD} text-right tabular-nums`}>{money(item.assumption_ore, true)}</td>
          <td className="p-1.5 text-right"><button type="button" aria-expanded={open === item.key} className="text-xs font-medium underline underline-offset-2" onClick={() => setOpen(open === item.key ? null : item.key)}>
            {open === item.key ? "Dölj förklaring" : "Visa vad som förklarar"}</button></td></tr>)}
          <tr className="border-t-2 font-semibold"><td className={TD}>Totalt</td><td className={`${TD} text-right tabular-nums`}>{money(explained.total.left_ore)}</td><td className={`${TD} text-right tabular-nums`}>{money(explained.total.right_ore)}</td>
            <td className={`${TD} text-right tabular-nums`}>{money(explained.total.difference_ore, true)}</td><td colSpan={3}/></tr></tbody></table>
      {!explained.available && <p className="text-xs text-slate-800">Beloppen visas inte: underlaget är inte jämförbart (se skälen ovan). Lokaler, bokningar och personalpass nedan är fortfarande fakta om respektive alternativ.</p>}
      {selected && <ItemDetail item={selected} explained={explained}/>}
    </CardContent></Card>
}

function Realization({ explained }: { explained: Explained }) {
  const { realization } = explained
  const summary = realization.summary
  if (realization.items.length === 0) return <Card><CardHeader><CardTitle>Kan besparingen realiseras?</CardTitle></CardHeader><CardContent><p className="text-sm">Ingen lokal frigörs och ingen extern bokning undviks, så det finns ingen lokalbesparing att bedöma.</p></CardContent></Card>
  return <Card><CardHeader><CardTitle className="flex items-center gap-1.5">Kan besparingen realiseras?<InfoTip label="Om realiserbar besparing">{realization.note}</InfoTip></CardTitle></CardHeader>
    <CardContent className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-4"><Figure label="Modellbesparing" value={formatKr(summary.modelled_saving_ore)} note="Det modellen räknar som sparat"/>
        <Figure label="Verifierad" value={formatKr(summary.verified_ore)} note="Kräver observerade avtalsuppgifter"/><Figure label="Villkorad" value={formatKr(summary.conditional_ore)} note="Avtalsuppgifter saknas eller är inte verifierade"/>
        <Figure label="Frigörs inte" value={formatKr(summary.blocked_ore)} note="Delat avtal eller avtal som inte kan sägas upp"/></div>
      <p className="text-xs">{summary.note}{realization.contract_basis ? ` Avtalsuppgifter: ${realization.contract_basis.pack_id} (${ORIGIN_TEXT[realization.contract_basis.origin] ?? realization.contract_basis.origin}).` : " Inga avtalsuppgifter finns i någon av körningarna."}</p>
      <table className="w-full text-sm"><thead><tr className="border-b"><th className={TH}>Lokal</th><th className={`${TH} text-right`}>Modellbesparing</th><th className={TH}>Bedömning</th></tr></thead>
        <tbody>{realization.items.map(item => { const view = realizationView(item.realization.status); return <tr key={item.room_id} className="border-b last:border-0">
          <td className={TD}>{item.name}{item.kind === "external" && <Badge className="ml-1">extern</Badge>}</td><td className={`${TD} text-right tabular-nums`}>{formatKr(item.modelled_saving_ore)}</td>
          <td className={TD}><strong>{view.label}</strong><span className="block text-xs">{item.realization.reason}</span>
            {item.realization.contract && <span className="block text-xs text-slate-700">{item.realization.contract.name}: uppsägningstid {item.realization.contract.notice_months === null ? "okänd" : `${item.realization.contract.notice_months} mån`}, tidigast {item.realization.contract.earliest_release_date ?? "okänt"}, engångskostnad {item.realization.contract.one_off_cost_ore === null ? "okänd" : formatKr(item.realization.contract.one_off_cost_ore)}</span>}</td></tr> })}</tbody></table>
    </CardContent></Card>
}

function Kinds({ explained }: { explained: Explained }) {
  const kinds = explained.savings_kinds
  return <Card><CardHeader><CardTitle className="flex items-center gap-1.5">Fyra slags kostnad som aldrig blandas<InfoTip label="Om kostnadsslag">Historisk kostnad, modellberäknad kostnad, teoretisk årlig potential och verifierad realiserbar besparing är olika saker.</InfoTip></CardTitle></CardHeader>
    <CardContent><dl className="grid gap-2 text-sm md:grid-cols-2">
      <div className="rounded-md border p-2"><dt className="font-semibold">Historisk kostnad</dt><dd className="text-xs">{kinds.historical.available ? "Finns" : `Saknas. ${kinds.historical.note}`}</dd></div>
      <div className="rounded-md border p-2"><dt className="font-semibold">Modellberäknad skillnad</dt><dd className="text-xs">{kinds.model_calculated.difference_ore === null ? "Kan inte redovisas." : signedKr(kinds.model_calculated.difference_ore)}</dd></div>
      <div className="rounded-md border p-2"><dt className="font-semibold">Teoretisk årlig potential</dt><dd className="text-xs">{kinds.theoretical_annual_potential.available ? formatKr(kinds.theoretical_annual_potential.ore) : `Ej beräknad. ${kinds.theoretical_annual_potential.note}`}</dd></div>
      <div className="rounded-md border p-2"><dt className="font-semibold">Verifierad realiserbar besparing</dt><dd className="text-xs">{kinds.verified_realisable.available ? formatKr(kinds.verified_realisable.ore) : `Ingen. ${kinds.verified_realisable.note}`}</dd></div>
    </dl></CardContent></Card>
}
