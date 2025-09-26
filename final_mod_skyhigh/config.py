# config.py
import os

class Settings:
    # --- Server basics (edit these) ---
    HOST = os.getenv("HOST", "127.0.0.1")   # keep localhost to stay private
    PORT = int(os.getenv("PORT", "5000"))
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # --- External APIs ---
    AVIATION_WEATHER_BASE = os.getenv(
        "AVIATION_WEATHER_BASE",
        "https://aviationweather.gov/api/data"
    )

    # --- Service knobs ---
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "7"))
    DEFAULT_BBOX = os.getenv("DEFAULT_BBOX", "25,-125,50,-65")
    NEARBY_PIREP_RADIUS_NM = float(os.getenv("NEARBY_PIREP_RADIUS_NM", "50"))
    NEAREST_METAR_RADIUS_NM = float(os.getenv("NEAREST_METAR_RADIUS_NM", "200"))
    REQUEST_TIMEOUT_S = float(os.getenv("REQUEST_TIMEOUT_S", "10"))