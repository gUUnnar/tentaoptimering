import { useCallback, useState } from "react"
import type { ReactNode } from "react"
import { Activity, Database } from "lucide-react"
import JointPage from "@/components/joint/joint-page"
import UnderlayPage from "@/components/underlay/underlay-page"

type Page = "joint" | "underlay"

const TITLES: Record<Page, string> = { joint: "Optimering", underlay: "Underlag" }

function Nav({ icon, active, onClick, children }: { icon: ReactNode; active: boolean; onClick: () => void; children: ReactNode }) {
  return <button className={`nav-item ${active ? "nav-item-active" : ""}`} aria-current={active ? "page" : undefined} onClick={onClick}>{icon}{children}</button>
}

export default function App() {
  const [page, setPage] = useState<Page>("joint")
  // Räknas upp när underlaget har förberetts, så att optimeringssidan hämtar scenarierna på nytt.
  const [underlayVersion, setUnderlayVersion] = useState(0)
  const onPrepared = useCallback(() => setUnderlayVersion(version => version + 1), [])

  return <div className="flex h-screen min-w-[1024px] overflow-hidden">
    <aside className="flex w-60 shrink-0 flex-col overflow-auto border-r bg-white p-3">
      <div className="mb-6 px-2"><div className="text-lg font-semibold text-sky-950">Tentaoptimering</div><div className="text-xs text-slate-500">Lokal terminsanalys</div></div>
      <nav className="space-y-1" aria-label="Huvudmeny">
        <Nav icon={<Activity size={17}/>} active={page === "joint"} onClick={() => setPage("joint")}>Optimering</Nav>
        <Nav icon={<Database size={17}/>} active={page === "underlay"} onClick={() => setPage("underlay")}>Underlag</Nav>
      </nav>
      <div className="mt-auto rounded-md bg-slate-50 p-3 text-xs text-slate-500">Servern lyssnar endast på <code>127.0.0.1</code>.</div>
    </aside>
    <main className="min-w-0 flex-1 overflow-auto p-6">
      <h1 className="mb-5 text-xl font-semibold">{TITLES[page]}</h1>
      {/* Båda sidorna hålls monterade när man byter sida, så att ändringar, en pågående körning och en pågående förberedelse inte tappas. */}
      <div hidden={page !== "joint"}><JointPage onOpenUnderlay={() => setPage("underlay")} reloadKey={underlayVersion}/></div>
      <div hidden={page !== "underlay"}><UnderlayPage active={page === "underlay"} onPrepared={onPrepared}/></div>
    </main>
  </div>
}
