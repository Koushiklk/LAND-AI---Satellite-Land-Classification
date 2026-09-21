"""
LAND AI - Configuration
------------------------
All secrets/config live here. For a real deployment, load these from
environment variables instead of hardcoding them.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    # Flask
    SECRET_KEY = os.environ.get("LAND_AI_SECRET_KEY", "change-this-secret-key-in-production")

    # SQLite database (simple, file-based, zero setup)
    DATABASE_PATH = os.path.join(BASE_DIR, "data", "land_ai.db")

    # ---- Email / OTP (2-step verification) ----
    # LAND AI ships in "DEV_MODE" so you can test the full flow with no
    # email server: the OTP is shown directly on the verification page
    # and printed to the console instead of being emailed.
    #
    # To send real emails, set DEV_MODE = False and fill in an SMTP
    # account below (e.g. a Gmail "App Password", SendGrid, Mailgun, etc.)
    DEV_MODE = True

    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", "no-reply@landai.local")

    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 10

    # ---- Classification ----
    # Land cover classes shown throughout the UI. Edit this list (and the
    # matching colors) once you plug in your own trained model, so the
    # class names/colors match your dataset's label set.
    LAND_CLASSES = {
        "Forest":      "#1b7a3d",
        "Agriculture": "#c8a33d",
        "Urban":       "#8a8f98",
        "Water":       "#2b7fd6",
        "Barren Land": "#a9714b",
        "Rangeland":   "#7fae56",
    }

    # Output directories
    OUTPUT_DIR = os.path.join(BASE_DIR, "output")
    GEOJSON_DIR = os.path.join(OUTPUT_DIR, "geojson")
    REPORTS_DIR = os.path.join(OUTPUT_DIR, "reports")

    # Where a real satellite-fetch integration would cache imagery.
    # See satellite_service.py for the plug-in point.
    SATELLITE_CACHE_DIR = os.path.join(BASE_DIR, "data", "sample")

    # Where you drop your trained model file(s) (e.g. model.h5, model.pkl)
    MODEL_DIR = os.path.join(BASE_DIR, "models")
