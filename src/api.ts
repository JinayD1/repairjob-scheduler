/**
 * Types for the JSON the Python backend returns, and the three fetch calls.
 *
 * These mirror dispatch/api.py one to one. The frontend never computes a
 * score, a path or an assignment itself; it only renders what comes back.
 * `null` in a distance field means "unreachable" (JSON cannot carry inf).
 */

export type ApplianceType = 'Washer' | 'Fridge' | 'Oven'

export interface Pin {
  x: number
  y: number
  appliance: ApplianceType
}

export interface TechConfig {
  id: number
  name: string
  color: string
  home: [number, number]
  ratings: Record<ApplianceType, number>
  capacity: number
}

export interface Config {
  grid: { width: number; height: number; walkable: boolean[][]; river: [number, number][]; bridges: [number, number][] }
  techs: TechConfig[]
  presets: { demo: Pin[]; trap: Pin[] }
  appliance_types: ApplianceType[]
  max_jobs: number
  brute_force_max_jobs: number
  default_weights: { w_distance: number; w_specialty: number }
}

export interface JobOut {
  id: number
  x: number
  y: number
  appliance: ApplianceType
}

export interface PairOut {
  distance: number | null
  closeness: number
  rating: number
  specialty_norm: number
  score: number
  eligible: boolean
  ineligible_reason: 'rating' | 'unreachable' | null
}

export type UnassignedReason = 'unreachable' | 'no-eligible-tech' | 'all-eligible-at-capacity'

export interface RouteOut {
  tech_index: number
  stops: number[]
  legs: { job_index: number; distance: number | null; path: [number, number][] }[]
  total_distance: number | null
}

export interface DispatchOut {
  weights: { w_distance: number; w_specialty: number }
  jobs: JobOut[]
  max_distance: number | null
  /** table[techIndex][jobIndex] */
  table: PairOut[][]
  greedy: {
    assignment: (number | null)[]
    total_score: number
    unassigned_reasons: Record<string, UnassignedReason>
    log: { step: number; tech_index: number; job_index: number; score: number; outcome: string }[]
  }
  greedy_routes: RouteOut[]
  optimal: { assignment: (number | null)[]; total_score: number; evaluated: number } | null
  optimal_routes: RouteOut[] | null
  explanations: { greedy: string[]; optimal: string[] | null }
  unassigned_text: Record<UnassignedReason, string>
}

export interface ExploreOut {
  path: [number, number][] | null
  distance: number | null
  astar_explored: [number, number][]
  dijkstra_explored: [number, number][]
}

async function request<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!res.ok) throw new Error(`${path} failed with ${res.status}`)
  return (await res.json()) as T
}

export const fetchConfig = () => request<Config>('/api/config')
export const fetchDispatch = (pins: Pin[], wDistance: number) => request<DispatchOut>('/api/dispatch', { pins, w_distance: wDistance })
export const fetchExplore = (techIndex: number, x: number, y: number) => request<ExploreOut>('/api/explore', { tech_index: techIndex, x, y })

export const jobLabel = (job: JobOut, j: number) => `Job ${j + 1} (${job.appliance})`
export const fmt = (s: number) => s.toFixed(2)
