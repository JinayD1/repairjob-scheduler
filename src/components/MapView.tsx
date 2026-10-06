import { useMemo } from 'react'
import type { ApplianceType, Config, DispatchOut, RouteOut } from '../api'
import type { Trace, ViewMode } from '../App'

const CELL = 22 // SVG units per grid cell
const GLYPH: Record<ApplianceType, string> = { Washer: 'W', Fridge: 'F', Oven: 'O' }

interface Props {
  config: Config
  result: DispatchOut
  assignment: (number | null)[]
  routes: RouteOut[]
  viewMode: ViewMode
  selectedTech: number | null
  selectedJob: number | null
  pendingCell: { x: number; y: number } | null
  trace: Trace | null
  onCellClick: (x: number, y: number) => void
  onSelectJob: (j: number) => void
  onPlacePin: (a: ApplianceType) => void
  onCancelPlace: () => void
  onRemoveJob: (j: number) => void
}

const cx = (x: number) => x * CELL + CELL / 2
const cy = (y: number) => y * CELL + CELL / 2
const points = (path: [number, number][]) => path.map(([x, y]) => `${cx(x)},${cy(y)}`).join(' ')

export function MapView(p: Props) {
  const { config, result, assignment, routes, trace } = p
  const grid = config.grid
  const techs = config.techs
  const width = grid.width * CELL
  const height = grid.height * CELL
  const dimTech = (t: number) => p.selectedTech !== null && p.selectedTech !== t

  // The background only depends on the (static) grid, so build it once.
  const background = useMemo(() => {
    const river = new Set(grid.river.map(([x, y]) => `${x},${y}`))
    const bridge = new Set(grid.bridges.map(([x, y]) => `${x},${y}`))
    const cells = []
    for (let y = 0; y < grid.height; y++) {
      for (let x = 0; x < grid.width; x++) {
        const walkable = grid.walkable[y][x]
        let fill = 'var(--street)'
        if (!walkable) fill = river.has(`${x},${y}`) ? 'var(--river)' : 'var(--building)'
        else if (bridge.has(`${x},${y}`)) fill = 'var(--bridge)'
        cells.push(
          <rect key={`${x}-${y}`} className={walkable ? 'cell' : 'cell blocked'} x={x * CELL} y={y * CELL} width={CELL} height={CELL} fill={fill} stroke="var(--gridline)" strokeWidth={0.5} onClick={() => p.onCellClick(x, y)} />,
        )
      }
    }
    return cells
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [grid])

  // Changes exactly when the drawn routes change, so the draw animation
  // restarts only then and not when the user merely selects something.
  const routeKey = `${p.viewMode}|${routes.map((r) => r.stops.join(',')).join('|')}`

  const exploreCells = useMemo(() => {
    if (!trace) return null
    const dj = new Set(trace.dijkstra_explored.map(String))
    const as = new Set(trace.astar_explored.map(String))
    return [...new Set([...dj, ...as])].map((key) => {
      const [x, y] = key.split(',').map(Number)
      const fill = as.has(key) && dj.has(key) ? '#fd7e14' : as.has(key) ? '#ffa94d' : '#4dabf7'
      return <rect key={key} x={x * CELL} y={y * CELL} width={CELL} height={CELL} fill={fill} opacity={0.45} />
    })
  }, [trace])

  return (
    <div className="map-wrapper">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="City map">
        <g>{background}</g>

        {exploreCells && <g pointerEvents="none">{exploreCells}</g>}
        {trace?.path && <polyline points={points(trace.path)} fill="none" stroke="#e03131" strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" pointerEvents="none" />}

        {/* Routes, drawn leg by leg with a CSS animation. */}
        <g key={routeKey} pointerEvents="none">
          {routes.map((route) => {
            let delay = 0
            return route.legs.map((leg, i) => {
              const distance = leg.distance ?? 0
              const length = distance * CELL
              const duration = Math.max(0.15, distance * 0.03)
              const style = { strokeDasharray: length, strokeDashoffset: length, animationDuration: `${duration}s`, animationDelay: `${delay}s` }
              delay += duration
              return (
                <polyline key={`${route.tech_index}-${i}`} className="route-leg" points={points(leg.path)} fill="none" stroke={techs[route.tech_index].color} strokeWidth={4} strokeOpacity={dimTech(route.tech_index) ? 0.2 : 0.85} strokeLinecap="round" strokeLinejoin="round" style={style} />
              )
            })
          })}
        </g>

        {/* Stop numbers along each route. */}
        <g pointerEvents="none">
          {routes.map((route) =>
            route.stops.map((j, i) => {
              const job = result.jobs[j]
              return (
                <text key={`${route.tech_index}-${j}`} x={cx(job.x) + 9} y={cy(job.y) - 9} fontSize={10} fontWeight={700} fill={techs[route.tech_index].color} opacity={dimTech(route.tech_index) ? 0.3 : 1}>
                  {i + 1}
                </text>
              )
            }),
          )}
        </g>

        {/* Technician homes. */}
        {techs.map((tech, t) => {
          const [x, y] = tech.home
          return (
            <g key={tech.id} opacity={dimTech(t) ? 0.35 : 1} pointerEvents="none">
              <rect x={cx(x) - 9} y={cy(y) - 9} width={18} height={18} rx={3} fill={tech.color} stroke="#fff" strokeWidth={2} />
              <text x={cx(x)} y={cy(y) + 4} fontSize={11} fontWeight={700} fill="#fff" textAnchor="middle">{tech.name[0]}</text>
              <text x={cx(x)} y={cy(y) - 13} fontSize={10} fontWeight={600} fill={tech.color} textAnchor="middle">{tech.name}</text>
            </g>
          )
        })}

        {/* Job pins: colour = assigned tech, grey = unassigned. */}
        {result.jobs.map((job, j) => {
          const t = assignment[j]
          const color = t === null ? '#868e96' : techs[t].color
          const selected = p.selectedJob === j
          return (
            <g key={job.id} className="pin" opacity={p.selectedTech !== null && t !== p.selectedTech ? 0.4 : 1} onClick={(e) => { e.stopPropagation(); p.onSelectJob(j) }}>
              <circle cx={cx(job.x)} cy={cy(job.y)} r={selected ? 10 : 8} fill="#fff" stroke={color} strokeWidth={selected ? 3.5 : 2.5} />
              <text x={cx(job.x)} y={cy(job.y) + 3.5} fontSize={9} fontWeight={700} fill={color} textAnchor="middle">{GLYPH[job.appliance]}</text>
              <text x={cx(job.x) - 9} y={cy(job.y) - 9} fontSize={9} fontWeight={600} fill="#1f2328" textAnchor="end">{j + 1}</text>
              {selected && (
                <g onClick={(e) => { e.stopPropagation(); p.onRemoveJob(j) }}>
                  <circle cx={cx(job.x) + 11} cy={cy(job.y) + 11} r={6} fill="#e03131" />
                  <text x={cx(job.x) + 11} y={cy(job.y) + 14} fontSize={9} fontWeight={700} fill="#fff" textAnchor="middle">×</text>
                </g>
              )}
            </g>
          )
        })}

        {p.pendingCell && <rect x={p.pendingCell.x * CELL} y={p.pendingCell.y * CELL} width={CELL} height={CELL} fill="none" stroke="#fab005" strokeWidth={3} pointerEvents="none" />}
      </svg>

      {p.pendingCell && (
        <div className="popover" style={{ left: `calc(${(cx(p.pendingCell.x) / width) * 100}% + 12px)`, top: `calc(${(cy(p.pendingCell.y) / height) * 100}% - 20px)` }}>
          {config.appliance_types.map((a) => (
            <button key={a} onClick={() => p.onPlacePin(a)}>{a}</button>
          ))}
          <button onClick={p.onCancelPlace}>Cancel</button>
        </div>
      )}

      <div className="legend">
        <span><i style={{ background: 'var(--street)' }} /> street</span>
        <span><i style={{ background: 'var(--building)' }} /> building</span>
        <span><i style={{ background: 'var(--river)' }} /> river</span>
        <span><i style={{ background: 'var(--bridge)' }} /> bridge</span>
        <span>W / F / O = Washer / Fridge / Oven</span>
        {trace && (
          <>
            <span><i style={{ background: '#4dabf7', opacity: 0.6 }} /> Dijkstra explored</span>
            <span><i style={{ background: '#fd7e14', opacity: 0.6 }} /> A* explored</span>
          </>
        )}
      </div>
      <p className="map-hint">
        Click an open cell to add a job pin (choose the appliance). Click a pin to see its explanation; click the red × to remove it.
        Showing the <strong>{p.viewMode}</strong> assignment. All computation runs in Python on the server.
      </p>
    </div>
  )
}
