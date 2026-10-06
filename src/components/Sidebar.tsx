import { fmt, jobLabel, type Config, type DispatchOut, type Pin } from '../api'
import type { ExploreSelection, Trace, ViewMode } from '../App'
import { TechDetail } from './TechDetail'

interface Props {
  config: Config
  result: DispatchOut
  wDistance: number
  onWDistanceChange: (w: number) => void
  viewMode: ViewMode
  onViewModeChange: (m: ViewMode) => void
  selectedTech: number | null
  onSelectTech: (t: number | null) => void
  selectedJob: number | null
  onSelectJob: (j: number | null) => void
  onRemoveJob: (j: number) => void
  onClear: () => void
  onLoadDemo: () => void
  onLoadTrap: () => void
  exploreOn: boolean
  onExploreToggle: (on: boolean) => void
  exploreSel: ExploreSelection
  onExploreSelChange: (s: ExploreSelection) => void
  trace: Trace | null
  pinCount: number
  error: string | null
}

export function jobCounts(assignment: (number | null)[], techCount: number): number[] {
  const counts = new Array<number>(techCount).fill(0)
  for (const t of assignment) if (t !== null) counts[t]++
  return counts
}

export function Sidebar(p: Props) {
  const { config, result, viewMode } = p
  const techs = config.techs
  const greedyScore = result.greedy.total_score
  const optimalScore = result.optimal?.total_score ?? null
  const pct = optimalScore && optimalScore > 0 ? (greedyScore / optimalScore) * 100 : null
  const assignment = viewMode === 'optimal' ? result.optimal!.assignment : result.greedy.assignment
  const routes = viewMode === 'optimal' ? result.optimal_routes! : result.greedy_routes
  const counts = jobCounts(assignment, techs.length)
  const drive = routes.reduce((s, r) => s + (r.total_distance ?? 0), 0)
  const unassigned = Object.entries(result.greedy.unassigned_reasons)
  const wSpecialty = Math.round((1 - p.wDistance) * 100) / 100
  const presetSize = (pins: Pin[]) => pins.length

  return (
    <aside className="sidebar">
      <section className="panel">
        <h2>Controls</h2>
        <div className="row">
          <button onClick={p.onLoadDemo}>Load demo ({presetSize(config.presets.demo)})</button>
          <button onClick={p.onLoadTrap}>Greedy trap</button>
          <button onClick={p.onClear}>Clear pins</button>
          <span className="note">{p.pinCount} / {config.max_jobs} pins</span>
        </div>

        <h3>Score weights</h3>
        <div className="slider-row">
          <span>Distance {p.wDistance.toFixed(2)}</span>
          <input type="range" min={0} max={100} step={5} value={Math.round(p.wDistance * 100)} onChange={(e) => p.onWDistanceChange(Number(e.target.value) / 100)} />
          <span>Specialty {wSpecialty.toFixed(2)}</span>
        </div>
        <p className="note">score = {p.wDistance.toFixed(2)} × closeness + {wSpecialty.toFixed(2)} × specialtyNorm</p>

        <h3>Map view</h3>
        <div className="row">
          <button className={viewMode === 'greedy' ? 'active' : ''} onClick={() => p.onViewModeChange('greedy')}>Greedy</button>
          <button className={viewMode === 'optimal' ? 'active' : ''} disabled={!result.optimal} onClick={() => p.onViewModeChange('optimal')}>Optimal</button>
        </div>
        {p.error && <p className="error">{p.error}</p>}
      </section>

      <section className="panel">
        <h2>Summary</h2>
        <dl className="stat-grid">
          <dt>Greedy total score</dt><dd>{fmt(greedyScore)}</dd>
          <dt>Optimal total score</dt><dd>{optimalScore === null ? 'n/a' : fmt(optimalScore)}</dd>
          <dt>Greedy % of optimal</dt><dd>{pct === null ? 'n/a' : `${pct.toFixed(1)}%`}</dd>
          <dt>Total drive distance ({viewMode})</dt><dd>{drive} steps</dd>
          <dt>Jobs per tech ({viewMode})</dt><dd>{techs.map((t, i) => `${t.name} ${counts[i]}`).join(' · ')}</dd>
        </dl>
        {result.optimal ? (
          <p className="note">Brute force evaluated {result.optimal.evaluated.toLocaleString()} complete assignments after pruning.</p>
        ) : (
          <p className="warn">
            Brute force is disabled above {config.brute_force_max_jobs} jobs: the number of possible assignments grows as 4^n (each job to one of 3 techs or nobody),
            so 13 jobs would already be 67 million leaves before pruning.
          </p>
        )}

        <h3>Unassigned (greedy)</h3>
        {unassigned.length === 0 ? (
          <p className="note">Every job is assigned.</p>
        ) : (
          <ul className="compact">
            {unassigned.map(([j, reason]) => (
              <li key={j}>
                <a href="#" onClick={(e) => { e.preventDefault(); p.onSelectJob(Number(j)) }}>{jobLabel(result.jobs[Number(j)], Number(j))}</a>: {result.unassigned_text[reason]}
              </li>
            ))}
          </ul>
        )}
      </section>

      {p.selectedJob !== null && p.selectedJob < result.jobs.length && (
        <section className="panel">
          <h2>{jobLabel(result.jobs[p.selectedJob], p.selectedJob)}</h2>
          <p className="note">Cell ({result.jobs[p.selectedJob].x}, {result.jobs[p.selectedJob].y})</p>
          <div className="explanation highlight">{result.explanations.greedy[p.selectedJob]}</div>
          {result.explanations.optimal && <div className="explanation">{result.explanations.optimal[p.selectedJob]}</div>}
          <div className="row">
            <button onClick={() => p.onRemoveJob(p.selectedJob!)}>Remove pin</button>
            <button onClick={() => p.onSelectJob(null)}>Close</button>
          </div>
        </section>
      )}

      <section className="panel">
        <h2>Technicians</h2>
        <div className="tech-list">
          {techs.map((tech, t) => (
            <button key={tech.id} className={`tech-card ${p.selectedTech === t ? 'selected' : ''}`} onClick={() => p.onSelectTech(p.selectedTech === t ? null : t)}>
              <span className="swatch" style={{ background: tech.color }} />
              <span>
                <strong>{tech.name}</strong>
                <div className="ratings">Washer {tech.ratings.Washer} · Fridge {tech.ratings.Fridge} · Oven {tech.ratings.Oven} · home ({tech.home[0]}, {tech.home[1]})</div>
              </span>
              <span>{counts[t]} / {tech.capacity}</span>
            </button>
          ))}
        </div>
        {p.selectedTech !== null && <TechDetail techIndex={p.selectedTech} config={config} result={result} viewMode={viewMode} onSelectJob={p.onSelectJob} />}
      </section>

      <section className="panel">
        <h2>A* vs Dijkstra</h2>
        <label className="row">
          <input type="checkbox" checked={p.exploreOn} onChange={(e) => p.onExploreToggle(e.target.checked)} />
          Show cells explored for one tech-to-job path
        </label>
        {p.exploreOn && result.jobs.length === 0 && <p className="note">Place a pin first.</p>}
        {p.exploreOn && result.jobs.length > 0 && (
          <>
            <div className="row" style={{ marginTop: 8 }}>
              <select value={p.exploreSel.techIndex} onChange={(e) => p.onExploreSelChange({ ...p.exploreSel, techIndex: Number(e.target.value) })}>
                {techs.map((t, i) => <option key={t.id} value={i}>{t.name}</option>)}
              </select>
              <span>→</span>
              <select value={Math.min(p.exploreSel.jobIndex, result.jobs.length - 1)} onChange={(e) => p.onExploreSelChange({ ...p.exploreSel, jobIndex: Number(e.target.value) })}>
                {result.jobs.map((j, i) => <option key={j.id} value={i}>{jobLabel(j, i)}</option>)}
              </select>
            </div>
            {p.trace && (
              <dl className="stat-grid" style={{ marginTop: 8 }}>
                <dt>Path length</dt><dd>{p.trace.distance === null ? 'unreachable' : `${p.trace.distance} steps`}</dd>
                <dt>Dijkstra explored</dt><dd>{p.trace.dijkstra_explored.length} cells</dd>
                <dt>A* explored</dt><dd>{p.trace.astar_explored.length} cells</dd>
              </dl>
            )}
            <p className="note">Both searches stop as soon as the goal is settled. Dijkstra expands every cell closer than the goal; A* uses the Manhattan heuristic to expand toward the goal first.</p>
          </>
        )}
      </section>
    </aside>
  )
}
