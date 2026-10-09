import { useEffect, useMemo, useState } from "react"
import type { ReactNode } from "react"
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { AlertTriangle, BarChart3, CalendarDays, FileCheck2, FolderOpen, Play, SlidersHorizontal } from "lucide-react"
import { RunComparison } from "@/components/run-comparison"
import { ScenarioEditor } from "@/components/scenario-editor"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type Parameter = { id: string; area: string; name_sv: string; unit: string; status: string; rule_status: string; definition_sv?: string; engine_binding?: string | null; implementation_status?: string }
type TermParameterBinding = { id: string; engine_binding: string; name_sv: string; unit: string; implementation_status: string; verification_status: string; source: string }
type Scenario = { id: string; name: string; description: string; engine: string; origin: string; editable: boolean; content?: Record<string, unknown> }
type Run = { run_id: string; scenario_id: string; status: string; engine: string; created_at: string }
type Page = "overview" | "parameters" | "scenarios" | "runs" | "results"

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options })
  if (!response.ok) { const error = await response.json().catch(() => ({})); throw new Error(error.detail || "Kunde inte hämta data.") }
  return response.json() as Promise<T>
}

const statusClass = (status?: string) => status === "pass" || status === "completed" ? "status-pass" : status === "fail" || status === "failed" ? "status-fail" : "status-neutral"

export default function App() {
  const [page, setPage] = useState<Page>("overview")
  const [parameters, setParameters] = useState<Parameter[]>([])
  const [termParameterBindings, setTermParameterBindings] = useState<TermParameterBinding[]>([])
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [runs, setRuns] = useState<Run[]>([])
  const [selectedScenario, setSelectedScenario] = useState<Scenario | null>(null)
  const [selectedRun, setSelectedRun] = useState<Record<string, unknown> | null>(null)
  const [validation, setValidation] = useState<Record<string, unknown> | null>(null)
  const [sourceDir, setSourceDir] = useState("")
  const [notice, setNotice] = useState("Ansluter till den lokala beräkningsmotorn …")
  const [busy, setBusy] = useState(false)

  const refresh = async () => {
    const [params, scenarioList, runList, settings] = await Promise.all([
      request<{ parameters: Parameter[]; term_parameter_bindings: TermParameterBinding[] }>("/api/parameters"), request<{ scenarios: Scenario[] }>("/api/scenarios"),
      request<{ runs: Run[] }>("/api/runs"), request<{ settings: { source_dir: string | null } }>("/api/settings"),
    ])
    setParameters(params.parameters); setTermParameterBindings(params.term_parameter_bindings); setScenarios(scenarioList.scenarios); setRuns(runList.runs); setSourceDir(settings.settings.source_dir || "")
    setNotice("Redo. Alla körningar hålls lokalt på denna dator.")
  }
  useEffect(() => { refresh().catch(error => setNotice(error.message)) }, [])

  const chooseScenario = async (id: string) => { setSelectedScenario(await request<Scenario>(`/api/scenarios/${id}`)); setPage("scenarios") }
  const chooseRun = async (id: string) => {
    const [run, post] = await Promise.all([request<Record<string, unknown>>(`/api/runs/${id}`), request<Record<string, unknown>>(`/api/runs/${id}/validation`)])
    setSelectedRun(run); setValidation(post); setPage("results")
  }
  const execute = async (path: string, success: string) => {
    setBusy(true)
    try {
      const job = await request<{ job_id: string }>(path, { method: "POST" })
      setNotice("Körningen pågår. Gränssnittet är fortfarande tillgängligt.")
      const poll = window.setInterval(async () => {
        const status = await request<{ status: string; result?: { run_id?: string }; error?: { message: string } }>(`/api/jobs/${job.job_id}`)
        if (status.status === "completed" || status.status === "failed") {
          window.clearInterval(poll); setBusy(false); setNotice(status.status === "completed" ? success : status.error?.message || "Körningen misslyckades."); await refresh()
          if (status.result?.run_id) chooseRun(status.result.run_id)
        }
      }, 800)
    } catch (error) { setBusy(false); setNotice((error as Error).message) }
  }
  const saveSource = async () => { await request("/api/settings", { method: "PUT", body: JSON.stringify({ source_dir: sourceDir || null }) }); setNotice("Källdatakatalogen är sparad i användarprofilen.") }
  const copyScenario = async () => {
    const id = window.prompt("Nytt scenarie-id (gemener, siffror och bindestreck):")
    if (!id || !selectedScenario) return
    try { const copied = await request<Scenario>("/api/scenarios", { method: "POST", body: JSON.stringify({ scenario_id: id, source_id: selectedScenario.id }) }); await refresh(); setSelectedScenario(copied); setNotice("Scenariot är kopierat och kan nu ändras.") } catch (error) { setNotice((error as Error).message) }
  }
  const validate = async () => { if (!selectedScenario) return; try { const answer = await request<{ valid: boolean; engine: string }>(`/api/scenarios/${selectedScenario.id}/validate`, { method: "POST" }); setNotice(answer.valid ? "Scenariot är tekniskt giltigt." : "Scenariot är inte giltigt.") } catch (error) { setNotice((error as Error).message) } }
  const saveScenario = async (content: Record<string, unknown>) => { if (!selectedScenario) return; try { const saved = await request<Scenario>(`/api/scenarios/${selectedScenario.id}`, { method: "PUT", body: JSON.stringify({ content }) }); setSelectedScenario(saved); await refresh(); setNotice("Scenariot är sparat. Validera det före körning.") } catch (error) { setNotice((error as Error).message) } }
  const compareRuns = (runIds: string[]) => request(`/api/runs/compare`, { method: "POST", body: JSON.stringify(runIds) })

  return <div className="flex h-screen min-w-[1024px] overflow-hidden">
    <aside className="flex w-60 shrink-0 flex-col border-r bg-white p-3">
      <div className="mb-6 px-2"><div className="text-lg font-semibold text-sky-950">Tentaoptimering</div><div className="text-xs text-slate-500">Lokal terminsanalys</div></div>
      <nav className="space-y-1">
        <Nav icon={<BarChart3 size={17}/>} active={page === "overview"} onClick={() => setPage("overview")}>Översikt</Nav>
        <Nav icon={<SlidersHorizontal size={17}/>} active={page === "parameters"} onClick={() => setPage("parameters")}>Parametrar</Nav>
        <Nav icon={<CalendarDays size={17}/>} active={page === "scenarios"} onClick={() => setPage("scenarios")}>Scenarier</Nav>
        <Nav icon={<Play size={17}/>} active={page === "runs"} onClick={() => setPage("runs")}>Simuleringar</Nav>
        <Nav icon={<FileCheck2 size={17}/>} active={page === "results"} onClick={() => setPage("results")}>Resultat</Nav>
      </nav>
      <div className="mt-auto rounded-md bg-slate-50 p-3 text-xs text-slate-500">Servern lyssnar endast på <code>127.0.0.1</code>.</div>
    </aside>
    <main className="min-w-0 flex-1 overflow-auto p-6">
      <div className="mb-5 flex items-start justify-between gap-4"><div><h1 className="text-xl font-semibold">{title(page)}</h1><p className="mt-1 text-sm text-slate-500">{notice}</p></div><Badge className={busy ? "status-neutral" : "status-pass"}>{busy ? "Beräkning pågår" : "Lokal drift"}</Badge></div>
      {page === "overview" && <Overview sourceDir={sourceDir} setSourceDir={setSourceDir} saveSource={saveSource} prepare={() => execute("/api/preparation", "Underlaget har förberetts.")} busy={busy} scenarios={scenarios} runs={runs} chooseScenario={chooseScenario}/>}
      {page === "parameters" && <Parameters parameters={parameters} bindings={termParameterBindings}/>}
      {page === "scenarios" && <Scenarios scenarios={scenarios} selected={selectedScenario} choose={chooseScenario} copy={copyScenario} validate={validate} save={saveScenario}/>}
      {page === "runs" && <Runs scenarios={scenarios} runs={runs} execute={execute} busy={busy} chooseRun={chooseRun}/>}
      {page === "results" && <Results runs={runs} selected={selectedRun} validation={validation} chooseRun={chooseRun} compare={compareRuns}/>}
    </main>
  </div>
}

function Nav({ icon, active, onClick, children }: { icon: ReactNode; active: boolean; onClick: () => void; children: ReactNode }) { return <button className={`nav-item ${active ? "nav-item-active" : ""}`} onClick={onClick}>{icon}{children}</button> }
function title(page: Page) { return ({ overview: "Översikt", parameters: "Parametrar och regelstatus", scenarios: "Scenarier", runs: "Simuleringar", results: "Resultat och eftervalidering" })[page] }

function Overview({ sourceDir, setSourceDir, saveSource, prepare, busy, scenarios, runs, chooseScenario }: { sourceDir: string; setSourceDir: (value: string) => void; saveSource: () => void; prepare: () => void; busy: boolean; scenarios: Scenario[]; runs: Run[]; chooseScenario: (id: string) => void }) {
  return <div className="grid max-w-6xl gap-4 xl:grid-cols-3"><Card className="xl:col-span-2"><CardHeader><CardTitle>Starta en reproducerbar analys</CardTitle></CardHeader><CardContent><div className="grid gap-3 sm:grid-cols-[1fr_auto_auto]"><div><label className="label">Källdatakatalog</label><input className="field" value={sourceDir} placeholder="Välj mapp med Excel-källor" onChange={e => setSourceDir(e.target.value)}/></div><Button variant="outline" className="self-end" onClick={saveSource}><FolderOpen size={15} className="mr-1"/>Spara sökväg</Button><Button className="self-end" disabled={busy || !sourceDir} onClick={prepare}>Förbered underlag</Button></div><p className="mt-3 text-xs text-slate-500">Originaldata läses från vald plats. Scenarier, bearbetade data och resultat sparas i en användarskrivbar lokal katalog.</p></CardContent></Card><Card><CardHeader><CardTitle>Aktivt underlag</CardTitle></CardHeader><CardContent><div className="space-y-2 text-sm"><div><span className="text-slate-500">Scenarier</span><strong className="float-right">{scenarios.length}</strong></div><div><span className="text-slate-500">Sparade körningar</span><strong className="float-right">{runs.length}</strong></div><div className="border-t pt-2 text-xs text-amber-700">Verksamhetsregler utan verifierat underlag visas alltid som ej verifierade.</div></div></CardContent></Card><Card className="xl:col-span-3"><CardHeader><CardTitle>Fortsätt med ett scenario</CardTitle></CardHeader><CardContent><div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">{scenarios.filter(item => item.engine === "integrated_term").map(item => <button key={item.id} className="rounded-md border p-3 text-left hover:border-sky-500" onClick={() => chooseScenario(item.id)}><div className="flex justify-between gap-2"><strong className="text-sm">{item.name}</strong><Badge>{item.origin === "user" ? "Eget" : "Inbyggt"}</Badge></div><p className="mt-1 line-clamp-2 text-xs text-slate-500">{item.description}</p></button>)}</div></CardContent></Card></div>
}

function Parameters({ parameters, bindings }: { parameters: Parameter[]; bindings: TermParameterBinding[] }) {
  const groups = useMemo(() => Object.entries(parameters.reduce<Record<string, Parameter[]>>((all, item) => { (all[item.area] ||= []).push(item); return all }, {})), [parameters])
  return <div className="max-w-6xl space-y-4">
    <Card><CardHeader><CardTitle>Terminsmotorns redigerbara parametrar</CardTitle></CardHeader><CardContent><p className="mb-3 text-xs text-slate-500">Varje rad visar den faktiska TOML-sökvägen, om den används av terminsmotorn och om verksamhetsunderlaget är verifierat. Ändra dem i scenarieformuläret, inte i JSON.</p><div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left text-xs text-slate-500"><th className="p-2">Parameter</th><th className="p-2">Beräkningsparameter</th><th className="p-2">Motor</th><th className="p-2">Underlag</th></tr></thead><tbody>{bindings.map(item => <tr className="border-b" key={item.id}><td className="p-2"><div className="font-medium">{item.name_sv}</div><div className="text-xs text-slate-500">{item.unit}</div></td><td className="p-2 font-mono text-xs">{item.engine_binding}</td><td className="p-2"><Badge className={item.implementation_status.startsWith("implemented") ? "status-pass" : "status-neutral"}>{item.implementation_status}</Badge></td><td className="p-2 text-xs text-slate-500">{item.verification_status}</td></tr>)}</tbody></table></div></CardContent></Card>
    <div className="grid gap-4 lg:grid-cols-2">{groups.map(([area, items]) => <Card key={area}><CardHeader><CardTitle>{area.replace(/_/g, " ")}</CardTitle></CardHeader><CardContent><div className="divide-y">{items.map(item => <div key={item.id} className="grid grid-cols-[1fr_auto] gap-3 py-2.5"><div><div className="text-sm font-medium">{item.name_sv}</div><div className="text-xs text-slate-500">{item.unit} · {item.definition_sv || item.id}</div>{item.engine_binding && <div className="mt-1 font-mono text-[11px] text-slate-500">{item.engine_binding}</div>}</div><div className="flex flex-col items-end gap-1"><Badge className={statusClass(item.status)}>{item.status}</Badge><span className="text-[11px] text-slate-500">{item.implementation_status || item.rule_status}</span></div></div>)}</div></CardContent></Card>)}</div>
  </div>
}

function Scenarios({ scenarios, selected, choose, copy, validate, save }: { scenarios: Scenario[]; selected: Scenario | null; choose: (id: string) => void; copy: () => void; validate: () => void; save: (content: Record<string, unknown>) => void }) { return <div className="grid max-w-6xl gap-4 lg:grid-cols-[300px_1fr]"><Card><CardHeader><CardTitle>Sparade scenarier</CardTitle></CardHeader><CardContent className="space-y-1">{scenarios.map(item => <button key={item.id} className={`w-full rounded-md p-2 text-left hover:bg-slate-50 ${selected?.id === item.id ? "bg-sky-50" : ""}`} onClick={() => choose(item.id)}><div className="flex justify-between gap-2 text-sm font-medium"><span>{item.name}</span><Badge>{item.engine === "integrated_term" ? "Termin" : "Äldre"}</Badge></div><div className="mt-1 text-xs text-slate-500">{item.origin === "user" ? "Användarscenario" : "Inbyggd mall"}</div></button>)}</CardContent></Card><Card>{selected ? <><CardHeader><div className="flex items-start justify-between gap-3"><div><CardTitle>{selected.name}</CardTitle><p className="mt-1 text-xs text-slate-500">{selected.description}</p></div><div className="flex gap-2"><Button size="sm" variant="outline" onClick={validate}>Validera</Button><Button size="sm" onClick={copy}>Kopiera</Button></div></div></CardHeader><CardContent><ScenarioEditor content={selected.content || {}} editable={selected.editable} save={save}/><div className="mt-4 rounded-md bg-amber-50 p-3 text-xs text-amber-800"><AlertTriangle size={14} className="mr-1 inline"/>Ändringar görs i en kopia. Parametrar med saknat datastöd blir inte godkända genom scenarioval.</div></CardContent></> : <CardContent>Välj ett scenario för att granska dess kalender, kostnad och regelantaganden.</CardContent>}</Card></div> }


function Runs({ scenarios, runs, execute, busy, chooseRun }: { scenarios: Scenario[]; runs: Run[]; execute: (path: string, success: string) => void; busy: boolean; chooseRun: (id: string) => void }) { const [scenarioId, setScenarioId] = useState(""); const selected = scenarios.find(item => item.id === scenarioId); return <div className="grid max-w-6xl gap-4 xl:grid-cols-[1fr_380px]"><Card><CardHeader><CardTitle>Starta simulering</CardTitle></CardHeader><CardContent><label className="label">Scenario</label><select className="field" value={scenarioId} onChange={e => setScenarioId(e.target.value)}><option value="">Välj validerat scenario</option>{scenarios.map(item => <option key={item.id} value={item.id}>{item.name} · {item.engine === "integrated_term" ? "termin" : "äldre"}</option>)}</select>{selected?.engine !== "integrated_term" && selected && <p className="mt-2 text-xs text-amber-700">Äldre motor ger inte den fristående termins-eftervalideringen.</p>}<Button className="mt-4" disabled={busy || !scenarioId} onClick={() => execute(`/api/simulations?scenario_id=${encodeURIComponent(scenarioId)}`, "Simuleringen är klar och eftervaliderad.")}><Play size={15} className="mr-1"/>Starta lokal simulering</Button></CardContent></Card><Card><CardHeader><CardTitle>Senaste körningar</CardTitle></CardHeader><CardContent className="space-y-2">{runs.slice(0, 5).map(run => <button key={run.run_id} onClick={() => chooseRun(run.run_id)} className="flex w-full items-center justify-between rounded-md border p-2 text-left text-xs hover:border-sky-500"><span>{run.scenario_id}</span><Badge className={statusClass(run.status)}>{run.status}</Badge></button>)}{!runs.length && <p className="text-sm text-slate-500">Inga sparade körningar ännu.</p>}</CardContent></Card></div> }

function Results({ runs, selected, validation, chooseRun, compare }: { runs: Run[]; selected: Record<string, unknown> | null; validation: Record<string, unknown> | null; chooseRun: (id: string) => void; compare: (ids: string[]) => Promise<any> }) { const solution = (selected?.solution || {}) as Record<string, number | string>; const technical = validation?.technical_placement_completeness as { status?: string; reason?: string } | undefined; const business = validation?.business_feasibility as { status?: string; reason?: string } | undefined; const validationRows = Array.isArray(validation?.rules) ? validation?.rules as Array<{ rule_id: string; status: string; reason?: string }> : []; const data = [{ name: "Lokaler", value: Number(solution.room_count || 0) }, { name: "Vaktpool", value: Number(solution.anonymous_staff_pool_size || 0) }, { name: "Placeringar", value: Number(solution.assignment_rows || 0) }]; return <div className="grid max-w-6xl gap-4 xl:grid-cols-[260px_1fr]"><Card><CardHeader><CardTitle>Körningar</CardTitle></CardHeader><CardContent className="space-y-1">{runs.map(run => <button key={run.run_id} className="w-full rounded-md border p-2 text-left text-xs hover:border-sky-500" onClick={() => chooseRun(run.run_id)}>{run.scenario_id}<div className="mt-1"><Badge className={statusClass(run.status)}>{run.status}</Badge></div></button>)}</CardContent></Card>{selected ? <div className="space-y-4"><div className="grid gap-4 md:grid-cols-3"><Metric title="Målfunktion" value={solution.objective_ore ? `${(Number(solution.objective_ore) / 100).toLocaleString("sv-SE")} kr` : "Ej tillämpligt"}/><Metric title="Lokaler" value={String(solution.room_count ?? "–")}/><Metric title="Anonym vaktpool" value={String(solution.anonymous_staff_pool_size ?? "–")}/></div><Card><CardHeader><CardTitle>Resursöversikt</CardTitle></CardHeader><CardContent><div className="h-48"><ResponsiveContainer width="100%" height="100%"><BarChart data={data}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="name"/><YAxis allowDecimals={false}/><Tooltip/><Bar dataKey="value" fill="#075985" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></div></CardContent></Card><Card><CardHeader><CardTitle>Fristående eftervalidering</CardTitle></CardHeader><CardContent>{validationRows.length ? <><div className="mb-3 grid gap-2 sm:grid-cols-2"><div className="rounded-md bg-slate-50 p-2 text-xs"><strong>Teknisk placering</strong><div className="mt-1"><Badge className={statusClass(technical?.status)}>{technical?.status || "not_evaluated"}</Badge></div><p className="mt-1 text-slate-500">{technical?.reason}</p></div><div className="rounded-md bg-slate-50 p-2 text-xs"><strong>Verksamhetsmässig genomförbarhet</strong><div className="mt-1"><Badge className={statusClass(business?.status)}>{business?.status || "not_evaluated"}</Badge></div><p className="mt-1 text-slate-500">{business?.reason}</p></div></div><div className="divide-y">{validationRows.map(row => <div className="flex items-start justify-between gap-4 py-2" key={row.rule_id}><div><div className="text-sm font-medium">{row.rule_id}</div><div className="text-xs text-slate-500">{row.reason}</div></div><Badge className={statusClass(row.status)}>{row.status}</Badge></div>)}</div></> : <p className="text-sm text-amber-700">{String(validation?.reason || validation?.status || "Eftervalidering saknas.")}</p>}</CardContent></Card><RunComparison runs={runs} compare={compare}/></div> : <Card><CardContent>Välj en körning för resultat, resursmått och regelvis eftervalidering.</CardContent></Card>}</div> }
function Metric({ title, value }: { title: string; value: string }) { return <Card><CardHeader><CardTitle>{title}</CardTitle></CardHeader><CardContent><div className="text-2xl font-semibold">{value}</div></CardContent></Card> }
