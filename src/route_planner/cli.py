from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from route_planner.exporters.json_exporter import JSONExporter
from route_planner.exporters.travel_guide_exporter import TravelGuideExporter
from route_planner.recommendations.service import RecommendationService
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
    parser.add_argument(
        "--guide",
        action="store_true",
        help="Genere un carnet de voyage HTML enrichi (avec recommandations de lieux a visiter)",
    )
    parser.add_argument("--guide-output", default="", help="Chemin du carnet de voyage (defaut: <output>-carnet.html)")
    parser.add_argument("--guide-title", default="", help="Titre du carnet de voyage")
    parser.add_argument("--recommend-radius", type=int, default=8000, help="Rayon de recherche des lieux (m)")
    parser.add_argument("--recommend-limit", type=int, default=8, help="Nombre max de lieux par etape")
    parser.add_argument(
        "--recommend-categories",
        default="",
        help="Categories separees par des virgules (sight,viewpoint,nature,beach,museum,religious,food,drink)",
    )
    parser.add_argument(
        "--no-recommend",
        action="store_true",
        help="Genere le carnet sans appeler le service de recommandations",
    )
    parser.add_argument("--overpass-url", default="", help="URL Overpass personnalisee")
    parser.add_argument(
        "--ai-prompt",
        default="",
        help="Demande en langage naturel; l'IA en deduit les etapes, le mode et l'objectif",
    )
    parser.add_argument(
        "--ai-enrich",
        action="store_true",
        help="Utilise l'IA pour rediger le contenu du carnet (astuces, vigilance, budget, secrets)",
    )
    parser.add_argument("--ai-provider", default="anthropic", choices=["anthropic", "openai", "vllm"])
    parser.add_argument("--ai-model", default="", help="Modele IA (defaut selon le provider)")
    parser.add_argument("--ai-base-url", default="", help="URL de base (OpenAI-compatible / vLLM)")
    parser.add_argument("--ai-api-key", default="", help="Cle API du provider IA (sinon variable d'environnement)")
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

    suggestion = _ai_itinerary(args) if args.ai_prompt else None
    if suggestion is not None:
        addresses = suggestion.stops
        args.mode = suggestion.transport_mode
        args.objective = suggestion.objective
        print(f"Itineraire propose par l'IA : {' -> '.join(addresses)}")
    else:
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

    if args.guide:
        _generate_guide(plan, args, suggestion)

    print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
    return 0


def _build_ai_service(args: argparse.Namespace):
    from route_planner.ai.factory import LLMFactory
    from route_planner.ai.service import TravelIntelligence

    options = {}
    if args.ai_model:
        options["model"] = args.ai_model
    if args.ai_api_key:
        options["api_key"] = args.ai_api_key
    if args.ai_base_url:
        options["base_url"] = args.ai_base_url
    provider = LLMFactory.get_provider(args.ai_provider, **options)
    return TravelIntelligence(provider)


def _ai_itinerary(args: argparse.Namespace):
    return _build_ai_service(args).suggest_itinerary(args.ai_prompt)


def _generate_guide(plan, args: argparse.Namespace, suggestion=None) -> None:
    recommendations = []
    if not args.no_recommend:
        from route_planner.recommendations.providers.overpass import OverpassProvider

        provider = OverpassProvider(base_url=args.overpass_url or None)
        service = RecommendationService(
            provider=provider,
            radius_m=args.recommend_radius,
            per_stop_limit=args.recommend_limit,
            categories=_split_categories(args.recommend_categories),
        )
        recommendations = service.recommend_for_plan(plan)

    guide_content = None
    if args.ai_enrich:
        guide_content = _build_ai_service(args).write_guide_content(
            plan, recommendations, request=args.ai_prompt
        )

    title = suggestion.title if suggestion and suggestion.title else args.guide_title or None
    subtitle = suggestion.subtitle if suggestion and suggestion.subtitle else None
    guide_output = args.guide_output or f"{args.output}-carnet"
    path = TravelGuideExporter().exporter(
        plan,
        recommendations,
        filename=guide_output,
        title=title,
        subtitle=subtitle,
        guide_content=guide_content,
    )
    total = sum(stop.count for stop in recommendations)
    enriched = " + contenu IA" if guide_content else ""
    print(f"Carnet de voyage genere : {path} ({total} lieux recommandes{enriched})")


def _split_categories(raw: str):
    if not raw:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


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
