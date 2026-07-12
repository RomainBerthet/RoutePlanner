"""Render a route plan and its recommendations as a self-contained travel guide.

The output is a single, dependency-free HTML page (inline CSS + inline SVG, no
external assets) styled as an editorial "carnet de voyage": hero, key facts, a
stylised route map, a day-by-day breakdown and an address book of things to
visit near every stop. It is theme-aware (light/dark) and responsive.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote_plus

from route_planner.models import RoutePlan
from route_planner.recommendations.categories import CATEGORY_BY_KEY
from route_planner.recommendations.models import StopRecommendations

try:  # optional: the guide renders fine without AI enrichment
    from route_planner.ai.models import GuideContent
except Exception:  # pragma: no cover
    GuideContent = None  # type: ignore

MODE_LABELS = {"drive": "Voiture", "bike": "Vélo", "walk": "Marche"}
MODE_PILLS = {
    "drive": "◈ Road trip · étapes · découvertes",
    "bike": "◈ À vélo · nature · effort doux",
    "walk": "◈ À pied · balades · détails",
}


class TravelGuideExporter:
    def exporter(
        self,
        plan: RoutePlan,
        recommendations: Optional[Sequence[StopRecommendations]] = None,
        filename: str = "carnet-voyage",
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        guide_content=None,
    ) -> str:
        html_doc = self.render(
            plan, recommendations or [], title=title, subtitle=subtitle, guide_content=guide_content
        )
        path = Path(filename)
        if path.suffix.lower() != ".html":
            path = path.with_suffix(".html")
        path.write_text(html_doc, encoding="utf-8")
        return str(path)

    def render(
        self,
        plan: RoutePlan,
        recommendations: Sequence[StopRecommendations],
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        guide_content=None,
    ) -> str:
        stops = plan.ordered_addresses or []
        title = title or self._default_title(stops)
        subtitle = subtitle or self._default_subtitle(plan, stops)
        sections = [
            self._hero(plan, title, subtitle),
            self._facts(plan, recommendations),
            self._philosophy(guide_content),
            self._map(plan),
            self._itinerary(plan, recommendations),
            self._address_book(recommendations),
            self._secrets(guide_content),
            self._advice(guide_content),
            self._vigilance(guide_content),
            self._budget(guide_content),
            self._stats(plan),
            self._footer(),
        ]
        body = "\n".join(section for section in sections if section)
        return (
            "<!doctype html>\n<html lang=\"fr\">\n<head>\n"
            "<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<title>{html.escape(title)}</title>\n"
            f"<style>{_CSS}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n"
        )

    # -- sections -----------------------------------------------------------

    def _hero(self, plan: RoutePlan, title: str, subtitle: str) -> str:
        mode = plan.preferences.get("transport_mode", "drive")
        pill = MODE_PILLS.get(mode, MODE_PILLS["drive"])
        eyebrow = (
            f"{len(plan.ordered_addresses)} étapes · "
            f"{plan.distance_km:.0f} km · {self._format_duration(plan.duration_h)}"
        )
        return f"""
<header class="hero">
  {_HERO_SVG}
  <div class="hero-text"><div class="hero-inner">
    <p class="eyebrow">{html.escape(eyebrow)}</p>
    <h1>{html.escape(title)}</h1>
    <p>{html.escape(subtitle)}</p>
    <span class="pill">{html.escape(pill)}</span>
  </div></div>
</header>"""

    def _facts(self, plan: RoutePlan, recommendations: Sequence[StopRecommendations]) -> str:
        mode = plan.preferences.get("transport_mode", "drive")
        poi_count = sum(stop.count for stop in recommendations)
        facts: List[Tuple[str, str]] = [
            (f"{plan.distance_km:.0f}", "km au total"),
            (self._format_duration(plan.duration_h), "de trajet"),
            (str(len(plan.ordered_addresses)), "étapes"),
        ]
        if mode == "drive":
            facts.append((f"{plan.cost_eur:.0f} €", "carburant estimé"))
        elif mode == "bike":
            facts.append(
                (f"{plan.stats.get('calories_estimees_kcal', 0):.0f}", "kcal brûlées")
            )
        else:
            facts.append((f"{plan.stats.get('pas_estimes', 0):,}".replace(",", " "), "pas"))
        if recommendations:
            facts.append((str(poi_count), "lieux à visiter"))
        cells = "".join(
            f'<div class="fact"><div class="n">{html.escape(value)}</div>'
            f'<div class="l">{html.escape(label)}</div></div>'
            for value, label in facts
        )
        return f"""
<section>
  <div class="wrap">
    <p class="eyebrow">En bref</p>
    <h2 class="sec">Le parcours en chiffres</h2>
    <div class="facts">{cells}</div>
  </div>
</section>"""

    def _map(self, plan: RoutePlan) -> str:
        coords = [tuple(c) for c in plan.coordinates]
        if len(coords) < 2:
            return ""
        svg = _render_route_svg(coords, plan.ordered_addresses)
        return f"""
<section>
  <div class="wrap">
    <p class="eyebrow">Le tracé</p>
    <h2 class="sec">Carte du parcours</h2>
    <div class="mapcard">{svg}</div>
  </div>
</section>"""

    def _itinerary(
        self, plan: RoutePlan, recommendations: Sequence[StopRecommendations]
    ) -> str:
        if not plan.legs:
            return ""
        rec_by_index: Dict[int, StopRecommendations] = {
            stop.index: stop for stop in recommendations
        }
        cards = []
        for i, leg in enumerate(plan.legs):
            stop = rec_by_index.get(i + 1)
            highlights = ""
            if stop and stop.pois:
                items = "".join(
                    f'<li><a href="{html.escape(poi.maps_url)}" target="_blank" '
                    f'rel="noopener">{_icon(poi.category)} {html.escape(poi.name)}</a>'
                    f'<span class="dist">{poi.distance_km:.0f} km</span></li>'
                    for poi in stop.pois[:4]
                )
                highlights = f'<ul class="highlights">{items}</ul>'
            cards.append(
                f"""
      <article class="day">
        <div class="art">{_stop_art(i)}<div class="badge">Étape {i + 1}</div></div>
        <div class="body">
          <h3>{html.escape(leg.depart)} → {html.escape(leg.arrivee)}</h3>
          <div class="route">≈ {leg.distance_km:.0f} km · {self._format_duration(leg.duree_h)}"""
                + (f" · {html.escape(leg.resume)}" if leg.resume else "")
                + f"""</div>
          {highlights or '<p class="muted">Étape de liaison.</p>'}
        </div>
      </article>"""
            )
        return f"""
<section>
  <div class="wrap">
    <p class="eyebrow">Jour par jour</p>
    <h2 class="sec">L'itinéraire détaillé</h2>
    <div class="days">{''.join(cards)}</div>
  </div>
</section>"""

    def _address_book(self, recommendations: Sequence[StopRecommendations]) -> str:
        zones = []
        for stop in recommendations:
            if not stop.pois:
                continue
            grouped = stop.by_category()
            items = []
            for category_key, pois in grouped.items():
                category = CATEGORY_BY_KEY.get(category_key)
                icon = category.icon if category else "📍"
                label = category.label if category else category_key
                links = " · ".join(
                    f'<a href="{html.escape(poi.maps_url)}" target="_blank" '
                    f'rel="noopener">{html.escape(poi.name)}</a>'
                    for poi in pois
                )
                items.append(
                    f'<div class="it"><span class="ic">{icon}</span>'
                    f'<span><span class="k">{html.escape(label)}</span>{links}</span></div>'
                )
            zones.append(
                f"""
      <div class="z">
        <span class="sub">Étape {stop.index + 1}</span>
        <h3>{html.escape(stop.label)}</h3>
        <div class="items">{''.join(items)}</div>
      </div>"""
            )
        if not zones:
            return ""
        return f"""
<section>
  <div class="wrap">
    <p class="eyebrow">Carnet d'adresses</p>
    <h2 class="sec">Que voir, où s'arrêter</h2>
    <p class="lead">Chaque nom est un lien : clique pour ouvrir Google Maps — photos, avis, horaires, itinéraire.</p>
    <div class="adr">{''.join(zones)}</div>
  </div>
</section>"""

    def _stats(self, plan: RoutePlan) -> str:
        mode = plan.preferences.get("transport_mode", "drive")
        rows: List[Tuple[str, str]] = [
            ("Distance totale", f"{plan.distance_km:.1f} km"),
            ("Durée totale", self._format_duration(plan.duration_h)),
            ("Vitesse moyenne", f"{plan.stats.get('average_speed_kmh', 0):.0f} km/h"),
            ("Moteur", plan.routing_engine),
            ("Optimisation", plan.optimization_strategy),
        ]
        if mode == "drive":
            rows += [
                ("Coût carburant", f"{plan.cost_eur:.2f} €"),
                ("CO₂ estimé", f"{plan.stats.get('co2_car_kg', 0):.1f} kg"),
            ]
        elif mode == "bike":
            rows += [
                ("Calories", f"{plan.stats.get('calories_estimees_kcal', 0):.0f} kcal"),
                ("CO₂ évité vs voiture", f"{plan.stats.get('co2_saved_vs_car_bike_kg', 0):.1f} kg"),
            ]
        else:
            rows += [
                ("Calories", f"{plan.stats.get('calories_estimees_kcal', 0):.0f} kcal"),
                ("Pas estimés", f"{plan.stats.get('pas_estimes', 0)}"),
            ]
        cells = "".join(
            f'<div class="note"><h4>{html.escape(str(value))}</h4>'
            f'<p>{html.escape(label)}</p></div>'
            for label, value in rows
        )
        warnings = ""
        if plan.warnings:
            lis = "".join(f"<li>{html.escape(w)}</li>" for w in plan.warnings)
            warnings = f'<ul class="warnlist">{lis}</ul>'
        return f"""
<section>
  <div class="wrap">
    <p class="eyebrow">Les détails</p>
    <h2 class="sec">Statistiques du trajet</h2>
    <div class="grid2">{cells}</div>
    {warnings}
  </div>
</section>"""

    # -- AI-enriched sections ----------------------------------------------

    def _philosophy(self, guide) -> str:
        if not guide or not getattr(guide, "intro", ""):
            return ""
        return f"""
<section>
  <div class="wrap">
    <p class="eyebrow">L'esprit du voyage</p>
    <h2 class="sec">Avant de partir</h2>
    <p class="lead">{html.escape(guide.intro)}</p>
  </div>
</section>"""

    def _advice(self, guide) -> str:
        if not guide:
            return ""
        items = list(getattr(guide, "tips", [])) + list(getattr(guide, "practical", []))
        if not items:
            return ""
        cards = "".join(
            f'<div class="note"><h4>{html.escape(item.title)}</h4>'
            f'<p>{html.escape(item.body)}</p></div>'
            for item in items
        )
        return f"""
<section>
  <div class="wrap">
    <p class="eyebrow">Le petit plus</p>
    <h2 class="sec">Astuces &amp; conseils pratiques</h2>
    <div class="grid2">{cards}</div>
  </div>
</section>"""

    def _vigilance(self, guide) -> str:
        if not guide or not getattr(guide, "vigilance", None):
            return ""
        alerts = "".join(
            f"""
        <div class="alert">
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3 L22 20 H2 Z" stroke="var(--warn-line)" stroke-width="2" stroke-linejoin="round"/><line x1="12" y1="10" x2="12" y2="14" stroke="var(--warn-line)" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="17" r="1.2" fill="var(--warn-line)"/></svg>
          <div><h4>{html.escape(item.title)}</h4><p>{html.escape(item.body)}</p></div>
        </div>"""
            for item in guide.vigilance
        )
        return f"""
<section>
  <div class="wrap">
    <p class="eyebrow">Ouvrir l'oeil</p>
    <h2 class="sec">Points de vigilance</h2>
    <div class="alerts">{alerts}</div>
  </div>
</section>"""

    def _secrets(self, guide) -> str:
        if not guide or not getattr(guide, "secrets", None):
            return ""
        cards = []
        for spot in guide.secrets:
            gps = f'<span class="gps">{html.escape(spot.gps)}</span>' if spot.gps else ""
            zone = f'<span class="zone">{html.escape(spot.zone)}</span>' if spot.zone else ""
            query = quote_plus(f"{spot.name} {spot.gps}".strip())
            maps = f"https://www.google.com/maps/search/?api=1&query={query}"
            cards.append(
                f"""
        <div class="secret">
          <div class="hd"><span class="tag">🔑 Secret</span>{zone}</div>
          <h4><a href="{html.escape(maps)}" target="_blank" rel="noopener">{html.escape(spot.name)}</a></h4>
          <p>{html.escape(spot.body)}</p>{gps}
        </div>"""
            )
        return f"""
<section>
  <div class="wrap">
    <p class="eyebrow">Entre nous</p>
    <h2 class="sec">🔑 Spots secrets</h2>
    <p class="lead">Des coins peu fréquentés, proches de l'itinéraire. Chaque nom ouvre Google Maps.</p>
    <div class="secrets">{''.join(cards)}</div>
  </div>
</section>"""

    def _budget(self, guide) -> str:
        budget = getattr(guide, "budget", None) if guide else None
        if not budget or not budget.rows:
            return ""
        rows = "".join(
            f"<tr><td>{html.escape(r.label)}</td>"
            f'<td class="sub">{html.escape(r.detail)}</td>'
            f'<td class="amt">{html.escape(r.amount)}</td></tr>'
            for r in budget.rows
        )
        total = (
            f'<tr class="total"><td>Total</td><td class="sub"></td>'
            f'<td class="amt">{html.escape(budget.total)}</td></tr>'
            if budget.total
            else ""
        )
        note = (
            f'<div class="splitnote">{html.escape(budget.note)}</div>' if budget.note else ""
        )
        return f"""
<section>
  <div class="wrap">
    <p class="eyebrow">Le nerf de la guerre</p>
    <h2 class="sec">Récap budget</h2>
    <div class="tablewrap">
      <table>
        <thead><tr><th>Poste</th><th>Détail</th><th style="text-align:right">Montant</th></tr></thead>
        <tbody>{rows}{total}</tbody>
      </table>
    </div>
    {note}
  </div>
</section>"""

    def _footer(self) -> str:
        return """
<footer>
  <div class="wrap">
    Carnet généré par <b>Route Planner</b>. Lieux issus d'OpenStreetMap (Overpass) ·
    tracé et distances estimés · les liens « Voir » ouvrent Google Maps. Bon voyage ! 🏔️🌊
  </div>
</footer>"""

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _format_duration(hours: float) -> str:
        total_min = int(round(hours * 60))
        h, m = divmod(total_min, 60)
        if h and m:
            return f"{h} h {m:02d}"
        if h:
            return f"{h} h"
        return f"{m} min"

    @staticmethod
    def _default_title(stops: Sequence[str]) -> str:
        if not stops:
            return "Carnet de voyage"
        first = _short_place(stops[0])
        last = _short_place(stops[-1])
        if first == last:
            return f"Boucle depuis {first}"
        return f"{first} → {last}"

    def _default_subtitle(self, plan: RoutePlan, stops: Sequence[str]) -> str:
        via = [_short_place(s) for s in stops[1:-1]][:4]
        mode = MODE_LABELS.get(plan.preferences.get("transport_mode", "drive"), "Voiture")
        if via:
            return f"{mode} · en passant par {', '.join(via)}."
        return f"{mode} · un itinéraire optimisé, prêt à partir."


def _short_place(address: str) -> str:
    return address.split(",")[0].strip() if address else address


def _icon(category_key: str) -> str:
    category = CATEGORY_BY_KEY.get(category_key)
    return category.icon if category else "📍"


# --------------------------------------------------------------------------
# SVG helpers
# --------------------------------------------------------------------------

def _render_route_svg(coords: Sequence[Tuple[float, float]], labels: Sequence[str]) -> str:
    width, height, pad = 900.0, 520.0, 60.0
    from math import cos, radians

    lats = [lat for lat, _ in coords]
    lons = [lon for _, lon in coords]
    mean_lat = sum(lats) / len(lats)
    kx = cos(radians(mean_lat)) or 1e-6
    xs = [lon * kx for lon in lons]
    ys = [lat for lat in lats]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = (max_x - min_x) or 1e-6
    span_y = (max_y - min_y) or 1e-6
    scale = min((width - 2 * pad) / span_x, (height - 2 * pad) / span_y)
    off_x = (width - span_x * scale) / 2
    off_y = (height - span_y * scale) / 2

    def project(lat: float, lon: float) -> Tuple[float, float]:
        px = off_x + (lon * kx - min_x) * scale
        py = height - (off_y + (lat - min_y) * scale)  # flip y
        return round(px, 1), round(py, 1)

    points = [project(lat, lon) for lat, lon in coords]
    path = "M " + " L ".join(f"{x} {y}" for x, y in points)

    markers = []
    for i, (x, y) in enumerate(points):
        is_end = i == 0 or i == len(points) - 1
        color = "var(--gold)" if is_end else "var(--lake)"
        r = 8 if is_end else 6
        label = _short_place(labels[i]) if i < len(labels) else f"#{i + 1}"
        anchor = "start" if x < width - 160 else "end"
        dx = 12 if anchor == "start" else -12
        markers.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>'
            f'<circle cx="{x}" cy="{y}" r="{r / 2.4:.1f}" fill="var(--paper)"/>'
            f'<text x="{x + dx}" y="{y + 4}" text-anchor="{anchor}" '
            f'font-size="13">{html.escape(label)}</text>'
        )

    return (
        f'<svg viewBox="0 0 {int(width)} {int(height)}" role="img" '
        f'aria-label="Carte stylisée du parcours">'
        f'<rect x="0" y="0" width="{int(width)}" height="{int(height)}" fill="var(--paper-2)"/>'
        f'<path d="{path}" fill="none" stroke="var(--soca-deep)" stroke-width="3.5" '
        f'stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="2 9"/>'
        f'<g font-family="ui-monospace, monospace" fill="var(--ink)">{"".join(markers)}</g>'
        f"</svg>"
    )


_HERO_SVG = (
    '<svg class="scene" viewBox="0 0 1200 440" preserveAspectRatio="xMidYMid slice" '
    'role="img" aria-label="Montagnes et lac au couchant">'
    '<defs><linearGradient id="hsky" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#0e5c6e"/><stop offset="0.5" stop-color="#1c7f86"/>'
    '<stop offset="1" stop-color="#e9d7a8"/></linearGradient>'
    '<linearGradient id="hlake" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#57c6d8"/><stop offset="1" stop-color="#1f7f88"/>'
    '</linearGradient></defs>'
    '<rect width="1200" height="440" fill="url(#hsky)"/>'
    '<circle cx="930" cy="112" r="46" fill="#fbeecb" opacity="0.92"/>'
    '<path d="M0 240 L150 145 L280 235 L420 115 L560 235 L700 135 L860 245 L1000 155 '
    'L1140 245 L1200 205 L1200 440 L0 440 Z" fill="#2a6d72" opacity="0.55"/>'
    '<path d="M0 300 L120 195 L230 295 L360 185 L470 305 L620 175 L760 295 L900 205 '
    'L1050 315 L1200 245 L1200 440 L0 440 Z" fill="#1f5a5f"/>'
    '<path d="M360 185 L392 235 L340 231 Z M620 175 L656 227 L598 223 Z" fill="#eaf6f2" opacity="0.9"/>'
    '<rect y="360" width="1200" height="80" fill="url(#hlake)"/>'
    '<path d="M120 388 h1000" stroke="#c9f7f0" stroke-width="3" opacity="0.35"/>'
    '</svg>'
)


def _stop_art(index: int) -> str:
    palettes = [
        ("#e79a5f", "#f4dc9c", "#3f9fb0"),
        ("#8fd0e0", "#f3e6bf", "#37b0c4"),
        ("#cfe0d2", "#eee6cc", "#7a8a5a"),
        ("#f2c877", "#f7e6bc", "#2e8fa8"),
    ]
    sky_top, sky_bottom, water = palettes[index % len(palettes)]
    gid = f"art{index}"
    return (
        f'<svg viewBox="0 0 300 260" preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
        f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{sky_top}"/><stop offset="1" stop-color="{sky_bottom}"/>'
        f'</linearGradient></defs>'
        f'<rect width="300" height="260" fill="url(#{gid})"/>'
        f'<circle cx="230" cy="70" r="26" fill="#fff0cc" opacity="0.9"/>'
        f'<path d="M0 150 L70 90 L140 150 L210 85 L300 150 L300 175 L0 175 Z" '
        f'fill="#5f7f88" opacity="0.55"/>'
        f'<rect y="168" width="300" height="92" fill="{water}"/></svg>'
    )


_CSS = """
:root{--paper:#f3efe4;--paper-2:#eae4d4;--card:#fbf9f3;--ink:#16302b;--ink-soft:#40534d;
--line:#d8d0bd;--soca:#16a89e;--soca-deep:#0e7d76;--lake:#1f5f7a;--coral:#d8674a;
--gold:#c99a3f;--maxw:940px;
--warn-bg:#f6e4d3;--warn-line:#c96a3f;--warn-ink:#8a3d1c;}
@media (prefers-color-scheme:dark){:root{--paper:#0e1a18;--paper-2:#12211e;--card:#16241f;
--ink:#eef3ea;--ink-soft:#a8b8b0;--line:#26372f;--soca:#3fd0c4;--soca-deep:#2fb6ab;
--lake:#6bb6d0;--coral:#ec876b;--gold:#e0b757;
--warn-bg:#2c1c12;--warn-line:#d8794f;--warn-ink:#f0b998;}}
:root[data-theme="dark"]{--paper:#0e1a18;--paper-2:#12211e;--card:#16241f;--ink:#eef3ea;
--ink-soft:#a8b8b0;--line:#26372f;--soca:#3fd0c4;--soca-deep:#2fb6ab;--lake:#6bb6d0;
--coral:#ec876b;--gold:#e0b757;
--warn-bg:#2c1c12;--warn-line:#d8794f;--warn-ink:#f0b998;}
*{box-sizing:border-box;}
body{margin:0;background:var(--paper);color:var(--ink);line-height:1.6;
font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased;}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 22px;}
h1,h2,h3,h4{font-family:Georgia,"Times New Roman",serif;font-weight:600;line-height:1.12;
letter-spacing:-.01em;text-wrap:balance;}
h2.sec{font-size:1.9rem;margin:.3rem 0 0;}
.eyebrow{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:.72rem;letter-spacing:.22em;
text-transform:uppercase;color:var(--soca-deep);margin:0;}
section{padding:48px 0;}
section+section{border-top:1px solid var(--line);}
.lead{font-size:1.08rem;color:var(--ink-soft);max-width:62ch;margin-top:.6rem;}
header.hero{position:relative;overflow:hidden;border-bottom:1px solid var(--line);}
.hero svg.scene{display:block;width:100%;height:auto;}
.hero-text{position:absolute;left:0;right:0;bottom:0;padding:0 22px 30px;}
.hero-inner{max-width:var(--maxw);margin:0 auto;}
.hero-text h1{font-size:clamp(2rem,5.4vw,3.4rem);margin:8px 0 6px;color:#fff;
text-shadow:0 2px 24px rgba(8,24,20,.55);}
.hero-text .eyebrow{color:#bff0eb;text-shadow:0 1px 10px rgba(8,24,20,.6);}
.hero-text p{margin:4px 0 0;color:#eafaf7;max-width:52ch;text-shadow:0 1px 12px rgba(8,24,20,.7);}
.pill{display:inline-block;margin-top:12px;background:var(--gold);color:#2a1c04;
font-family:ui-monospace,monospace;font-size:.72rem;letter-spacing:.1em;text-transform:uppercase;
padding:5px 11px;border-radius:999px;font-weight:700;}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;
background:var(--line);border:1px solid var(--line);border-radius:14px;overflow:hidden;margin-top:22px;}
.fact{background:var(--card);padding:20px 18px;}
.fact .n{font-family:Georgia,serif;font-size:1.6rem;color:var(--soca-deep);font-variant-numeric:tabular-nums;}
.fact .l{font-size:.82rem;color:var(--ink-soft);margin-top:2px;}
.mapcard{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px;margin-top:18px;}
.mapcard svg{display:block;width:100%;height:auto;}
.days{display:flex;flex-direction:column;gap:20px;margin-top:26px;}
.day{display:grid;grid-template-columns:220px 1fr;background:var(--card);border:1px solid var(--line);
border-radius:16px;overflow:hidden;}
.day .art{position:relative;}
.day .art svg{display:block;width:100%;height:100%;}
.day .art .badge{position:absolute;top:12px;left:12px;background:rgba(10,24,20,.55);color:#eafaf7;
backdrop-filter:blur(3px);padding:5px 10px;border-radius:999px;font-size:.7rem;letter-spacing:.1em;
font-family:ui-monospace,monospace;text-transform:uppercase;}
.day .body{padding:20px 22px;}
.day h3{font-size:1.22rem;margin:0 0 4px;}
.day .route{font-size:.78rem;color:var(--soca-deep);font-family:ui-monospace,monospace;margin-bottom:12px;}
.highlights{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:7px;}
.highlights li{display:flex;justify-content:space-between;gap:12px;align-items:baseline;font-size:.92rem;}
.highlights a{color:var(--ink);text-decoration:none;
border-bottom:1px solid color-mix(in srgb,var(--soca) 45%,transparent);}
.highlights a:hover{border-color:var(--soca);}
.highlights .dist{font-family:ui-monospace,monospace;font-size:.72rem;color:var(--ink-soft);white-space:nowrap;}
.muted{color:var(--ink-soft);font-size:.9rem;margin:0;}
.adr{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-top:24px;}
.adr .z{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px 22px;}
.adr .z .sub{font-family:ui-monospace,monospace;font-size:.68rem;letter-spacing:.12em;
text-transform:uppercase;color:var(--soca-deep);}
.adr .z h3{font-size:1.14rem;margin:3px 0 0;}
.adr .items{display:flex;flex-direction:column;gap:13px;margin-top:15px;}
.adr .it{display:grid;grid-template-columns:24px 1fr;gap:9px;font-size:.9rem;align-items:baseline;}
.adr .it .k{font-family:ui-monospace,monospace;font-size:.62rem;letter-spacing:.1em;
text-transform:uppercase;color:var(--ink-soft);display:block;margin-bottom:3px;}
.adr .it a{color:var(--soca-deep);text-decoration:none;
border-bottom:1px solid color-mix(in srgb,var(--soca) 45%,transparent);}
.adr .it a:hover{border-color:var(--soca);}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-top:22px;}
.note{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;}
.note h4{margin:0 0 4px;font-size:1.15rem;color:var(--soca-deep);}
.note p{margin:0;font-size:.85rem;color:var(--ink-soft);}
.warnlist{margin:18px 0 0;padding:14px 16px 14px 34px;background:color-mix(in srgb,var(--gold) 16%,transparent);
border-left:3px solid var(--gold);border-radius:0 8px 8px 0;font-size:.9rem;}
.alerts{display:flex;flex-direction:column;gap:14px;margin-top:22px;}
.alert{display:grid;grid-template-columns:44px 1fr;gap:14px;background:var(--warn-bg);
border:1px solid var(--warn-line);border-radius:14px;padding:16px 20px;}
.alert svg{width:32px;height:32px;}
.alert h4{margin:0 0 4px;color:var(--warn-ink);font-size:1.05rem;}
.alert p{margin:0;font-size:.9rem;color:var(--ink);}
.secrets{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-top:24px;}
.secret{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--gold);
border-radius:0 14px 14px 0;padding:16px 20px;}
.secret .hd{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;}
.secret .tag{font-family:ui-monospace,monospace;font-size:.6rem;letter-spacing:.16em;
text-transform:uppercase;color:var(--gold);}
.secret .zone{font-family:ui-monospace,monospace;font-size:.62rem;letter-spacing:.1em;
text-transform:uppercase;color:var(--soca-deep);}
.secret h4{font-size:1.08rem;margin:7px 0 5px;}
.secret h4 a{color:var(--ink);text-decoration:none;
border-bottom:1px solid color-mix(in srgb,var(--gold) 55%,transparent);}
.secret h4 a:hover{border-color:var(--gold);}
.secret p{margin:0;font-size:.9rem;color:var(--ink-soft);}
.secret .gps{display:block;margin-top:9px;font-family:ui-monospace,monospace;font-size:.72rem;
color:var(--ink-soft);font-variant-numeric:tabular-nums;}
.tablewrap{overflow-x:auto;margin-top:22px;border:1px solid var(--line);border-radius:14px;}
table{border-collapse:collapse;width:100%;min-width:520px;background:var(--card);}
th,td{text-align:left;padding:12px 16px;border-bottom:1px solid var(--line);font-size:.92rem;}
th{font-family:ui-monospace,monospace;font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;
color:var(--ink-soft);}
td.amt{text-align:right;font-family:ui-monospace,monospace;font-variant-numeric:tabular-nums;white-space:nowrap;}
td .sub,td.sub{color:var(--ink-soft);font-size:.82rem;}
tr:last-child td{border-bottom:none;}
tr.total td{font-weight:700;background:color-mix(in srgb,var(--soca) 10%,transparent);font-size:1rem;}
tr.total td.amt{color:var(--soca-deep);}
.splitnote{margin-top:16px;padding:14px 16px;background:color-mix(in srgb,var(--gold) 16%,transparent);
border-left:3px solid var(--gold);border-radius:0 8px 8px 0;font-size:.9rem;}
footer{padding:36px 0 56px;color:var(--ink-soft);font-size:.85rem;}
@media (max-width:680px){.adr{grid-template-columns:1fr;}.day{grid-template-columns:1fr;}
.day .art{min-height:140px;}.secrets{grid-template-columns:1fr;}}
"""
