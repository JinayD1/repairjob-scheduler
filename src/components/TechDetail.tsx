import { fmt, jobLabel, type Config, type DispatchOut } from '../api'
import type { ViewMode } from '../App'

interface Props {
  techIndex: number
  config: Config
  result: DispatchOut
  viewMode: ViewMode
  onSelectJob: (j: number) => void
}

/**
 * Per-technician table of every job with the scoring breakdown and status,
 * plus the explanation for each job this tech holds. All numbers and all
 * sentences come from the backend payload.
 */
export function TechDetail({ techIndex, config, result, viewMode, onSelectJob }: Props) {
  const techs = config.techs
  const tech = techs[techIndex]
  const assignment = viewMode === 'optimal' ? result.optimal!.assignment : result.greedy.assignment

  function status(j: number): { text: string; className: string } {
    const pair = result.table[techIndex][j]
    const holder = assignment[j]
    if (holder === techIndex) return { text: `assigned to ${tech.name}`, className: 'mine' }
    if (!pair.eligible) return { text: pair.ineligible_reason === 'unreachable' ? 'unreachable' : 'ineligible (rating 1)', className: 'ineligible' }
    if (holder === null) return { text: 'unassigned', className: '' }
    return { text: `assigned to ${techs[holder].name}`, className: '' }
  }

  const mine = result.jobs.map((_, j) => j).filter((j) => assignment[j] === techIndex)

  return (
    <div>
      <h3>{tech.name}: every job ({viewMode})</h3>
      {result.jobs.length === 0 ? (
        <p className="note">No jobs on the map.</p>
      ) : (
        <table className="job-table">
          <thead>
            <tr><th>Job</th><th>Dist</th><th>Close</th><th>Rating</th><th>Score</th><th>Status</th></tr>
          </thead>
          <tbody>
            {result.jobs.map((job, j) => {
              const pair = result.table[techIndex][j]
              const s = status(j)
              return (
                <tr key={job.id} className={`${s.className} clickable`} onClick={() => onSelectJob(j)} title="Show explanation">
                  <td>{jobLabel(job, j)}</td>
                  <td>{pair.distance === null ? '∞' : pair.distance}</td>
                  <td>{pair.closeness.toFixed(2)}</td>
                  <td>{pair.rating}</td>
                  <td>{fmt(pair.score)}</td>
                  <td>{s.text}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}

      <h3>Why {tech.name} has these jobs</h3>
      {mine.length === 0 ? (
        <p className="note">No jobs assigned.</p>
      ) : (
        mine.map((j) => (
          <div key={j} className="explanation">
            {viewMode === 'optimal' && result.explanations.optimal && <p>{result.explanations.optimal[j]}</p>}
            <p>{result.explanations.greedy[j]}</p>
          </div>
        ))
      )}
    </div>
  )
}
