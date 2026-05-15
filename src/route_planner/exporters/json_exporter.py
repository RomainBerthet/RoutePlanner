from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from route_planner.models import RoutePlan


class JSONExporter:
    def exporter(self, plan: RoutePlan, filename: Union[str, Path] = "route") -> Path:
        if not isinstance(plan, RoutePlan):
            raise TypeError("JSONExporter expects a RoutePlan")

        output_path = Path(filename)
        if output_path.suffix.lower() != ".json":
            output_path = output_path.with_suffix(".json")

        output_path.write_text(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path
