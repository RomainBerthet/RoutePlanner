from __future__ import annotations

import argparse
import html
import json
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from route_planner.exporters.html_exporter import HTMLExporter
from route_planner.exporters.json_exporter import JSONExporter
from route_planner.exporters.pdf_exporter import PDFExporter
from route_planner.models import RoutePlan
from route_planner.route_planner import RoutePlanner
from route_planner.vehicule import Vehicule


APP_TITLE = "Route Planner"
STATIC_ROOT = Path(tempfile.gettempdir()) / "route_planner_web"
STATIC_ROOT.mkdir(parents=True, exist_ok=True)
EXPORT_ROOT = STATIC_ROOT / "exports"
EXPORT_ROOT.mkdir(parents=True, exist_ok=True)

MODE_LABELS = {
    "drive": "Voiture",
    "bike": "Velo",
    "walk": "Marche",
}
OBJECTIVE_LABELS = {
    "fastest": "Plus rapide",
    "shortest_km": "Plus court",
    "cheapest": "Moins couteux",
    "balanced": "Equilibre",
}
OBJECTIVES_BY_MODE = {
    "drive": {"fastest", "shortest_km", "cheapest", "balanced"},
    "bike": {"fastest", "shortest_km", "balanced"},
    "walk": {"fastest", "shortest_km", "balanced"},
}


def create_app():
    def app(environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")

        if method in {"GET", "HEAD"} and path == "/":
            status, headers, body = _render_form()
        elif method == "POST" and path == "/plan":
            status, headers, body = _handle_plan(environ)
        elif method in {"GET", "HEAD"} and (path.startswith("/files/") or path.startswith("/maps/")):
            status, headers, body = _serve_asset(path)
        else:
            status, headers, body = "404 Not Found", [("Content-Type", "text/plain; charset=utf-8")], b"Not Found"

        if method == "HEAD":
            body = b""
        start_response(status, headers)
        return [body]

    return app


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    with make_server(host, port, create_app()) as server:
        print(f"Route Planner web app running at http://{host}:{port}")
        server.serve_forever()


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="route-planner-web")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    run(args.host, args.port)
    return 0


def _render_form(values: Dict[str, str] | None = None, error: str = ""):
    values = values or {}
    addresses = _addresses_html(values.get("addresses", ""))
    body = _page(
        title=APP_TITLE,
        content=f"""
        <section class="hero">
          <div>
            <p class="eyebrow">Planification de tournées</p>
            <h2>Construire un itineraire propre, rapide et exportable</h2>
            <p class="lede">Saisissez plusieurs adresses, choisissez un objectif de calcul, puis recuperez directement la carte HTML, la feuille de route PDF et les donnees JSON.</p>
          </div>
        </section>

        <div class="layout">
          <section class="panel">
            <form method="post" action="/plan" class="form-grid" id="planner-form">
              <div class="section-title">
                <h3>Adresses</h3>
                <p>Ajoutez au moins deux points. L'ordre peut etre optimise automatiquement.</p>
              </div>
              <div id="addresses" class="addresses">{addresses}</div>
              <button type="button" class="secondary" onclick="addAddress()">Ajouter une adresse</button>

              <div class="split">
                <label>Methode de routage
                  <select name="method" id="method">
                    {_select_option("osrm", values.get("method", "osrm"), "OSRM")}
                    {_select_option("osmnx", values.get("method", "osrm"), "OSMnx")}
                    {_select_option("valhalla", values.get("method", "osrm"), "Valhalla")}
                    {_select_option("graphhopper", values.get("method", "osrm"), "GraphHopper")}
                    {_select_option("brouter", values.get("method", "osrm"), "BRouter")}
                  </select>
                </label>
                <label>Mode de transport
                  <select name="mode" id="mode">
                    {_select_option("drive", values.get("mode", "drive"), "Voiture")}
                    {_select_option("bike", values.get("mode", "drive"), "Velo")}
                    {_select_option("walk", values.get("mode", "drive"), "Marche")}
                  </select>
                </label>
              </div>

              <div class="context-strip">
                <div>
                  <span>Methode</span>
                  <strong id="method-help-title">OSRM</strong>
                  <p id="method-help" class="help-copy"></p>
                </div>
                <div>
                  <span>Mode actif</span>
                  <strong id="mode-help-title">Voiture</strong>
                  <p id="mode-help" class="help-copy"></p>
                </div>
              </div>

              <section class="method-config" data-methods="valhalla">
                <div class="section-title">
                  <h3>Configuration Valhalla</h3>
                  <p>Renseignez l'URL de votre service Valhalla si elle differe de la valeur par defaut.</p>
                </div>
                <label>URL Valhalla
                  <input name="valhalla_url" type="url" value="{html.escape(values.get('valhalla_url', ''))}" placeholder="http://localhost:8002">
                </label>
              </section>

              <section class="method-config" data-methods="graphhopper">
                <div class="section-title">
                  <h3>Configuration GraphHopper</h3>
                  <p>Utilisez une cle API pour le service public, ou une URL locale si vous hebergez GraphHopper.</p>
                </div>
                <div class="split">
                  <label>URL GraphHopper
                    <input name="graphhopper_url" type="url" value="{html.escape(values.get('graphhopper_url', ''))}" placeholder="https://graphhopper.com/api/1">
                  </label>
                  <label>Cle API GraphHopper
                    <input name="graphhopper_api_key" type="password" value="{html.escape(values.get('graphhopper_api_key', ''))}" placeholder="Optionnel si URL locale">
                  </label>
                </div>
              </section>

              <section class="method-config" data-methods="brouter">
                <div class="section-title">
                  <h3>Configuration BRouter</h3>
                  <p>Renseignez l'URL du service BRouter si vous n'utilisez pas le service public.</p>
                </div>
                <label>URL BRouter
                  <input name="brouter_url" type="url" value="{html.escape(values.get('brouter_url', ''))}" placeholder="https://brouter.de/brouter">
                </label>
              </section>

              <div class="split">
                <label>Objectif de calcul
                  <select name="objective" id="objective">
                    {_select_option("fastest", values.get("objective", "fastest"), "Aller au plus vite")}
                    {_select_option("shortest_km", values.get("objective", "fastest"), "Plus court en km")}
                    {_select_option("cheapest", values.get("objective", "fastest"), "Le moins couteux")}
                    {_select_option("balanced", values.get("objective", "fastest"), "Equilibre temps / distance")}
                  </select>
                </label>
                <label>Poids du temps
                  <input name="balanced_weight" id="balanced_weight" type="number" step="0.05" min="0" max="1" value="{html.escape(values.get('balanced_weight', '0.5'))}">
                </label>
              </div>

              <section class="mode-config" data-modes="drive">
                <div class="section-title">
                  <h3>Budget et peages</h3>
                  <p>Parametres disponibles uniquement pour la voiture.</p>
                </div>
                <div class="split budget-row">
                  <label class="budget-field">Budget maximal (€)
                    <input name="budget" type="number" step="0.01" min="0" value="{html.escape(values.get('budget', ''))}" placeholder="Optionnel">
                  </label>
                  <label class="checkbox inline">
                    <input type="checkbox" name="avoid_tolls" {"checked" if values.get("avoid_tolls") else ""}>
                    Eviter les peages
                  </label>
                </div>
              </section>

              <section class="mode-config" data-modes="drive">
                <div class="section-title">
                  <h3>Profil vehicule</h3>
                  <p>Visible pour la voiture: la vitesse, le cout et les peages peuvent influencer le resultat.</p>
                </div>
                <div class="split">
                  <label>Consommation / km
                    <input name="consumption" type="number" step="0.001" min="0" value="{html.escape(values.get('consumption', '0.06'))}">
                  </label>
                  <label>Cout energie
                    <input name="energy_cost" type="number" step="0.01" min="0" value="{html.escape(values.get('energy_cost', '1.8'))}">
                  </label>
                </div>
              </section>

              <section class="mode-config" data-modes="bike">
                <div class="section-title">
                  <h3>Profil velo</h3>
                  <p>Les peages ne sont pas pertinents en velo. Le mode utilise uniquement les objectifs temps, distance et equilibre.</p>
                </div>
                <div class="mode-facts">
                  <div><span>Critere principal</span><strong>Temps ou distance</strong></div>
                  <div><span>Cout</span><strong>0 €</strong></div>
                  <div><span>Stats</span><strong>Calories, CO2 evite</strong></div>
                </div>
              </section>

              <section class="mode-config" data-modes="walk">
                <div class="section-title">
                  <h3>Profil marche</h3>
                  <p>La marche retire elle aussi budget et peages. Elle garde les reglages utiles au temps, a la distance et au compromis.</p>
                </div>
                <div class="mode-facts">
                  <div><span>Critere principal</span><strong>Temps ou distance</strong></div>
                  <div><span>Cout</span><strong>0 €</strong></div>
                  <div><span>Stats</span><strong>Pas, allure, calories</strong></div>
                </div>
              </section>

              <button type="submit" class="primary">Calculer</button>
            </form>
            {f'<div class="error">{html.escape(error)}</div>' if error else ''}
          </section>

          <aside class="panel sidebar">
            <div class="section-title">
              <h3>Lecture rapide</h3>
            </div>
            <div class="hint-list">
              <div>
                <strong>OSRM</strong>
                <p>Le plus rapide pour produire un trajet routier fiable. Supporte l'exclusion des peages sur le profil voiture.</p>
              </div>
              <div>
                <strong>OSMnx</strong>
                <p>Alternative locale pour construire un graphe et calculer sans service externe quand le reseau OSM suffit.</p>
              </div>
              <div>
                <strong>Valhalla</strong>
                <p>Routeur avance pour profils voiture, velo et marche, avec options fines comme l'evitement des peages.</p>
              </div>
              <div>
                <strong>GraphHopper</strong>
                <p>API rapide et robuste. Utilise GRAPHHOPPER_API_KEY pour le service public, ou GRAPHHOPPER_URL pour une instance locale.</p>
              </div>
              <div>
                <strong>BRouter</strong>
                <p>Tres utile pour le velo et la marche. Sa matrice publique n'etant pas standard, l'optimisation garde une estimation de secours.</p>
              </div>
              <div>
                <strong>Objectifs</strong>
                <p>Fastest optimise le temps, shortest_km la distance, cheapest le cout, balanced un compromis controle par le poids du temps.</p>
              </div>
            </div>
          </aside>
        </div>

        <script>
        const METHOD_HELP = {{
          osrm: {{
            title: "OSRM",
            copy: "Recommande pour la meilleure reactivite. Les durees reelles alimentent aussi l'optimisation de l'ordre des etapes."
          }},
          osmnx: {{
            title: "OSMnx",
            copy: "Alternative locale ou de secours. Le graphe OpenStreetMap est construit autour des points avant calcul."
          }},
          valhalla: {{
            title: "Valhalla",
            copy: "Ideal pour profils avances voiture, velo et marche. Configurez VALHALLA_URL si le service ne tourne pas sur localhost:8002."
          }},
          graphhopper: {{
            title: "GraphHopper",
            copy: "API rapide pour voiture, velo et marche. Le service public demande GRAPHHOPPER_API_KEY; une instance locale peut utiliser GRAPHHOPPER_URL."
          }},
          brouter: {{
            title: "BRouter",
            copy: "Tres pertinent pour velo et marche. Le trajet vient de BRouter, tandis que l'ordre des etapes utilise une matrice estimee."
          }}
        }};
        const MODE_HELP = {{
          drive: {{
            title: "Voiture",
            copy: "Tous les criteres sont actifs: temps, distance, cout, budget et peages lorsque le moteur le supporte."
          }},
          bike: {{
            title: "Velo",
            copy: "Budget, peages et cout carburant sont neutralises. Les statistiques mettent en avant calories et CO2 evite."
          }},
          walk: {{
            title: "Marche",
            copy: "Seuls temps, distance et equilibre pilotent l'itineraire. Les statistiques affichent allure, pas et calories."
          }}
        }};
        const OBJECTIVES_BY_MODE = {{
          drive: ["fastest", "shortest_km", "cheapest", "balanced"],
          bike: ["fastest", "shortest_km", "balanced"],
          walk: ["fastest", "shortest_km", "balanced"]
        }};

        function addAddress(value = '') {{
          const root = document.getElementById('addresses');
          const row = document.createElement('div');
          row.className = 'address-row';
          row.innerHTML = `
            <input name="addresses" type="text" value="${{value}}">
            <button type="button" class="icon" onclick="this.parentElement.remove()">Supprimer</button>
          `;
          root.appendChild(row);
        }}

        function updateMethodHelp() {{
          const method = document.getElementById('method').value;
          const help = METHOD_HELP[method] || METHOD_HELP.osrm;
          document.getElementById('method-help-title').textContent = help.title;
          document.getElementById('method-help').textContent = help.copy;
          document.querySelectorAll('.method-config').forEach((section) => {{
            const methods = section.dataset.methods.split(' ');
            const active = methods.includes(method);
            section.classList.toggle('is-hidden', !active);
            section.querySelectorAll('input, select, textarea').forEach((field) => {{
              field.disabled = !active;
            }});
          }});
        }}

        function updateModeConfig() {{
          const mode = document.getElementById('mode').value;
          const modeHelp = MODE_HELP[mode] || MODE_HELP.drive;
          const objective = document.getElementById('objective');
          const allowedObjectives = OBJECTIVES_BY_MODE[mode] || OBJECTIVES_BY_MODE.drive;
          document.getElementById('mode-help-title').textContent = modeHelp.title;
          document.getElementById('mode-help').textContent = modeHelp.copy;
          Array.from(objective.options).forEach((option) => {{
            const allowed = allowedObjectives.includes(option.value);
            option.disabled = !allowed;
            option.hidden = !allowed;
          }});
          if (!allowedObjectives.includes(objective.value)) {{
            objective.value = 'fastest';
          }}
          document.querySelectorAll('.mode-config').forEach((section) => {{
            const modes = section.dataset.modes.split(' ');
            const active = modes.includes(mode);
            section.classList.toggle('is-hidden', !active);
            section.querySelectorAll('input, select, textarea').forEach((field) => {{
              field.disabled = !active;
            }});
          }});
          updateObjectiveDefaults();
        }}

        function updateObjectiveDefaults() {{
          const objective = document.getElementById('objective').value;
          const balanced = document.getElementById('balanced_weight');
          balanced.disabled = objective !== 'balanced';
          balanced.closest('label').classList.toggle('is-muted', objective !== 'balanced');
        }}

        window.addEventListener('load', () => {{
          if (!document.querySelector('.address-row')) {{
            addAddress();
            addAddress();
          }}
          updateMethodHelp();
          updateModeConfig();
          updateObjectiveDefaults();
          document.getElementById('method').addEventListener('change', updateMethodHelp);
          document.getElementById('mode').addEventListener('change', updateModeConfig);
          document.getElementById('objective').addEventListener('change', updateObjectiveDefaults);
        }});
        </script>
        """,
    )
    return "200 OK", [("Content-Type", "text/html; charset=utf-8")], body.encode("utf-8")


def _handle_plan(environ):
    payload = _read_form(environ)
    try:
        addresses = _parse_addresses(payload)
        vehicule = Vehicule(
            type_transport=payload.get("mode", ["drive"])[0],
            consommation_l_km=float(payload.get("consumption", ["0.06"])[0]),
            cout_energie=float(payload.get("energy_cost", ["1.8"])[0]),
        )
        budget_value = payload.get("budget", [""])[0].strip()
        budget = float(budget_value) if budget_value else None
        planner = RoutePlanner(
            vehicule,
            methode_routage=payload.get("method", ["osrm"])[0],
            objective=payload.get("objective", ["fastest"])[0],
            avoid_tolls="avoid_tolls" in payload,
            budget_eur=budget,
            balanced_weight=float(payload.get("balanced_weight", ["0.5"])[0]),
            router_options=_router_options_from_payload(payload),
        )
        plan = planner.planifier_parcours(addresses)
        exports = _save_exports(plan)
        status, headers, body = _render_result(plan, exports)
        return status, headers, body
    except Exception as exc:
        values = {
            "addresses": "\n".join(payload.get("addresses", [])),
            "method": payload.get("method", ["osrm"])[0],
            "mode": payload.get("mode", ["drive"])[0],
            "objective": payload.get("objective", ["fastest"])[0],
            "consumption": payload.get("consumption", ["0.06"])[0],
            "energy_cost": payload.get("energy_cost", ["1.8"])[0],
            "budget": payload.get("budget", [""])[0],
            "balanced_weight": payload.get("balanced_weight", ["0.5"])[0],
            "valhalla_url": payload.get("valhalla_url", [""])[0],
            "graphhopper_url": payload.get("graphhopper_url", [""])[0],
            "graphhopper_api_key": payload.get("graphhopper_api_key", [""])[0],
            "brouter_url": payload.get("brouter_url", [""])[0],
            "output": payload.get("output", ["route"])[0],
            "json_output": payload.get("json_output", [""])[0],
            "skip_html": "skip_html" in payload,
            "avoid_tolls": "avoid_tolls" in payload,
        }
        return _render_form(values, error=str(exc))


def _router_options_from_payload(payload: Dict[str, List[str]]) -> Dict[str, str]:
    options = {}
    for field in ("valhalla_url", "graphhopper_url", "graphhopper_api_key", "brouter_url"):
        value = payload.get(field, [""])[0].strip()
        if value:
            options[field] = value
    return options


def _render_result(plan: RoutePlan, exports: Dict[str, str]):
    transport_mode = plan.preferences.get("transport_mode", "drive")
    objective = plan.preferences.get("objective", "fastest")
    mode_summary = _render_mode_summary(plan, str(transport_mode), str(objective))
    legs_html = "".join(
        f"""
        <tr>
          <td>{idx + 1}</td>
          <td>{html.escape(step.depart)}</td>
          <td>{html.escape(step.arrivee)}</td>
          <td>{step.distance_km:.3f}</td>
          <td>{step.duree_h * 60:.1f}</td>
          <td>{html.escape(step.resume)}</td>
        </tr>
        """
        for idx, step in enumerate(plan.legs)
    )
    map_url = exports.get("html")
    map_block = f'<iframe src="{html.escape(map_url)}" class="map-frame"></iframe>' if map_url else '<div class="empty-state">Carte HTML non exportee pour cette execution.</div>'
    warnings_html = ""
    if plan.warnings:
        warnings_html = "<ul class='warnings'>" + "".join(
            f"<li>{html.escape(warning)}</li>" for warning in plan.warnings
        ) + "</ul>"
    export_cards = ""
    if exports:
        export_cards = f"""
        <section class="panel">
          <div class="section-title">
            <h2>Exports</h2>
            <p>Tous les fichiers sont deja generes et prets a etre telecharges.</p>
          </div>
          <div class="export-grid">
            {f'<a class="export-card" href="{html.escape(exports["html"])}" download>Télécharger HTML</a>' if exports.get("html") else ''}
            {f'<a class="export-card" href="{html.escape(exports["pdf"])}" download>Feuille de route PDF</a>' if exports.get("pdf") else ''}
            {f'<a class="export-card" href="{html.escape(exports["json"])}" download>Données JSON</a>' if exports.get("json") else ''}
          </div>
        </section>
        """
    top_stats_html = _render_top_stats(plan)
    stats_html = _render_mode_stats(plan)
    body = _page(
        title=f"{APP_TITLE} - Resultat",
        content=f"""
        {mode_summary}
        {top_stats_html}
        <section class="panel">
          <div class="section-title">
            <h2>Statistiques completes</h2>
            <p>Les indicateurs affiches changent selon le mode de deplacement pour rester utiles et lisibles.</p>
          </div>
          {stats_html}
        </section>
        {warnings_html}
        <section class="panel">
          <h2>Ordre optimise</h2>
          <p>{html.escape(" -> ".join(plan.ordered_addresses))}</p>
          {map_block}
        </section>
        {export_cards}
        <section class="panel">
          <h2>Etapes</h2>
          <table>
            <thead>
              <tr><th>#</th><th>Depart</th><th>Arrivee</th><th>km</th><th>min</th><th>Resume</th></tr>
            </thead>
            <tbody>{legs_html}</tbody>
          </table>
        </section>
        <section class="panel">
          <details class="compact-data">
            <summary>Donnees</summary>
            <pre>{html.escape(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))}</pre>
          </details>
        </section>
        """,
    )
    return "200 OK", [("Content-Type", "text/html; charset=utf-8")], body.encode("utf-8")


def _render_mode_summary(plan: RoutePlan, transport_mode: str, objective: str) -> str:
    metrics = [
        ("Mode", _mode_label(transport_mode)),
        ("Objectif", _objective_label(objective)),
        ("Routeur", plan.routing_engine),
    ]
    if plan.optimization_strategy and plan.optimization_strategy != "none":
        metrics.append(("Optimisation", plan.optimization_strategy))
    cards = "".join(
        f'<div class="stat"><span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong></div>'
        for label, value in metrics
    )
    return f'<section class="summary mode-summary">{cards}</section>'


def _render_top_stats(plan: RoutePlan) -> str:
    mode = plan.preferences.get("transport_mode", "drive")
    metrics = [
        ("Distance", f"{plan.distance_km:.2f} km"),
        ("Duree", f"{plan.duration_h * 60:.1f} min"),
    ]
    if mode == "drive":
        metrics.extend([
            ("Cout", f"{plan.cost_eur:.2f} €"),
            ("CO2", f"{plan.stats.get('co2_car_kg', 0):.3f} kg"),
        ])
    elif mode == "bike":
        metrics.extend([
            ("Calories", f"{plan.stats.get('calories_estimees_kcal', 0):.1f} kcal"),
            ("CO2 evite", f"{plan.stats.get('co2_saved_vs_car_bike_kg', 0):.3f} kg"),
        ])
    else:
        metrics.extend([
            ("Allure", f"{plan.stats.get('temps_par_km_min', 0):.1f} min/km"),
            ("Pas", f"{plan.stats.get('pas_estimes', 0):d}"),
        ])
    cards = "".join(
        f'<div class="stat"><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></div>'
        for label, value in metrics
    )
    return f'<section class="summary">{cards}</section>'


def _render_mode_stats(plan: RoutePlan) -> str:
    mode = plan.preferences.get("transport_mode", "drive")
    distance = plan.stats.get("distance_km", 0.0)
    duration = plan.stats.get("duration_min", 0.0)
    steps = max(len(plan.legs), 1)
    common = [
        ("Vitesse moyenne", f"{plan.stats.get('average_speed_kmh', 0):.2f} km/h"),
        ("Distance totale", f"{distance:.2f} km"),
        ("Temps total", f"{duration:.1f} min"),
        ("Distance moyenne / etape", f"{distance / steps:.2f} km"),
        ("Temps moyen / etape", f"{duration / steps:.1f} min"),
    ]
    if mode == "drive":
        metrics = common + [
            ("Coût total", f"{plan.stats.get('cost_eur', 0):.2f} €"),
            ("CO2 voiture", f"{plan.stats.get('co2_car_kg', 0):.3f} kg"),
            ("Intensite carbone", f"{plan.stats.get('carbon_intensity_g_per_km', 0):.2f} g/km"),
            ("Péages", "Evites" if plan.preferences.get("avoid_tolls") else "Non demandes"),
        ]
    elif mode == "bike":
        metrics = common + [
            ("Calories estimees", f"{plan.stats.get('calories_estimees_kcal', 0):.1f} kcal"),
            ("CO2 economise vs voiture", f"{plan.stats.get('co2_saved_vs_car_bike_kg', 0):.3f} kg"),
            ("Distance par heure", f"{plan.stats.get('distance_par_heure_km', 0):.2f} km/h"),
        ]
    else:
        metrics = common + [
            ("Calories estimees", f"{plan.stats.get('calories_estimees_kcal', 0):.1f} kcal"),
            ("Pas estimees", f"{plan.stats.get('pas_estimes', 0):d}"),
            ("Temps par km", f"{plan.stats.get('temps_par_km_min', 0):.1f} min/km"),
            ("CO2 economise vs voiture", f"{plan.stats.get('co2_saved_vs_car_walk_kg', 0):.3f} kg"),
        ]
    cards = "".join(
        f'<div class="metric"><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></div>'
        for label, value in metrics
    )
    return f'<div class="stats-grid">{cards}</div>'


def _mode_label(mode: str) -> str:
    return MODE_LABELS.get(mode, mode)


def _objective_label(objective: str) -> str:
    return OBJECTIVE_LABELS.get(objective, objective)


def _serve_asset(path: str):
    relative = Path(path.lstrip("/"))
    if len(relative.parts) < 2:
        return "404 Not Found", [("Content-Type", "text/plain; charset=utf-8")], b"Asset not found"
    root = EXPORT_ROOT if relative.parts[0] == "files" else STATIC_ROOT
    file_path = root / relative.name
    if not file_path.exists():
        return "404 Not Found", [("Content-Type", "text/plain; charset=utf-8")], b"Asset not found"
    content_type = "application/octet-stream"
    suffix = file_path.suffix.lower()
    if suffix == ".html":
        content_type = "text/html; charset=utf-8"
    elif suffix == ".json":
        content_type = "application/json; charset=utf-8"
    elif suffix == ".pdf":
        content_type = "application/pdf"
    return "200 OK", [("Content-Type", content_type)], file_path.read_bytes()


def _save_exports(plan: RoutePlan) -> Dict[str, str]:
    safe_name = f"route-{uuid.uuid4().hex[:8]}"
    html_path = EXPORT_ROOT / f"{safe_name}.html"
    json_path = EXPORT_ROOT / f"{safe_name}.json"
    pdf_path = EXPORT_ROOT / f"{safe_name}.pdf"

    HTMLExporter().exporter(plan, filename=str(html_path.with_suffix("")))
    JSONExporter().exporter(plan, json_path)
    PDFExporter().exporter(plan, pdf_path)

    return {
        "html": f"/files/{html_path.name}",
        "json": f"/files/{json_path.name}",
        "pdf": f"/files/{pdf_path.name}",
    }


def _read_form(environ) -> Dict[str, List[str]]:
    try:
        size = int(environ.get("CONTENT_LENGTH", "0") or "0")
    except ValueError:
        size = 0
    raw = environ["wsgi.input"].read(size).decode("utf-8")
    return parse_qs(raw, keep_blank_values=True)


def _parse_addresses(payload: Dict[str, List[str]]) -> List[str]:
    addresses = [value.strip() for value in payload.get("addresses", []) if value.strip()]
    if len(addresses) < 2:
        raise ValueError("Il faut au moins deux adresses")
    return addresses


def _addresses_html(raw_value: str) -> str:
    values = [line.strip() for line in raw_value.splitlines() if line.strip()]
    if not values:
        values = ["", ""]
    return "".join(
        f"""
        <div class="address-row">
          <input name="addresses" type="text" value="{html.escape(value)}">
          <button type="button" class="icon" onclick="this.parentElement.remove()">Supprimer</button>
        </div>
        """
        for value in values
    )


def _select_option(value: str, selected: str, label: str) -> str:
    return f'<option value="{value}" {"selected" if value == selected else ""}>{label}</option>'


def _page(title: str, content: str) -> str:
    return f"""
    <!doctype html>
    <html lang="fr">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>{html.escape(title)}</title>
      <style>
        :root {{
          --bg: #f4f7fb;
          --panel: #ffffff;
          --text: #142033;
          --muted: #607089;
          --line: #d8e0ea;
          --accent: #2156f3;
          --accent-dark: #173fb2;
          --error: #b42318;
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          background: var(--bg);
          color: var(--text);
        }}
        header {{
          padding: 18px 28px 10px;
          border-bottom: 1px solid var(--line);
          background: rgba(255,255,255,.7);
          backdrop-filter: blur(8px);
          position: sticky;
          top: 0;
          z-index: 2;
        }}
        header h1 {{ margin: 0; font-size: 22px; }}
        main {{
          max-width: 1200px;
          margin: 0 auto;
          padding: 30px 28px 40px;
          display: grid;
          gap: 20px;
        }}
        .hero {{
          padding: 22px;
          background: #ffffff;
          border: 1px solid var(--line);
          border-radius: 8px;
          box-shadow: 0 10px 30px rgba(20, 32, 51, 0.05);
        }}
        .hero h2 {{
          margin: 6px 0 10px;
          font-size: 30px;
          line-height: 1.1;
        }}
        .hero .lede {{
          margin: 0;
          color: var(--muted);
          max-width: 65ch;
        }}
        .hint-list div {{
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 14px;
          background: #fbfcfe;
        }}
        .hint-list strong, .eyebrow {{
          display: block;
          color: var(--muted);
          font-size: 12px;
          text-transform: none;
          letter-spacing: 0;
        }}
        .panel, .summary {{
          background: var(--panel);
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 22px;
          box-shadow: 0 10px 30px rgba(20, 32, 51, 0.05);
        }}
        .form-grid {{
          display: grid;
          gap: 18px;
        }}
        .layout {{
          display: grid;
          grid-template-columns: minmax(0, 1.55fr) minmax(300px, .95fr);
          gap: 20px;
          align-items: start;
        }}
        .section-title h3, .panel h2 {{
          margin: 0;
          font-size: 18px;
        }}
        .section-title p {{
          margin: 6px 0 0;
          color: var(--muted);
          font-size: 13px;
          line-height: 1.5;
        }}
        .split {{
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 16px;
        }}
        .context-strip {{
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 12px;
        }}
        .context-strip > div {{
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #f8fbff;
          padding: 16px;
        }}
        .context-strip span, .mode-facts span {{
          display: block;
          color: var(--muted);
          font-size: 12px;
          margin-bottom: 5px;
        }}
        .context-strip strong, .mode-facts strong {{
          display: block;
          font-size: 15px;
          margin-bottom: 6px;
        }}
        .help-copy, .mini-note {{
          margin: 0;
          color: var(--muted);
          font-size: 13px;
          line-height: 1.5;
        }}
        .mode-facts {{
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 12px;
        }}
        .mode-facts div {{
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 14px;
          background: #fcfdff;
        }}
        .hint-list {{
          display: grid;
          gap: 12px;
        }}
        label {{ display: grid; gap: 10px; font-weight: 600; }}
        label.inline {{
          grid-template-columns: none;
          align-items: stretch;
        }}
        input, select {{
          width: 100%;
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 12px 14px;
          min-height: 46px;
          font: inherit;
          background: #fff;
        }}
        textarea {{
          width: 100%;
          min-height: 120px;
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 10px 12px;
          font: inherit;
        }}
        button {{
          border: 0;
          border-radius: 8px;
          padding: 12px 16px;
          min-height: 46px;
          font: inherit;
          background: var(--accent);
          color: #fff;
          cursor: pointer;
        }}
        button.secondary, button.icon {{
          background: #eaf0ff;
          color: var(--accent-dark);
        }}
        button.icon {{
          min-width: 112px;
          justify-self: end;
        }}
        button.primary {{
          background: var(--accent-dark);
        }}
        .grid-2 {{
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 12px;
        }}
        .addresses {{ display: grid; gap: 10px; }}
        .address-row {{
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 12px;
          align-items: center;
        }}
        .checkbox.inline {{
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 14px 16px;
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #fbfcfe;
          min-height: 58px;
        }}
        .checkbox.inline input[type="checkbox"] {{
          width: 20px;
          height: 20px;
          margin: 0;
          flex: 0 0 20px;
          accent-color: var(--accent-dark);
        }}
        .mode-config.is-hidden, .method-config.is-hidden {{
          display: none;
        }}
        .is-muted {{
          opacity: 0.55;
        }}
        .summary {{
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 14px;
        }}
        .stats-grid {{
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 14px;
        }}
        .stat {{
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 14px 16px;
          background: #fbfcfe;
          min-height: 88px;
        }}
        .metric {{
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 14px 16px;
          background: #fbfcfe;
          min-height: 88px;
        }}
        .stat span {{ display: block; color: var(--muted); font-size: 12px; margin-bottom: 6px; }}
        .stat strong {{ font-size: 17px; }}
        .metric span {{ display: block; color: var(--muted); font-size: 12px; margin-bottom: 6px; }}
        .metric strong {{ font-size: 16px; }}
        .warnings {{
          margin: 0;
          padding: 12px 18px;
          border: 1px solid #f1c40f;
          background: #fff9db;
          border-radius: 8px;
        }}
        .warnings li {{ margin: 0 0 6px 0; }}
        .map-frame {{
          width: 100%;
          min-height: 560px;
          border: 1px solid var(--line);
          border-radius: 8px;
          overflow: hidden;
        }}
        .export-grid {{
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 14px;
        }}
        .export-card {{
          display: block;
          text-decoration: none;
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 16px;
          background: #f8fbff;
          color: var(--text);
          font-weight: 600;
        }}
        table {{
          width: 100%;
          border-collapse: collapse;
        }}
        th, td {{
          border-bottom: 1px solid var(--line);
          text-align: left;
          padding: 12px 10px;
          vertical-align: top;
        }}
        pre {{
          white-space: pre-wrap;
          word-break: break-word;
          background: #f8fafc;
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 12px;
          overflow: auto;
        }}
        .compact-data pre {{
          max-height: 220px;
          margin-top: 8px;
        }}
        .error {{
          background: #fff1f0;
          color: var(--error);
          border: 1px solid #ffb4a9;
          border-radius: 8px;
          padding: 12px 14px;
        }}
        .empty-state {{
          border: 1px dashed var(--line);
          border-radius: 8px;
          padding: 18px 20px;
          color: var(--muted);
        }}
        @media (max-width: 900px) {{
          .hero, .layout, .split, .export-grid, .stats-grid, .context-strip, .mode-facts {{
            grid-template-columns: 1fr;
          }}
          .summary, .grid-2 {{ grid-template-columns: 1fr; }}
          .address-row {{ grid-template-columns: 1fr; }}
          main {{ padding: 18px; }}
        }}
      </style>
    </head>
    <body>
      <header><h1>{html.escape(title)}</h1></header>
      <main>{content}</main>
    </body>
    </html>
    """


if __name__ == "__main__":
    raise SystemExit(main())
