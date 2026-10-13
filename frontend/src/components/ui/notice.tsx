import { useState, type ReactNode } from "react"
import { ChevronDown, CircleAlert, TriangleAlert } from "lucide-react"

const TONE = {
  warning: { box: "border-amber-700 bg-amber-50 text-amber-950", Icon: TriangleAlert },
  error: { box: "border-red-700 bg-red-50 text-red-950", Icon: CircleAlert },
}

/** Varning eller fel: rubriken syns alltid och tar lite plats; detaljerna fälls ut vid behov och är stängda från början. */
export function Notice({ tone, title, children, open = false }: { tone: keyof typeof TONE; title: ReactNode; children?: ReactNode; open?: boolean }) {
  const [shown, setShown] = useState(open)
  const { box, Icon } = TONE[tone]
  return <div role={tone === "error" ? "alert" : "status"} className={`rounded-md border-2 p-3 text-sm ${box}`}>
    <div className="flex items-start gap-2">
      <Icon size={18} className="mt-0.5 shrink-0" aria-hidden="true"/>
      <div className="min-w-0 flex-1 font-semibold">{title}</div>
      {children && <button type="button" aria-expanded={shown} onClick={() => setShown(value => !value)} className="flex shrink-0 items-center gap-1 text-xs font-medium underline-offset-2 hover:underline">
        {shown ? "Dölj" : "Visa mer"}<ChevronDown size={14} className={shown ? "rotate-180" : ""} aria-hidden="true"/></button>}
    </div>
    {children && shown && <div className="mt-2 space-y-1.5 pl-7 text-xs font-normal">{children}</div>}
  </div>
}
