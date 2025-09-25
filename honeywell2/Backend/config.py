from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ✅ CORRECT API URL
    AVIATION_WEATHER_BASE_URL: str = "https://aviationweather.gov/api/data"
    APP_NAME: str = "Aviation Weather Briefing System"
    DEBUG: bool = True

settings = Settings()
