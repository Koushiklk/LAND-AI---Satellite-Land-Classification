# 🛰️ LAND AI — Satellite Land Classification & GIS Mapping System

A runnable starter project for the workflow:

```
Login/Register (2-step)  →  Select Location  →  Draw Area  →  Fetch Satellite Image
   →  AI Classification  →  View Results  →  View GIS Polygons  →  Download GeoJSON/Shapefile  →  Report
```

It works **out of the box, with no dataset and no API keys** — it ships with a
`MockClassifier` that produces realistic, repeatable land-cover results from
the shape of the area you draw. Plug in your trained model later (see
**"Adding your dataset / model"** below) without touching the rest of the app.

---

## 1. Quick start

**Requirements:** Python 3.9+

**macOS / Linux**
```bash
./run.sh
```

**Windows**
```bat
run.bat
```

Or manually:
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

## 2. Using the app

1. **Register** with a username, email, and password.
2. You'll be asked for a **6-digit verification code** (this is the 2-step
   verification). Since no email server is configured by default, the app
   runs in `DEV_MODE` — the code is shown directly on screen and printed to
   the terminal. Enter it to finish creating your account.
3. **Log in** next time — logging in also asks for a fresh 6-digit code
   (2-step verification on every login, not just registration).
4. On the dashboard:
   - **Search a location** (e.g. "Davangere, Karnataka") — this uses the
     free OpenStreetMap Nominatim geocoder, no API key needed.
   - **Draw a polygon or rectangle** on the satellite map to select your
     area of interest.
   - Click **"Fetch image & classify"** — this calls the classifier and
     draws the resulting land-cover percentages + classified GIS polygons
     on the map.
   - **Download** the result as GeoJSON, Shapefile (.zip), or a printable
     HTML report.

## 3. Turning on real email delivery

By default `DEV_MODE = True` in `backend/config.py`, so OTP codes are shown
on-screen instead of emailed. To send real emails:

1. Open `backend/config.py`.
2. Set `DEV_MODE = False`.
3. Fill in `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`,
   `SMTP_FROM` (e.g. a Gmail account with an
   [App Password](https://support.google.com/accounts/answer/185833), or
   any SMTP provider like SendGrid/Mailgun).

## 4. Adding your dataset / model

You said you'll bring your own dataset — here's exactly where it plugs in:

| What | Where |
|---|---|
| Your dataset (images, labels) | `backend/data/sample/` |
| Your trained model file | `backend/models/` |
| The code that currently fakes predictions | `backend/classifier.py` → `MockClassifier` |
| The single line to change once your model is ready | `backend/app.py` → `classifier = MockClassifier()` |
| Real satellite imagery fetching (optional) | `backend/satellite_service.py` (stub with instructions) |

`classifier.py` documents the exact interface your real classifier needs to
implement so nothing else in the app has to change.

## 5. Project structure

```
land_ai_project/
├── run.sh / run.bat            # one-command start
├── README.md
└── backend/                    # Flask app = backend (APIs) + frontend (templates/static)
    ├── app.py                  # routes: auth, dashboard, classify, downloads
    ├── config.py                # all settings (classes, colors, SMTP, DEV_MODE)
    ├── auth.py                  # password hashing + OTP (2-step verification)
    ├── database.py               # SQLite users / OTP / history tables
    ├── classifier.py             # MockClassifier — swap for your trained model
    ├── satellite_service.py      # stub: plug in a real satellite imagery API
    ├── gis_utils.py               # pure-python area calc, grid, polygon clipping, GeoJSON
    ├── requirements.txt
    ├── models/                    # <- put your trained model file(s) here
    ├── data/sample/                # <- put your dataset here
    ├── output/geojson/, reports/    # generated downloads land here
    ├── templates/                   # login, register, OTP, dashboard, report (Jinja)
    └── static/css/, js/              # blue satellite-earth theme + dashboard logic
```

## 6. How each of the 8 steps is implemented

| Step | Implementation |
|---|---|
| 1. Select location | Nominatim (OpenStreetMap) search, `/api/location/search` |
| 2. Draw area | Leaflet.draw polygon/rectangle tool on an Esri World Imagery satellite basemap |
| 3. Fetch satellite image | Stubbed (`satellite_service.py`) — classification currently works directly from the drawn area; wire up a real provider when ready |
| 4. AI classification | `classifier.py` → `MockClassifier` (swap for your trained model) |
| 5. View results | Percentage bars + area, `/api/classify` response rendered on the dashboard |
| 6. View polygons | `gis_utils.py` grids + clips the AOI and renders it as a colored GeoJSON layer on the map |
| 7. Download output | `/api/download/geojson` and `/api/download/shapefile` (real `.shp/.shx/.dbf` if `pyshp` is installed, otherwise a labeled GeoJSON fallback) |
| 8. Final report | `/api/download/report` — a styled, printable HTML report |

## 7. Notes & honest limitations

- This is a **working scaffold**, not a trained land-cover model. Classification
  results are deterministic-but-synthetic until you plug in your own model.
- GIS polygonization uses a simple grid-and-clip approach in pure Python
  (no GDAL/rasterio dependency required to run). For production-quality
  polygon simplification/smoothing, install `rasterio` + `shapely` +
  `geopandas` (already listed, commented out, in `requirements.txt`) and
  extend `gis_utils.py`.
- Satellite imagery fetching (step 3) is a documented stub — see
  `satellite_service.py` for exactly what to implement.

Smart Mapping · Better Decisions · Sustainable Future 🌍
