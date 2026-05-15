from __future__ import annotations

import io
import unicodedata
from pathlib import Path
from typing import List, Union

from route_planner.models import RoutePlan


class PDFExporter:
    def exporter(self, plan: RoutePlan, filename: Union[str, Path] = "route") -> Path:
        if not isinstance(plan, RoutePlan):
            raise TypeError("PDFExporter expects a RoutePlan")

        output_path = Path(filename)
        if output_path.suffix.lower() != ".pdf":
            output_path = output_path.with_suffix(".pdf")

        lines = self._render_lines(plan)
        pdf_bytes = self._build_pdf(lines)
        output_path.write_bytes(pdf_bytes)
        return output_path

    def _render_lines(self, plan: RoutePlan) -> List[str]:
        lines = [
            "Route Planner - Feuille de route",
            "",
            f"Distance totale: {plan.distance_km:.2f} km",
            f"Duree totale: {plan.duration_h * 60:.1f} min",
            f"Cout total: {plan.cost_eur:.2f} EUR",
            f"Objectif: {plan.preferences.get('objective', 'fastest')}",
        ]
        if plan.preferences.get("avoid_tolls"):
            lines.append("Peages: evites quand supporte par le moteur")
        if plan.budget_limit_eur is not None:
            lines.append(
                f"Budget: {plan.budget_limit_eur:.2f} EUR - "
                + ("respecte" if plan.budget_within else f"depasse de {plan.budget_gap_eur:.2f} EUR")
            )
        if plan.warnings:
            lines.append("")
            lines.append("Avertissements:")
            lines.extend(f"- {warning}" for warning in plan.warnings)
        lines.append("")
        lines.append("Etapes:")
        for idx, leg in enumerate(plan.legs, start=1):
            lines.append(
                f"{idx}. {leg.depart} -> {leg.arrivee} | "
                f"{leg.distance_km:.3f} km | {leg.duree_h * 60:.1f} min"
            )
            if leg.resume:
                lines.append(f"   {leg.resume}")
        return lines

    def _build_pdf(self, lines: List[str]) -> bytes:
        escaped_lines = [self._escape_pdf_text(line) for line in lines]
        commands = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"]
        if escaped_lines:
            commands.append(f"({escaped_lines[0]}) Tj")
            for line in escaped_lines[1:]:
                commands.append("T*")
                commands.append(f"({line}) Tj")
        commands.append("ET")
        text_stream = "\n".join(commands)

        objects = []
        objects.append("<< /Type /Catalog /Pages 2 0 R >>")
        objects.append("<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        objects.append(
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            "/Resources << /Font << /F1 4 0 R >> >> "
            "/Contents 5 0 R >>"
        )
        objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        stream = text_stream.encode("latin-1")
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{text_stream}\nendstream")

        buffer = io.BytesIO()
        buffer.write(b"%PDF-1.4\n")
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(buffer.tell())
            buffer.write(f"{index} 0 obj\n{obj}\nendobj\n".encode("latin-1"))
        xref_start = buffer.tell()
        buffer.write(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
        buffer.write(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            buffer.write(f"{offset:010d} 00000 n \n".encode("latin-1"))
        buffer.write(
            (
                "trailer\n"
                f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref_start}\n%%EOF"
            ).encode("latin-1")
        )
        return buffer.getvalue()

    def _escape_pdf_text(self, text: str) -> str:
        ascii_text = (
            unicodedata.normalize("NFKD", text)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
        return ascii_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
