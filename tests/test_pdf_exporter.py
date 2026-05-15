from route_planner.exporters.pdf_exporter import PDFExporter
from route_planner.models import RouteLeg, RoutePlan


def test_pdf_exporter_writes_pdf(tmp_path):
    plan = RoutePlan(
        requested_addresses=["A", "B"],
        ordered_addresses=["A", "B"],
        coordinates=[(48.0, 2.0), (48.1, 2.1)],
        geometry={"type": "LineString", "coordinates": [[2.0, 48.0], [2.1, 48.1]]},
        distance_km=12.34,
        duration_h=0.5,
        cost_eur=3.21,
        legs=[RouteLeg("A", "B", 12.34, 0.5, "summary")],
        routing_engine="OSRMRouter",
        optimization_strategy="exact_dp",
    )

    path = PDFExporter().exporter(plan, tmp_path / "route")
    data = path.read_bytes()

    assert path.suffix == ".pdf"
    assert data.startswith(b"%PDF-1.4")
