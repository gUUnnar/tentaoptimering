import { FolderOpen } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Notice } from "@/lib/useUnderlay"

type Props = { value: string; saved: string; onChange: (value: string) => void; onSave: () => void; disabled: boolean; notice: Notice | null; appDataDir: string }

/** Val av katalogen med de Excel-filer som underlaget byggs av. */
export function SourceDirCard({ value, saved, onChange, onSave, disabled, notice, appDataDir }: Props) {
  const changed = value.trim() !== saved
  return <Card>
    <CardHeader><CardTitle>1. Källdatakatalog</CardTitle></CardHeader>
    <CardContent className="space-y-3">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[320px] flex-1">
          <label className="label" htmlFor="source-dir">Mapp med Excel-källorna</label>
          <input id="source-dir" className="field" value={value} placeholder="till exempel C:\lokalt\tentalokaler\underlag" onChange={event => onChange(event.target.value)} disabled={disabled}/>
        </div>
        <Button type="button" variant="outline" onClick={onSave} disabled={disabled || !changed}><FolderOpen size={15} className="mr-1" aria-hidden="true"/>Spara sökväg</Button>
      </div>
      {disabled && <p className="text-xs text-slate-800">Sökvägen kan inte ändras medan underlaget förbereds.</p>}
      {notice && <p role={notice.kind === "error" ? "alert" : "status"} className={`text-sm ${notice.kind === "error" ? "text-red-900" : "text-emerald-900"}`}>{notice.text}</p>}
      <p className="text-xs text-slate-800">Originalfilerna läses bara och ändras aldrig. Det som skapas (bearbetat underlag, rapporter och körresultat) sparas lokalt för din användare{appDataDir ? <>, under <code>{appDataDir}</code></> : null}.</p>
    </CardContent>
  </Card>
}
