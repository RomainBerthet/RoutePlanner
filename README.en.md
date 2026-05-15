# Route Planner

[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-0.4.0-111827)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-pytest-0A7E07?logo=pytest&logoColor=white)](pytest.ini)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![OSM](https://img.shields.io/badge/data-OpenStreetMap-7EBC6F?logo=openstreetmap&logoColor=white)](https://www.openstreetmap.org/)

Multi-engine route planner to build, optimize, and export routes from a list of addresses.

Route Planner provides a local web UI, a CLI, and a Python API. It supports multiple travel modes, several optimization objectives, HTML/PDF/JSON exports, and statistics tailored to the selected transport mode.

[Lire en francais](README.md)

![Route Planner demo](assets/demo_paris.png)

## Highlights

- Multi-engine routing: OSRM, OSMnx, Valhalla, GraphHopper, and BRouter.
- Travel modes: car, bike, walking.
- Stop order optimization for multi-point routes.
- Objectives: fastest, shortest, cheapest, balanced time/distance.
- Dynamic configuration by routing engine: URLs, GraphHopper API key, Valhalla service, BRouter service.
- Mode-aware fields: budget, toll avoidance, consumption, and energy cost only appear when relevant.
- Contextual statistics: cost/CO2 for car, calories/CO2 saved for bike, steps/pace/calories for walking.
- Automatic exports: interactive HTML map, PDF route sheet, and JSON payload.
- SQLite cache to reduce repeated geocoding and matrix calls.

## Installation

```bash
git clone https://github.com/RomainBerthet/RoutePlanner.git
cd RoutePlanner
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Quick check:

```bash
pytest
```

## Run The Web UI

```bash
route-planner-web --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

The interface only displays fields that make sense for the current context:

| Selection | Visible fields |
| --- | --- |
| `Car` | budget, tolls, consumption, energy cost |
| `Bike` | time/distance/balanced objectives, bike statistics |
| `Walking` | time/distance/balanced objectives, walking statistics |
| `Valhalla` | Valhalla service URL |
| `GraphHopper` | GraphHopper URL and API key |
| `BRouter` | BRouter service URL |

## CLI Usage

Simple OSRM route:

```bash
route-planner \
  --method osrm \
  --mode drive \
  --objective fastest \
  --addresses "Tour Eiffel, Paris" "Musee du Louvre, Paris" "Notre-Dame de Paris" \
  --output parcours_paris \
  --json-output parcours_paris.json
```

Bike route with BRouter:

```bash
route-planner \
  --method brouter \
  --mode bike \
  --objective balanced \
  --balanced-weight 0.4 \
  --addresses "Bastille, Paris" "Canal Saint-Martin, Paris" "Montmartre, Paris"
```

GraphHopper with an API key:

```bash
route-planner \
  --method graphhopper \
  --graphhopper-api-key "$GRAPHHOPPER_API_KEY" \
  --mode drive \
  --avoid-tolls \
  --addresses "Lyon" "Grenoble" "Chambery"
```

## Python Usage

```python
from route_planner import RoutePlanner, Vehicule

addresses = [
    "Tour Eiffel, Paris",
    "Musee du Louvre, Paris",
    "Notre-Dame de Paris",
]

vehicle = Vehicule(
    type_transport="drive",
    consommation_l_km=0.06,
    cout_energie=1.8,
)

planner = RoutePlanner(
    vehicle,
    methode_routage="osrm",
    objective="balanced",
    balanced_weight=0.6,
    avoid_tolls=True,
    budget_eur=12.0,
)

plan = planner.planifier_parcours(addresses)

print(plan.ordered_addresses)
print(plan.distance_km, plan.duration_h, plan.cost_eur)
print(plan.stats)
```

Export an HTML map:

```python
planner.exporter.exporter(plan, filename="parcours_paris")
```

## Available Routers

| Method | Recommended use | Configuration |
| --- | --- | --- |
| `osrm` | fast and simple for car/bike/walking | none by default |
| `osmnx` | local computation with an OpenStreetMap graph | none by default |
| `valhalla` | advanced profiles, toll avoidance, possible multimodal routing | `VALHALLA_URL` or web field |
| `graphhopper` | robust API, public service or local instance | `GRAPHHOPPER_API_KEY`, `GRAPHHOPPER_URL` |
| `brouter` | especially useful for bike and walking routes | `BROUTER_URL` |

Environment variables are optional if you provide values through the web UI or CLI options.

```bash
export VALHALLA_URL="http://localhost:8002"
export GRAPHHOPPER_API_KEY="..."
export GRAPHHOPPER_URL="https://graphhopper.com/api/1"
export BROUTER_URL="https://brouter.de/brouter"
```

## Optimization Objectives

| Objective | Description | Modes |
| --- | --- | --- |
| `fastest` | minimizes duration | car, bike, walking |
| `shortest_km` | minimizes distance | car, bike, walking |
| `cheapest` | minimizes energy cost | car only |
| `balanced` | time/distance compromise | car, bike, walking |

For `balanced`, `balanced_weight` controls how much duration matters:

- `0.0`: prioritize distance.
- `0.5`: equal compromise.
- `1.0`: prioritize duration.

## Exports

After a web calculation, Route Planner automatically generates:

| Format | Content |
| --- | --- |
| HTML | interactive Folium map |
| PDF | readable route sheet |
| JSON | complete route plan data |

The JSON payload includes:

```json
{
  "ordered_addresses": ["A", "B", "C"],
  "distance_km": 12.34,
  "duration_h": 0.5,
  "cost_eur": 3.21,
  "routing_engine": "OSRMRouter",
  "optimization_strategy": "exact_dp",
  "stats": {}
}
```

## Architecture

```text
src/route_planner/
├── route_planner.py          # business orchestration
├── vehicule.py               # transport profile
├── webapp.py                 # WSGI web interface
├── cli.py                    # command-line interface
├── models.py                 # RoutePlan, RouteLeg, preferences
├── optimization/
│   └── heuristics.py         # stop order optimization
├── routers/
│   ├── factory.py            # dynamic engine selection
│   ├── interface.py          # shared contract
│   ├── osrm_router.py
│   ├── osmnx_router.py
│   └── http_routers.py       # Valhalla, GraphHopper, BRouter
└── exporters/
    ├── html_exporter.py
    ├── pdf_exporter.py
    └── json_exporter.py
```

## Tests

```bash
pytest
```

The test suite covers:

- route calculation and optimization,
- routers and factory,
- web interface,
- HTML/PDF/JSON exports,
- SQLite cache,
- transport-mode-specific statistics.

## Troubleshooting

### `GraphHopper requiert GRAPHHOPPER_API_KEY`

The public GraphHopper service requires an API key. Provide it through the web UI, CLI, or environment:

```bash
export GRAPHHOPPER_API_KEY="..."
```

### `graph_from_bbox() got an unexpected keyword argument 'north'`

Recent OSMnx versions use a bbox tuple. This project is compatible with OSMnx 2.x.

### Valhalla does not respond

By default, Route Planner looks for Valhalla at:

```text
http://localhost:8002
```

Provide another URL through the web UI, `--valhalla-url`, or `VALHALLA_URL`.

## Contributing

Contributions are welcome:

1. Fork the project.
2. Create a short, explicit branch.
3. Add or update tests.
4. Run `pytest`.
5. Open a pull request.

## License

Distributed under the MIT license. See [LICENSE](LICENSE).

## Credits

- [OpenStreetMap](https://www.openstreetmap.org/)
- [OSRM](https://project-osrm.org/)
- [OSMnx](https://osmnx.readthedocs.io/)
- [Valhalla](https://valhalla.github.io/valhalla/)
- [GraphHopper](https://www.graphhopper.com/)
- [BRouter](https://brouter.de/)
- [Folium](https://python-visualization.github.io/folium/)
