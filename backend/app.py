"""
LAND AI - Satellite Land Classification & GIS Mapping System
----------------------------------------------------------------
Run with:   python app.py
Then open:  http://127.0.0.1:5000

See README.md in the project root for full setup instructions.
"""

import json
import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, send_file, flash
)

from config import Config
from database import init_db, get_db
from auth import hash_password, verify_password, create_otp, verify_otp, send_otp_email
from classifier import MockClassifier
from gis_utils import make_classified_grid, cells_to_geojson, aoi_to_geojson

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# ---- plug-in point: swap MockClassifier() for your trained model's class ----
classifier = MockClassifier()

os.makedirs(Config.GEOJSON_DIR, exist_ok=True)
os.makedirs(Config.REPORTS_DIR, exist_ok=True)
init_db()


# ---------------------------------------------------------------- helpers --

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def get_user_by_username_or_email(identifier):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? OR email = ?",
        (identifier, identifier),
    ).fetchone()
    conn.close()
    return row


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


# ------------------------------------------------------------------ pages --

@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# --------------------------------------------------------------- register --

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not username or not email or not password:
        flash("All fields are required.", "error")
        return render_template("register.html")

    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM users WHERE username = ? OR email = ?", (username, email)
    ).fetchone()
    if existing:
        conn.close()
        flash("Username or email already registered.", "error")
        return render_template("register.html")

    cur = conn.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (username, email, hash_password(password)),
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()

    code = create_otp(user_id, purpose="register")
    send_otp_email(email, code)

    session["pending_user_id"] = user_id
    session["pending_purpose"] = "register"

    dev_hint = code if Config.DEV_MODE else None
    return render_template("verify_otp.html", email=email, dev_hint=dev_hint)


# ------------------------------------------------------------------ login --

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    identifier = request.form.get("identifier", "").strip()
    password = request.form.get("password", "")

    user = get_user_by_username_or_email(identifier)
    if user is None or not verify_password(password, user["password_hash"]):
        flash("Invalid username/email or password.", "error")
        return render_template("login.html")

    # ---- 2-step verification on every login ----
    code = create_otp(user["id"], purpose="login")
    send_otp_email(user["email"], code)

    session["pending_user_id"] = user["id"]
    session["pending_purpose"] = "login"

    dev_hint = code if Config.DEV_MODE else None
    return render_template("verify_otp.html", email=user["email"], dev_hint=dev_hint)


# -------------------------------------------------------------- verify OTP --

@app.route("/verify-otp", methods=["POST"])
def verify_otp_route():
    user_id = session.get("pending_user_id")
    purpose = session.get("pending_purpose")
    code = request.form.get("code", "").strip()

    if not user_id or not purpose:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("login"))

    if not verify_otp(user_id, purpose, code):
        flash("Invalid or expired code. Please try again.", "error")
        user = get_user_by_id(user_id)
        return render_template("verify_otp.html", email=user["email"])

    if purpose == "register":
        conn = get_db()
        conn.execute("UPDATE users SET is_verified = 1 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

    session.pop("pending_user_id", None)
    session.pop("pending_purpose", None)
    session["user_id"] = user_id

    return redirect(url_for("dashboard"))


@app.route("/resend-otp", methods=["POST"])
def resend_otp():
    user_id = session.get("pending_user_id")
    purpose = session.get("pending_purpose")
    if not user_id or not purpose:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    code = create_otp(user_id, purpose)
    send_otp_email(user["email"], code)

    dev_hint = code if Config.DEV_MODE else None
    flash("A new code has been sent.", "success")
    return render_template("verify_otp.html", email=user["email"], dev_hint=dev_hint)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --------------------------------------------------------------- dashboard --

@app.route("/dashboard")
@login_required
def dashboard():
    user = get_user_by_id(session["user_id"])
    return render_template(
        "dashboard.html",
        username=user["username"],
        land_classes=Config.LAND_CLASSES,
    )


# --------------------------------------------------------------- API: geocode (location search) --
# Uses OpenStreetMap's free Nominatim service - no API key required.
# If you don't have outbound internet where this runs, wire up any
# geocoding provider here instead (Google, Mapbox, LocationIQ, ...).

@app.route("/api/location/search")
@login_required
def location_search():
    import urllib.request
    import urllib.parse

    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"results": []})

    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
        "q": query, "format": "json", "limit": 5,
    })
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LandAI/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
        results = [
            {"name": d["display_name"], "lat": float(d["lat"]), "lng": float(d["lon"])}
            for d in data
        ]
        return jsonify({"results": results})
    except Exception as exc:
        return jsonify({"results": [], "error": str(exc)})


# --------------------------------------------------------------- API: classify --

@app.route("/api/classify", methods=["POST"])
@login_required
def classify():
    data = request.get_json(force=True)
    polygon = data.get("polygon")          # [[lat, lng], ...]
    location_name = data.get("location_name", "Selected Area")

    if not polygon or len(polygon) < 3:
        return jsonify({"error": "A valid polygon with at least 3 points is required."}), 400

    aoi_coords = [(pt[0], pt[1]) for pt in polygon]

    result = classifier.predict(aoi_coords, location_name)
    percentages = result["percentages"]

    # Step 6: turn the classification into GIS polygons (grid-based, see gis_utils.py)
    cells = make_classified_grid(
        aoi_coords, percentages, grid_size=8, seed=result["seed"]
    )
    geojson = cells_to_geojson(
        cells, Config.LAND_CLASSES,
        properties_extra={"location": location_name},
    )
    aoi_geojson = aoi_to_geojson(aoi_coords, {"location": location_name})

    payload = {
        "location_name": location_name,
        "area_km2": result["area_km2"],
        "percentages": percentages,
        "dominant_class": result["dominant_class"],
        "geojson": geojson,
        "aoi_geojson": aoi_geojson,
        "class_colors": Config.LAND_CLASSES,
        "generated_at": datetime.utcnow().isoformat(),
    }

    # cache the latest result in the session for the download endpoints
    session["last_result"] = payload

    conn = get_db()
    conn.execute(
        "INSERT INTO classification_history (user_id, location_name, area_km2, result_json) VALUES (?, ?, ?, ?)",
        (session["user_id"], location_name, result["area_km2"], json.dumps(payload)),
    )
    conn.commit()
    conn.close()

    return jsonify(payload)


# --------------------------------------------------------------- API: downloads --

@app.route("/api/download/geojson")
@login_required
def download_geojson():
    result = session.get("last_result")
    if not result:
        return jsonify({"error": "No classification result yet. Run a classification first."}), 400

    path = os.path.join(Config.GEOJSON_DIR, "land_ai_classification.geojson")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result["geojson"], f, indent=2)

    return send_file(path, as_attachment=True, download_name="land_ai_classification.geojson")


@app.route("/api/download/shapefile")
@login_required
def download_shapefile():
    """
    Exports a proper .zip Shapefile if pyshp/geopandas/shapely are
    installed; otherwise falls back to a clearly-labeled GeoJSON so the
    button always works out of the box. Install `pyshp` (pip install
    pyshp) for real .shp/.shx/.dbf output - see requirements.txt.
    """
    result = session.get("last_result")
    if not result:
        return jsonify({"error": "No classification result yet. Run a classification first."}), 400

    try:
        import shapefile 
        import zipfile

        base = os.path.join(Config.GEOJSON_DIR, "land_ai_classification")
        w = shapefile.Writer(base, shapeType=shapefile.POLYGON)
        w.field("land_class", "C")
        w.field("color", "C")
        w.field("location", "C")

        for feature in result["geojson"]["features"]:
            ring = feature["geometry"]["coordinates"][0]
            w.poly([ring])
            props = feature["properties"]
            w.record(props.get("land_class", ""), props.get("color", ""), props.get("location", ""))
        w.close()

        zip_path = base + ".zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for ext in (".shp", ".shx", ".dbf"):
                zf.write(base + ext, arcname="land_ai_classification" + ext)

        return send_file(zip_path, as_attachment=True, download_name="land_ai_classification_shapefile.zip")

    except ImportError:
        # fallback: still give the user something useful
        path = os.path.join(Config.GEOJSON_DIR, "land_ai_classification.geojson")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result["geojson"], f, indent=2)
        return send_file(
            path, as_attachment=True,
            download_name="land_ai_classification_(install_pyshp_for_.shp).geojson",
        )


@app.route("/api/download/report")
@login_required
def download_report():
    result = session.get("last_result")
    if not result:
        return jsonify({"error": "No classification result yet. Run a classification first."}), 400

    user = get_user_by_id(session["user_id"])
    html = render_template("report.html", result=result, username=user["username"])

    path = os.path.join(Config.REPORTS_DIR, "land_ai_report.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    return send_file(path, as_attachment=True, download_name="land_ai_report.html")


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000) 