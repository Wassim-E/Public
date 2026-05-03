# StudAI data pipeline

Modular Python scripts that fetch external data and produce JSON for the frontend at `App/src/data/`.

Each script does **one thing**. Run them individually with `python pipeline/<script>.py` from the StudAI root.

## Setup

```powershell
python -m pip install -r pipeline/requirements.txt
```

## Scripts

| Script | Output | Source |
|---|---|---|
| `fetch_paris_transit.py` | `App/src/data/transit.json` | IDFM `traces-du-reseau-ferre-idf` (metro/RER/tram polylines) |

More scripts are added as new data sources are wired into the app — see the rolling plan.
