from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class WeatherCategory(str, Enum):
    SEVERE = "SEVERE"
    SIGNIFICANT = "SIGNIFICANT"
    CLEAR = "CLEAR"

class WeatherProductType(str, Enum):
    METAR = "METAR"
    TAF = "TAF"
    PIREP = "PIREP"
    SIGMET = "SIGMET"
    G_AIRMET = "G-AIRMET"
    AIRMET = "AIRMET"
    CWA = "CWA"

class MetarData(BaseModel):
    station_id: str
    raw_text: str
    observation_time: datetime
    category: WeatherCategory
    wind_speed: Optional[int] = None
    wind_direction: Optional[int] = None
    wind_gust: Optional[int] = None
    visibility: Optional[float] = None
    temperature: Optional[int] = None
    dewpoint: Optional[int] = None
    altimeter: Optional[float] = None
    clouds: List[str] = []
    weather: List[str] = []

class TafData(BaseModel):
    station_id: str
    raw_text: str
    issue_time: datetime
    valid_from: datetime
    valid_until: datetime
    category: WeatherCategory

class PirepData(BaseModel):
    station_id: str
    raw_text: str
    report_time: datetime
    aircraft_type: Optional[str] = None
    altitude: Optional[int] = None
    turbulence: Optional[str] = None
    icing: Optional[str] = None
    category: WeatherCategory

class SigmetData(BaseModel):
    identifier: str
    raw_text: str
    issue_time: datetime
    valid_until: datetime
    phenomenon: str
    category: WeatherCategory = WeatherCategory.SEVERE

class GAirmetData(BaseModel):
    identifier: str
    raw_text: str
    issue_time: datetime
    valid_until: datetime
    hazard_type: str
    category: WeatherCategory = WeatherCategory.SIGNIFICANT

class AirmetData(BaseModel):
    identifier: str
    raw_text: str
    issue_time: datetime
    valid_until: datetime
    hazard_type: str
    category: WeatherCategory = WeatherCategory.SIGNIFICANT

class CwaData(BaseModel):
    identifier: str
    raw_text: str
    issue_time: datetime
    valid_until: datetime
    phenomenon: str
    category: WeatherCategory = WeatherCategory.SIGNIFICANT

class WeatherBriefing(BaseModel):
    station_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    overall_category: WeatherCategory
    pilot_summary: str
    recommendations: List[str] = []
    primary_source: WeatherProductType
    confidence_score: float
    
    # Weather products
    metar_data: Optional[MetarData] = None
    taf_data: Optional[TafData] = None
    pirep_data: List[PirepData] = []
    sigmet_data: List[SigmetData] = []
    gairmet_data: List[GAirmetData] = []
    airmet_data: List[AirmetData] = []
    cwa_data: List[CwaData] = []
    
    available_products: List[WeatherProductType] = []
    hazards: List[Dict[str, Any]] = []
