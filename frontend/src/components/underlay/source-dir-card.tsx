import { CircleAlert, CircleCheck, FolderOpen, FolderSearch } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatBytes, formatWhen } from "@/lib/underlay"
import type { SourceCheck } from "@/lib/underlayApi"
import type { Notice } from "@/lib/useUnderlay"

type Props = {
  value: string; saved: string; onChange: (value: string) => void; onSave: () => void; onBrowse: () => void
  disabled: boolean; choosing: boolean; notice: Notice | null; appDataDir: string; check: SourceCheck | null
}

/** Förhandskontroll: vilka av de förväntade Excel-filerna som finns i den angivna katalogen. */
function SourceFiles({ check }: { check: SourceCheck }) {
  if (!check.exists) return <p className="flex items-center gap-2 text-sm text-red-900" role="alert"><CircleAlert size={16} aria-hidden="true"/>Katalogen finns inte.</p>
  return <ul className="space-y-1 text-sm" aria-label="Källfiler i katalogen">
    {check.files.map(file => <li key={file.role} className="flex flex-wrap items-baseline gap-x-2">
      {file.found ? <CircleCheck size={15} className="shrink-0 translate-y-0.5 text-emerald-800" aria-label="Hittad"/> : <CircleAlert size={15} className="shrink-0 translate-y-0.5 text-red-800" aria-label="Saknas"/>}
      <span className="font-medium">{file.label}</span>
      <code className="text-xs">{file.filename}</code>
      <span className="text-xs text-slate-800">{file.found ? `${formatBytes(file.bytes)}, ändrad ${formatWhen(file.modified)}` : "saknas"}</span>
    </li>)}
  </ul>
}

/** Val av katalogen med de Excel-filer som underlaget byggs av. */
export function SourceDirCard({ value, saved, onChange, onSave, onBrowse, disabled, choosing, notice, appDataDir, check }: Props) {
  const changed = value.trim() !== saved
  return <Card>
    <CardHeader><CardTitle>1. Källdatakatalog</CardTitle></CardHeader>
    <CardContent className="space-y-3">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[320px] flex-1">
          <label className="label" htmlFor="source-dir">Mapp med Excel-källorna</label>
          <input id="source-dir" className="field" value={value} placeholder="till exempel C:\lokalt\tentalokaler\underlag" onChange={event => onChange(event.target.value)} disabled={disabled || choosing}/>
        </div>
        <Button type="button" variant="outline" onClick={onBrowse} disabled={disabled || choosing}><FolderSearch size={15} className="mr-1" aria-hidden="true"/>{choosing ? "Väljer …" : "Bläddra…"}</Button>
        <Button type="button" variant="outline" onClick={onSave} disabled={disabled || choosing || !changed}><FolderOpen size={15} className="mr-1" aria-hidden="true"/>Spara sökväg</Button>
      </div>
      {disabled && <p className="text-xs text-slate-800">Sökvägen kan inte ändras medan underlaget förbereds.</p>}
      {notice && <p role={notice.kind === "error" ? "alert" : "status"} className={`text-sm ${notice.kind === "error" ? "text-red-900" : "text-emerald-900"}`}>{notice.text}</p>}
      {check && value.trim() && <SourceFiles check={check}/>}
      <p className="text-xs text-slate-800">Originalfilerna läses bara och ändras aldrig. Det som skapas (bearbetat underlag, rapporter och körresultat) sparas lokalt för din användare{appDataDir ? <>, under <code>{appDataDir}</code></> : null}. Det bearbetade underlaget innehåller uppgifter om tentander och ligger kvar där tills det förbereds om.</p>
    </CardContent>
  </Card>
}
