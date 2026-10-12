import { useCallback, useEffect, useMemo, useState } from "react"
import { jointApi } from "./jointApi"
import type { FieldError, ParameterInfo, ParametersResponse } from "./jointTypes"
import {
  changesToRequest, collectErrors, computeChanges, crossErrors, splitServerErrors, type EditMap, type ErrorMap, type GroupMeta, type ParamChange,
} from "./paramDiff"
import { sameValue, toDraft } from "./paramValues"

export type EditorLoad = { status: "idle" | "loading" | "ready" | "error"; error: string; response: ParametersResponse | null }

export type ParameterEditor = {
  load: EditorLoad
  params: ParameterInfo[]
  /** Läsbara gruppnamn och gruppordning från katalogen. */
  groupMeta: GroupMeta
  edits: EditMap
  changes: ParamChange[]
  /** Fel per parameter-id (eget formatfel, fel mellan parametrar och fel från servern). */
  errors: ErrorMap
  /** Serverfel som inte hör till någon parameter i listan. */
  generalErrors: string[]
  /** Värden att skicka med körningen: bara giltiga ändringar. */
  request: Record<string, unknown>
  /** Lokala fel som hindrar start. Serverfel hindrar inte ett nytt försök. */
  hasErrors: boolean
  draftFor(param: ParameterInfo): unknown
  setDraft(param: ParameterInfo, draft: unknown): void
  reset(id: string): void
  resetAll(): void
  applyServerErrors(errors: FieldError[]): void
  reload(): void
}

/** Parametrarna för ett scenario och användarens ändringar av dem. Originalscenariot ändras aldrig. */
export function useParameterEditor(scenarioId: string): ParameterEditor {
  const [load, setLoad] = useState<EditorLoad>({ status: "idle", error: "", response: null })
  const [edits, setEdits] = useState<EditMap>({})
  const [serverErrors, setServerErrors] = useState<ErrorMap>({})
  const [generalErrors, setGeneralErrors] = useState<string[]>([])
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    setEdits({}); setServerErrors({}); setGeneralErrors([])
    if (!scenarioId) { setLoad({ status: "idle", error: "", response: null }); return }
    let cancelled = false
    setLoad({ status: "loading", error: "", response: null })
    jointApi.parameters(scenarioId)
      .then(response => { if (!cancelled) setLoad({ status: "ready", error: "", response }) })
      .catch(error => { if (!cancelled) setLoad({ status: "error", error: (error as Error).message, response: null }) })
    return () => { cancelled = true }
  }, [scenarioId, attempt])

  const params = useMemo(() => load.response?.parameters ?? [], [load.response])
  const groupMeta = useMemo<GroupMeta>(() => ({ labels: load.response?.group_labels, order: load.response?.group_order }), [load.response])
  const changes = useMemo(() => computeChanges(params, edits), [params, edits])
  const localErrors = useMemo(() => collectErrors(changes, crossErrors(params, edits), {}), [changes, params, edits])
  const errors = useMemo(() => ({ ...serverErrors, ...localErrors }), [serverErrors, localErrors])
  const request = useMemo(() => changesToRequest(changes), [changes])
  const clearServerError = useCallback((id: string) => setServerErrors(current => { if (!(id in current)) return current; const { [id]: _removed, ...rest } = current; return rest }), [])

  const setDraft = useCallback((param: ParameterInfo, draft: unknown) => {
    clearServerError(param.id)
    setEdits(current => {
      if (sameValue(draft, toDraft(param))) { const { [param.id]: _removed, ...rest } = current; return rest }
      return { ...current, [param.id]: draft }
    })
  }, [clearServerError])

  return {
    load, params, groupMeta, edits, changes, errors, generalErrors, request,
    hasErrors: Object.keys(localErrors).length > 0,
    draftFor: param => param.id in edits ? edits[param.id] : toDraft(param),
    setDraft,
    reset: id => { clearServerError(id); setEdits(current => { const { [id]: _removed, ...rest } = current; return rest }) },
    resetAll: () => { setEdits({}); setServerErrors({}); setGeneralErrors([]) },
    applyServerErrors: list => { const split = splitServerErrors(list, params); setServerErrors(split.byId); setGeneralErrors(split.general) },
    reload: () => setAttempt(value => value + 1),
  }
}
