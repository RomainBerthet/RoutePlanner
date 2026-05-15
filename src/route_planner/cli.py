from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from route_planner.exporters.json_exporter import JSONExporter
from route_planner.route_planner import RoutePlanner
from route_planner.vehicule import Vehicule


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="route-planner")
    parser.add_argument("--addresses", nargs="*", help="Liste des adresses a planifier")
    parser.add_argument("--addresses-file", help="Fichier texte avec une adresse par ligne")
    parser.add_argument("--method", default="osrm", choices=["osrm", "osmnx", "valhalla", "graphhopper", "brouter"])
    parser.add_argument("--mode", default="drive", choices=["drive", "bike", "walk"])
    parser.add_argument(
        "--objective",
        default="fastest",
        choices=["fastest", "shortest_km", "cheapest", "balanced"],
    )
    parser.add_argument("--avoid-tolls", action="store_true")
    parser.add_argument("--budget", type=float, default=None)
    parser.add_argument("--balanced-weight", type=float, default=0.5)
    parser.add_argument("--consumption", type=float, default=0.06)
    parser.add_argument("--energy-cost", type=float, default=1.8)
    parser.add_argument("--valhalla-url", default="")
    parser.add_argument("--graphhopper-url", default="")
    parser.add_argument("--graphhopper-api-key", default="")
    parser.add_argument("--brouter-url", default="")
    parser.add_argument("--output", default="route")
    parser.add_argument("--json-output", default="")
    parser.add_argument("--skip-html", action="store_true")
    return parser


def load_addresses(args: argparse.Namespace) -> List[str]:
    addresses = list(args.addresses or [])
    if args.addresses_file:
        file_addresses = [
            line.strip()
            for line in Path(args.addresses_file).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        addresses.extend(file_addresses)
    if len(addresses) < 2:
        raise ValueError("Il faut au moins deux adresses")
    return addresses


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    addresses = load_addresses(args)

    vehicule = Vehicule(
        type_transport=args.mode,
        consommation_l_km=args.consumption,
        cout_energie=args.energy_cost,
    )
    planner = RoutePlanner(
        vehicule,
        methode_routage=args.method,
        objective=args.objective,
        avoid_tolls=args.avoid_tolls,
        budget_eur=args.budget,
        balanced_weight=args.balanced_weight,
        router_options=_router_options_from_args(args),
    )
    plan = planner.planifier_parcours(addresses)

    if not args.skip_html:
        planner.exporter.exporter(plan, filename=args.output)
    if args.json_output:
        JSONExporter().exporter(plan, args.json_output)

    print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
    return 0


def _router_options_from_args(args: argparse.Namespace) -> dict:
    options = {}
    mapping = {
        "valhalla_url": args.valhalla_url,
        "graphhopper_url": args.graphhopper_url,
        "graphhopper_api_key": args.graphhopper_api_key,
        "brouter_url": args.brouter_url,
    }
    for key, value in mapping.items():
        if value:
            options[key] = value
    return options


if __name__ == "__main__":
    raise SystemExit(main())
