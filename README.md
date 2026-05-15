# Route Planner

[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-0.4.0-111827)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-pytest-0A7E07?logo=pytest&logoColor=white)](pytest.ini)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![OSM](https://img.shields.io/badge/data-OpenStreetMap-7EBC6F?logo=openstreetmap&logoColor=white)](https://www.openstreetmap.org/)

Planificateur d'itineraire multi-moteurs pour construire, optimiser et exporter des parcours a partir d'une liste d'adresses.

Route Planner combine une interface web locale, un CLI et une API Python. Il gere plusieurs modes de deplacement, plusieurs objectifs d'optimisation, des exports HTML/PDF/JSON et des statistiques adaptees au mode choisi.

[Read in English](README.en.md)

![Demo Route Planner](assets/demo_paris.png)

## Points Forts

- Routage multi-moteurs : OSRM, OSMnx, Valhalla, GraphHopper et BRouter.
- Modes de deplacement : voiture, velo, marche.
- Optimisation de l'ordre des etapes des parcours multi-points.
- Objectifs : plus rapide, plus court, moins couteux, equilibre temps/distance.
- Configuration dynamique selon le moteur choisi : URLs, cle API GraphHopper, service Valhalla, service BRouter.
- Champs adaptes au mode : budget, peages, consommation et cout energie uniquement quand ils sont pertinents.
- Statistiques contextualisees : cout/CO2 en voiture, calories/CO2 evite en velo, pas/allure/calories en marche.
- Exports automatiques : carte HTML interactive, feuille PDF et donnees JSON.
- Cache SQLite pour limiter les appels repetes de geocodage et de matrices.

## Installation

```bash
git clone https://github.com/RomainBerthet/RoutePlanner.git
cd RoutePlanner
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Verification rapide :

```bash
pytest
```

## Lancer L'Interface Web

```bash
route-planner-web --host 127.0.0.1 --port 8000
```

Ouvrez ensuite :

```text
http://127.0.0.1:8000
```

L'interface affiche uniquement les champs utiles au contexte :

| Selection | Champs visibles |
| --- | --- |
| `Voiture` | budget, peages, consommation, cout energie |
| `Velo` | objectifs temps/distance/equilibre, stats velo |
| `Marche` | objectifs temps/distance/equilibre, stats marche |
| `Valhalla` | URL du service Valhalla |
| `GraphHopper` | URL GraphHopper et cle API |
| `BRouter` | URL du service BRouter |

## Utilisation CLI

Calcul simple avec OSRM :

```bash
route-planner \
  --method osrm \
  --mode drive \
  --objective fastest \
  --addresses "Tour Eiffel, Paris" "Musee du Louvre, Paris" "Notre-Dame de Paris" \
  --output parcours_paris \
  --json-output parcours_paris.json
```

Exemple velo avec BRouter :

```bash
route-planner \
  --method brouter \
  --mode bike \
  --objective balanced \
  --balanced-weight 0.4 \
  --addresses "Bastille, Paris" "Canal Saint-Martin, Paris" "Montmartre, Paris"
```

Exemple GraphHopper avec cle API :

```bash
route-planner \
  --method graphhopper \
  --graphhopper-api-key "$GRAPHHOPPER_API_KEY" \
  --mode drive \
  --avoid-tolls \
  --addresses "Lyon" "Grenoble" "Chambery"
```

## Utilisation Python

```python
from route_planner import RoutePlanner, Vehicule

adresses = [
    "Tour Eiffel, Paris",
    "Musee du Louvre, Paris",
    "Notre-Dame de Paris",
]

vehicule = Vehicule(
    type_transport="drive",
    consommation_l_km=0.06,
    cout_energie=1.8,
)

planner = RoutePlanner(
    vehicule,
    methode_routage="osrm",
    objective="balanced",
    balanced_weight=0.6,
    avoid_tolls=True,
    budget_eur=12.0,
)

plan = planner.planifier_parcours(adresses)

print(plan.ordered_addresses)
print(plan.distance_km, plan.duration_h, plan.cost_eur)
print(plan.stats)
```

Exporter une carte HTML :

```python
planner.exporter.exporter(plan, filename="parcours_paris")
```

## Routeurs Disponibles

| Methode | Usage recommande | Configuration |
| --- | --- | --- |
| `osrm` | rapide, simple, efficace pour voiture/velo/marche | aucune par defaut |
| `osmnx` | calcul local via graphe OpenStreetMap | aucune par defaut |
| `valhalla` | profils avances, peages, multi-modalite possible | `VALHALLA_URL` ou champ web |
| `graphhopper` | API robuste, service public ou instance locale | `GRAPHHOPPER_API_KEY`, `GRAPHHOPPER_URL` |
| `brouter` | tres pertinent pour velo et marche | `BROUTER_URL` |

Les variables d'environnement restent optionnelles si vous renseignez les champs dans l'interface web ou les options CLI.

```bash
export VALHALLA_URL="http://localhost:8002"
export GRAPHHOPPER_API_KEY="..."
export GRAPHHOPPER_URL="https://graphhopper.com/api/1"
export BROUTER_URL="https://brouter.de/brouter"
```

## Objectifs D'Optimisation

| Objectif | Description | Modes |
| --- | --- | --- |
| `fastest` | minimise la duree | voiture, velo, marche |
| `shortest_km` | minimise la distance | voiture, velo, marche |
| `cheapest` | minimise le cout energie | voiture uniquement |
| `balanced` | compromis temps/distance | voiture, velo, marche |

Pour `balanced`, `balanced_weight` controle l'importance du temps :

- `0.0` : priorite distance.
- `0.5` : compromis equivalent.
- `1.0` : priorite duree.

## Exports

Apres calcul depuis l'interface web, Route Planner genere automatiquement :

| Format | Contenu |
| --- | --- |
| HTML | carte interactive Folium |
| PDF | feuille de route lisible |
| JSON | donnees completes du plan |

Le payload JSON contient notamment :

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
├── route_planner.py          # orchestration metier
├── vehicule.py               # profil de transport
├── webapp.py                 # interface web WSGI
├── cli.py                    # interface ligne de commande
├── models.py                 # RoutePlan, RouteLeg, preferences
├── optimization/
│   └── heuristics.py         # optimisation de l'ordre des etapes
├── routers/
│   ├── factory.py            # selection dynamique du moteur
│   ├── interface.py          # contrat commun
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

L'ensemble couvre :

- calcul de parcours et optimisation,
- routeurs et factory,
- interface web,
- exports HTML/PDF/JSON,
- cache SQLite,
- statistiques par mode de deplacement.

## Depannage

### `GraphHopper requiert GRAPHHOPPER_API_KEY`

Le service public GraphHopper demande une cle API. Fournissez-la via l'interface, le CLI ou l'environnement :

```bash
export GRAPHHOPPER_API_KEY="..."
```

### `graph_from_bbox() got an unexpected keyword argument 'north'`

Les versions recentes d'OSMnx utilisent un tuple de bbox. Le projet est compatible avec OSMnx 2.x.

### Valhalla ne repond pas

Par defaut, Route Planner cherche Valhalla sur :

```text
http://localhost:8002
```

Renseignez une autre URL via l'interface, `--valhalla-url` ou `VALHALLA_URL`.

## Contribution

Les contributions sont bienvenues :

1. Fork du projet.
2. Creation d'une branche courte et explicite.
3. Ajout ou mise a jour des tests.
4. Lancement de `pytest`.
5. Ouverture d'une pull request.

## Licence

Projet distribue sous licence MIT. Voir [LICENSE](LICENSE).

## Credits

- [OpenStreetMap](https://www.openstreetmap.org/)
- [OSRM](https://project-osrm.org/)
- [OSMnx](https://osmnx.readthedocs.io/)
- [Valhalla](https://valhalla.github.io/valhalla/)
- [GraphHopper](https://www.graphhopper.com/)
- [BRouter](https://brouter.de/)
- [Folium](https://python-visualization.github.io/folium/)
