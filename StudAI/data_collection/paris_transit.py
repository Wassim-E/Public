"""
Download the IDFM rail-network GeoJSON (traces-du-reseau-ferre-idf) and write
a compact transit.json into App/src/data/.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import requests

GEOJSON_URL = (
    "https://data.iledefrance-mobilites.fr/api/explore/v2.1/catalog/datasets/"
    "traces-du-reseau-ferre-idf/exports/geojson"
)

MODE_MAP = {"METRO": "metro", "RER": "rer", "TRAMWAY": "tram"}

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "App" / "src" / "data" / "transit.json"


def main() -> int:
    print(f"[paris-transit] GET {GEOJSON_URL}")
    resp = requests.get(GEOJSON_URL, timeout=180)
    resp.raise_for_status()
    features = resp.json().get("features", [])
    print(f"[paris-transit] Fetched {len(features)} segment features")

    grouped: dict[str, dict] = defaultdict(lambda: {
        "id": "", "shortName": "", "longName": "", "mode": "", "color": "", "shapes": [],
    })

    skipped = 0
    for f in features:
        props = f.get("properties", {}) or {}
        mode = MODE_MAP.get(props.get("mode"))
        if not mode:
            skipped += 1
            continue

        route_id = str(props.get("idrefligc") or props.get("idrefliga") or "")
        if not route_id:
            skipped += 1
            continue

        geom = f.get("geometry") or {}
        coords = geom.get("coordinates")
        gtype = geom.get("type")
        if gtype == "LineString":
            polylines = [coords]
        elif gtype == "MultiLineString":
            polylines = coords
        else:
            skipped += 1
            continue

        latlng_polylines = []
        for line in polylines:
            latlng = [[round(c[1], 5), round(c[0], 5)] for c in line if isinstance(c, list) and len(c) >= 2]
            if len(latlng) >= 2:
                latlng_polylines.append(latlng)
        if not latlng_polylines:
            skipped += 1
            continue

        entry = grouped[route_id]
        entry["id"] = route_id
        entry["shortName"] = props.get("indice_lig") or entry["shortName"]
        entry["longName"] = props.get("res_com") or entry["longName"]
        entry["mode"] = mode
        color = props.get("colourweb_hexa")
        if color and not entry["color"]:
            entry["color"] = "#" + str(color).lstrip("#").upper()
        entry["shapes"].extend(latlng_polylines)

    fallback_color = {"metro": "#7AA2FF", "rer": "#E2231A", "tram": "#3FB16E"}
    for r in grouped.values():
        if not r["color"]:
            r["color"] = fallback_color.get(r["mode"], "#7AA2FF")

    routes = sorted(grouped.values(), key=lambda r: (r["mode"], r["shortName"] or ""))
    by_mode = defaultdict(int)
    for r in routes:
        by_mode[r["mode"]] += 1
    print(f"[paris-transit] {len(routes)} routes: " + ", ".join(f"{k}={v}" for k, v in sorted(by_mode.items())))
    print(f"[paris-transit] {skipped} segments skipped")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(routes, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[paris-transit] Wrote {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
