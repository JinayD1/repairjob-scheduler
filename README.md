# Technician Dispatch Demo

An interactive demo of a technician dispatch system for appliance repair.
You drop job pins on a grid city; the system assigns each job to one of three
technicians, orders each technician's stops into a route, draws the routes,
and explains every decision in plain English. It also computes the true
optimal assignment by brute force so you can see exactly how much the greedy
heuristic gives up.

- **Backend: Python**, standard library only. Every algorithm lives in
  `dispatch/` and runs as Vercel serverless functions in `api/`.
- **Frontend: Vite + React + TypeScript** in `src/`. It does no arithmetic of
  its own; every score, assignment, route, explanation and explored cell
  comes back from the Python API as JSON.

There are no LLMs, no calls to anything external, and no randomness at
runtime. Every result is a deterministic function of the pins, the technician
config, and the weight slider.

## Run it locally

```bash
npm install                # once
npm run dev                # starts the Python API (:8000) and Vite (:5173)
```

`npm run dev` runs `dev.mjs`, which starts `python3 dev_server.py` and the
Vite dev server together. Vite proxies `/api/*` to the Python process. If
you prefer two terminals, `npm run dev:api` and `npm run dev:web` start them
separately.

Other commands:

```bash
python3 -m unittest        # 62 backend tests, no pytest needed
npm run build              # typecheck + static frontend build into dist/
python3 demo.py            # terminal version: ASCII map + explanations
python3 demo.py trap       # the greedy-trap layout
python3 demo.py explore    # cells explored by A* vs Dijkstra for one path
```

Python 3.10 or newer and Node 20 or newer.

## What the demo does

- **Map**: a 40 x 28 grid with building blocks and a river crossed by exactly
  two bridges. Movement is 4-directional, one step per cell.
- **Technicians**: Maria, Dev and Sam, each with a fixed home, a colour, a
  1-5 specialty rating per appliance type (Washer, Fridge, Oven) and a
  capacity of 4 jobs. All of this lives in `dispatch/config.py`.
- **Jobs**: click any open cell to add a pin (max 15) and choose its
  appliance type. Click a pin to see its explanation; the red × removes it.
- **Scoring**: every (tech, job) pair gets a score blending closeness and
  specialty. The slider changes the weights and recomputes everything.
- **Greedy assignment** with a full decision log, **nearest-next-stop
  routing**, and animated route drawing.
- **Optimal comparison**: for 12 or fewer jobs, an exhaustive search finds
  the best possible assignment. The sidebar shows greedy as a percentage of
  optimal, and you can toggle the map between the two.
- **Presets**: "Load demo" (10 pins) and "Greedy trap" (a layout where greedy
  reaches only about 77% of optimal).
- **A\* vs Dijkstra**: an overlay that colours the cells each search explored
  for one tech-to-job path, with counts, so the effect of the heuristic is
  visible.

## How each algorithm works

All algorithm code is in `dispatch/`, and each file opens with a long comment
written for someone meeting the algorithm for the first time. Read them in
this order:

| File | What it does |
|---|---|
| `dispatch/types.py` | the dataclasses every other module uses |
| `dispatch/grid.py` | the map, neighbours, Manhattan distance |
| `dispatch/dijkstra.py` | shortest paths from one cell to every cell |
| `dispatch/astar.py` | shortest path to one goal, guided by a heuristic |
| `dispatch/scoring.py` | closeness, specialty, the weighted score, eligibility |
| `dispatch/greedy.py` | best-pair-first assignment with a decision log |
| `dispatch/routing.py` | nearest-next-stop ordering of each tech's jobs |
| `dispatch/bruteforce.py` | the true optimum by exhaustive search with pruning |
| `dispatch/explain.py` | English sentences built from the decision log |
| `dispatch/pipeline.py` | `run_dispatch()`: everything in one call |
| `dispatch/config.py` | technicians, the city map, preset pin layouts |
| `dispatch/api.py` | JSON views of the results for the frontend |
| `dispatch/web.py` | the HTTP request handler shared by dev_server.py and api/ |

Short versions:

**Dijkstra**. Single-source shortest paths. Start at the source with distance
0 and keep a priority queue (`heapq`) of discovered cells ordered by
tentative distance. Repeatedly pop the closest cell, mark it final, and offer
each neighbour a shorter distance through it. Because every step costs at
least 1, the closest frontier cell can never be improved by a longer route,
which is what makes the popped distance final. One run from a technician's
home gives that tech's distance to every cell, so one run per home and one
per job fills the whole distance matrix.

**A\***. Dijkstra with a sense of direction. Instead of ordering the frontier
by cost-so-far `g`, it uses `f = g + h` where `h` is the Manhattan distance
to the goal. Manhattan distance never over-estimates the real distance on a
4-directional grid (it is "admissible"), so the first time the goal is
popped the path is guaranteed shortest. The heuristic just makes A\* look at
far fewer cells. Ties on `f` are broken toward the smaller `h`, which keeps
the search marching at the goal. A test checks on hundreds of random grids
that A\*'s path length always equals Dijkstra's distance.

**Scoring**. For each pair, `closeness = 1 - distance / max_distance` (max
over all reachable pairs on the map), `specialty_norm = (rating - 1) / 4`,
and `score = w_distance * closeness + w_specialty * specialty_norm`. A rating
of 1 or an unreachable job makes the pair ineligible regardless of score.

**Greedy assignment**. Sort all eligible pairs by score descending, with ties
broken by shorter distance, then lower tech index, then lower job index. Walk
the list and take a pair whenever the job is still free and the tech has
room. Every examined pair is written to a decision log with its outcome,
which the explain module turns into sentences like "Sam scored higher (0.64)
but was already at capacity when this pair was reached". Jobs are indexed in
a canonical order (by row, then column) so the result never depends on the
order pins were placed.

**Nearest-next-stop routing**. From home, repeatedly go to the closest
not-yet-visited assigned job using the Dijkstra distance matrix. A\* then
produces the actual cells of each leg for drawing.

**Brute force**. Depth-first search over jobs in index order; at each job
branch over every eligible tech with spare capacity, plus "unassigned".
Branches that would exceed capacity are never created. A leaf is accepted
only if every unassigned job genuinely has no eligible tech with room left.
A branch-and-bound check (current score plus the best each remaining job
could possibly get) prunes subtrees that cannot beat the best found so far,
so 12 jobs finish in well under a second. The result is identical to naive
enumeration, which a test verifies on random instances.

## How the frontend talks to Python

`dispatch/web.py` holds one request handler with three routes. The local dev
server (`dev_server.py`) and each Vercel function in `api/` use that same class,
so development and production run identical code.

| Route | Purpose |
|---|---|
| `GET /api/config` | the map, technicians, presets and limits, fetched once |
| `POST /api/dispatch` | pins plus the distance weight in, the full result out |
| `POST /api/explore` | one tech and one job in, both explored-cell sets out |

`src/api.ts` declares TypeScript types that mirror `dispatch/api.py` field
for field. `null` in a distance means unreachable, since JSON cannot carry
infinity.

## Deploying to Vercel

The repo is laid out the way Vercel expects for a Vite frontend with Python
functions: the Vite app at the root and one `.py` file per route in `api/`.

1. Push the repo to GitHub (or GitLab / Bitbucket).
2. In Vercel, "Add New Project" and import the repo. **Check that the
   Framework Preset says "Vite"** before deploying. `vercel.json` sets it too,
   but the dashboard setting must not say "Python" (see below).
3. Deploy. The site is live at `https://<project>.vercel.app`, with `/api/*`
   served by the Python functions. Python 3.12 is pinned by `.python-version`.

From the command line: `npx vercel` for a preview, `npx vercel --prod` for
production.

### If `/api/config` returns 502

Vercel has a generic "Python" framework preset that is detected whenever a
`requirements.txt`, `pyproject.toml` or `Pipfile` exists at the root. That
preset takes precedence over file-based functions: it looks for a single app
entrypoint (`app.py`, `index.py`, `server.py` or `main.py` exporting `app`)
and routes every request, including `/api/*`, to it. The functions in `api/`
are then never deployed and `/api/config` fails with a 502.

This repo avoids the trigger on purpose: there is no `requirements.txt`
(the backend has no dependencies) and the dev server is named
`dev_server.py`, not `server.py`. If a project was imported before, open its
Settings → General → Framework Preset, set it to **Vite**, and redeploy. Do
not add a `requirements.txt` or `pyproject.toml` unless you also move to
Vercel's single-entrypoint layout.

Each function is cold-started on first use and reruns the whole pipeline per
request. On the 40 x 28 map that takes well under 100 ms, including the
12-job brute force.

## Project layout

```
api/               Vercel serverless functions (config, dispatch, explore)
dispatch/          the algorithms, pure Python; web.py is the HTTP layer
src/               React + TypeScript frontend (api.ts, App.tsx, components/)
dev_server.py      local Python API server for development
dev.mjs            `npm run dev`: starts the Python API and Vite together
demo.py            terminal demo
tests/             unittest suite, one file per area
vercel.json        Python runtime for api/*.py
vite.config.ts     dev proxy from /api to the Python server
```

## Limitations

- **Scoring uses distance from home, not marginal route cost.** Each pair is
  scored by how far the job is from the technician's home. A real dispatcher
  cares how much a job adds to the route the tech is already driving: a job
  far from home but next to an existing stop is cheap, and this scoring
  cannot see that.
- **No time windows, parts readiness, or traffic.** Every job is available
  all day, every tech has every part, and every step costs the same. Real
  systems weigh appointment windows, skills, inventory, and travel-time
  estimates that change by hour.
- **Nearest-next-stop routing is not optimal.** It is a greedy heuristic for
  ordering stops and can be beaten even on three stops (see
  `tests/test_routing_pipeline.py` for a concrete case). Optimal ordering is
  the travelling salesman problem.
- **Brute force only works for tiny inputs.** The search space grows as
  (techs + 1) to the power of jobs, so it is disabled above 12 jobs. Real
  dispatch is a vehicle routing problem with constraints, and production
  systems use mixed-integer or constraint solvers, local search, or
  metaheuristics rather than exhaustive enumeration.
- **Closeness is normalised by the current maximum distance**, so adding or
  removing a far-away pin shifts every score a little. This keeps scores in
  [0, 1] for any map size but makes individual numbers less stable than a
  fixed scale would.
