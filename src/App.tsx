import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchConfig, fetchDispatch, fetchExplore, type ApplianceType, type Config, type DispatchOut, type ExploreOut, type Pin } from './api'
import { MapView } from './components/MapView'
import { Sidebar } from './components/Sidebar'

export type ViewMode = 'greedy' | 'optimal'

export interface ExploreSelection {
  techIndex: number
  jobIndex: number
}

export type Trace = ExploreOut & ExploreSelection

/**
 * The app holds the user's inputs (pins, weight, selections) and asks the
 * Python backend for everything else. Every change to pins or the weight
 * triggers one POST /api/dispatch; the response is the single source of
 * truth for the map and the sidebar.
 */
export default function App() {
  const [config, setConfig] = useState<Config | null>(null)
  const [pins, setPins] = useState<Pin[]>([])
  const [wDistance, setWDistance] = useState(0.6)
  const [result, setResult] = useState<DispatchOut | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [viewMode, setViewMode] = useState<ViewMode>('greedy')
  const [selectedTech, setSelectedTech] = useState<number | null>(null)
  /** Index into result.jobs (canonical order from the backend). */
  const [selectedJob, setSelectedJob] = useState<number | null>(null)
  const [pendingCell, setPendingCell] = useState<{ x: number; y: number } | null>(null)
  const [exploreOn, setExploreOn] = useState(false)
  const [exploreSel, setExploreSel] = useState<ExploreSelection>({ techIndex: 0, jobIndex: 0 })
  const [trace, setTrace] = useState<Trace | null>(null)

  // Load the static config once, then start with the demo layout.
  useEffect(() => {
    fetchConfig()
      .then((c) => {
        setConfig(c)
        setWDistance(c.default_weights.w_distance)
        setPins(c.presets.demo)
      })
      .catch((e) => setError(String(e)))
  }, [])

  // Recompute whenever pins or the weight change. A request counter drops
  // stale responses if the user changes things faster than the server replies.
  const requestId = useRef(0)
  useEffect(() => {
    if (!config) return
    const id = ++requestId.current
    setBusy(true)
    fetchDispatch(pins, wDistance)
      .then((r) => {
        if (id !== requestId.current) return
        setResult(r)
        setError(null)
        setSelectedJob((j) => (j !== null && j >= r.jobs.length ? null : j))
      })
      .catch((e) => setError(String(e)))
      .finally(() => {
        if (id === requestId.current) setBusy(false)
      })
  }, [config, pins, wDistance])

  // Explore trace: depends on the toggle, the selection, and the job list.
  useEffect(() => {
    if (!exploreOn || !result || result.jobs.length === 0) {
      setTrace(null)
      return
    }
    const jobIndex = Math.min(exploreSel.jobIndex, result.jobs.length - 1)
    const job = result.jobs[jobIndex]
    let cancelled = false
    fetchExplore(exploreSel.techIndex, job.x, job.y)
      .then((t) => {
        if (!cancelled) setTrace({ ...t, techIndex: exploreSel.techIndex, jobIndex })
      })
      .catch((e) => setError(String(e)))
    return () => {
      cancelled = true
    }
  }, [exploreOn, exploreSel, result])

  const handleCellClick = useCallback(
    (x: number, y: number) => {
      if (!config || !result) return
      if (!config.grid.walkable[y][x]) return
      if (config.techs.some((t) => t.home[0] === x && t.home[1] === y)) return
      const existing = result.jobs.findIndex((j) => j.x === x && j.y === y)
      if (existing >= 0) {
        setSelectedJob(existing)
        setPendingCell(null)
        return
      }
      if (pins.length >= config.max_jobs) return
      setPendingCell({ x, y })
    },
    [config, result, pins.length],
  )

  function placePin(appliance: ApplianceType) {
    if (!pendingCell) return
    setPins((prev) => [...prev, { ...pendingCell, appliance }])
    setPendingCell(null)
    setSelectedJob(null)
  }

  function removeJob(jobIndex: number) {
    if (!result) return
    const job = result.jobs[jobIndex]
    setPins((prev) => prev.filter((p) => !(p.x === job.x && p.y === job.y)))
    setSelectedJob(null)
  }

  function loadPins(next: Pin[]) {
    setPins(next.map((p) => ({ ...p })))
    setSelectedJob(null)
    setPendingCell(null)
  }

  if (!config || !result) {
    return (
      <div className="app">
        {error ? (
          <div className="error">
            <p>Could not reach the Python backend: {error}</p>
            <p className="note">
              Locally, run <code>npm run dev</code> (which starts both the Python API and Vite) or start <code>python3 dev_server.py</code> alongside Vite.
              On Vercel, make sure the project's Framework Preset is "Vite" so the files in <code>api/</code> are deployed as Python functions.
            </p>
          </div>
        ) : (
          <p className="note">Loading…</p>
        )}
      </div>
    )
  }

  const effectiveView: ViewMode = viewMode === 'optimal' && result.optimal ? 'optimal' : 'greedy'
  const assignment = effectiveView === 'optimal' ? result.optimal!.assignment : result.greedy.assignment
  const routes = effectiveView === 'optimal' ? result.optimal_routes! : result.greedy_routes

  return (
    <div className="app">
      <div>
        <MapView
          config={config}
          result={result}
          assignment={assignment}
          routes={routes}
          viewMode={effectiveView}
          selectedTech={selectedTech}
          selectedJob={selectedJob}
          pendingCell={pendingCell}
          trace={trace}
          onCellClick={handleCellClick}
          onSelectJob={(j) => { setSelectedJob(j); setPendingCell(null) }}
          onPlacePin={placePin}
          onCancelPlace={() => setPendingCell(null)}
          onRemoveJob={removeJob}
        />
      </div>
      <Sidebar
        config={config}
        result={result}
        wDistance={wDistance}
        onWDistanceChange={setWDistance}
        viewMode={effectiveView}
        onViewModeChange={setViewMode}
        selectedTech={selectedTech}
        onSelectTech={setSelectedTech}
        selectedJob={selectedJob}
        onSelectJob={setSelectedJob}
        onRemoveJob={removeJob}
        onClear={() => loadPins([])}
        onLoadDemo={() => loadPins(config.presets.demo)}
        onLoadTrap={() => loadPins(config.presets.trap)}
        exploreOn={exploreOn}
        onExploreToggle={setExploreOn}
        exploreSel={exploreSel}
        onExploreSelChange={setExploreSel}
        trace={trace}
        pinCount={pins.length}
        error={error}
      />
      <div className="status">{busy ? 'computing in Python…' : ''}</div>
    </div>
  )
}
