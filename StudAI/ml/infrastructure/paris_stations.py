"""
Download IDFM rail station locations (emplacement-des-gares-idf) and write a
compact stations.json into App/src/data/.

Each source feature is one (station × line); we group by `id_ref_zda` so the
same physical station with multiple lines becomes one entry with a `lines` list.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

GEOJSON_URL = (
    "https://data.iledefrance-mobilites.fr/api/explore/v2.1/catalog/datasets/"
    "emplacement-des-gares-idf/exports/geojson"
)

MODE_MAP = {
    "METRO": "metro",
    "RER": "rer",
    "TRAMWAY": "tram",
    "TRAM": "tram",
}

OUTPUT_PATH = Path(__file__).resolve().parents[2] / "App" / "src" / "data" / "stations.json"


def main() -> int:
    print(f"[paris-stations] GET {GEOJSON_URL}")
    resp = requests.get(GEOJSON_URL, timeout=180)
    resp.raise_for_status()
    features = resp.json().get("features", [])
    print(f"[paris-stations] Fetched {len(features)} station-line features")

    grouped: dict[str, dict] = {}
    skipped = 0
    for f in features:
        props = f.get("properties", {}) or {}
        mode = MODE_MAP.get(str(props.get("mode") or "").upper())
        if not mode:
            skipped += 1
            continue

        route_id = str(props.get("idrefligc") or "")
        if not route_id:
            skipped += 1
            continue

        zda = str(props.get("id_ref_zda") or "")
        if not zda:
            skipped += 1
            continue

        geom = f.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            skipped += 1
            continue

        lat = round(coords[1], 5)
        lng = round(coords[0], 5)
        name = props.get("nom_gares") or props.get("nom_iv") or ""
        indice = props.get("indice_lig") or ""

        entry = grouped.setdefault(zda, {"id": zda, "name": name, "lat": lat, "lng": lng, "lines": []})
        if not entry["name"]:
            entry["name"] = name
        line_ref = {"routeId": route_id, "mode": mode, "indice": indice}
        if line_ref not in entry["lines"]:
            entry["lines"].append(line_ref)

    stations = sorted(grouped.values(), key=lambda s: s["name"])
    print(f"[paris-stations] {len(stations)} unique stations; {skipped} features skipped")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(stations, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[paris-stations] Wrote {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
