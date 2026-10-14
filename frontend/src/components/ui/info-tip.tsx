import { useEffect, useId, useRef, useState, type ReactNode } from "react"
import { Info } from "lucide-react"

/**
 * Förklaring bakom en ⓘ-ikon: visas först när användaren klickar, stängs med Esc, nytt klick eller klick utanför.
 * Förklaringar och instruktioner hör hit; varningar och fel hör till `Notice`.
 */
export function InfoTip({ label, children, align = "left" }: { label: string; children: ReactNode; align?: "left" | "right" }) {
  const [open, setOpen] = useState(false)
  const id = useId()
  const box = useRef<HTMLSpanElement>(null)
  useEffect(() => {
    if (!open) return
    const outside = (event: MouseEvent) => { if (!box.current?.contains(event.target as Node)) setOpen(false) }
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false) }
    document.addEventListener("mousedown", outside)
    document.addEventListener("keydown", escape)
    return () => { document.removeEventListener("mousedown", outside); document.removeEventListener("keydown", escape) }
  }, [open])
  return <span ref={box} className="relative inline-flex align-middle">
    <button type="button" aria-expanded={open} aria-controls={open ? id : undefined} aria-label={label} title={label} onClick={() => setOpen(value => !value)}
      className="rounded-full p-0.5 text-slate-700 hover:bg-slate-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-slate-900"><Info size={15} aria-hidden="true"/></button>
    {open && <span id={id} role="note" className={`absolute top-full z-30 mt-1 block w-[min(28rem,85vw)] space-y-1.5 rounded-md border bg-white p-3 text-left text-xs font-normal leading-relaxed text-slate-900 shadow-lg ${align === "right" ? "right-0" : "left-0"}`}>{children}</span>}
  </span>
}
