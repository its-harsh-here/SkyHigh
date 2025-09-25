from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
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

class ProductPriority(BaseModel):
    """Priority and confidence for weather products"""
    product_type: WeatherProductType
    priority: int  # 1 = highest, 7 = lowest
    confidence: float  # 0.0 to 1.0
    recency_weight: float  # How much age affects priority
    
# Priority configuration
WEATHER_PRIORITIES = {
    WeatherProductType.PIREP: ProductPriority(
        product_type=WeatherProductType.PIREP,
        priority=1, confidence=0.95, recency_weight=0.8
    ),
    WeatherProductType.SIGMET: ProductPriority(
        product_type=WeatherProductType.SIGMET,
        priority=2, confidence=0.90, recency_weight=0.3
    ),
    WeatherProductType.METAR: ProductPriority(
        product_type=WeatherProductType.METAR,
        priority=3, confidence=0.85, recency_weight=0.6
    ),
    WeatherProductType.G_AIRMET: ProductPriority(
        product_type=WeatherProductType.G_AIRMET,
        priority=4, confidence=0.75, recency_weight=0.4
    ),
    WeatherProductType.TAF: ProductPriority(
        product_type=WeatherProductType.TAF,
        priority=5, confidence=0.70, recency_weight=0.2
    ),
    WeatherProductType.AIRMET: ProductPriority(
        product_type=WeatherProductType.AIRMET,
        priority=6, confidence=0.65, recency_weight=0.3
    ),
    WeatherProductType.CWA: ProductPriority(
        product_type=WeatherProductType.CWA,
        priority=7, confidence=0.60, recency_weight=0.4
    )
}

# Extended models for each weather product
class PirepData(BaseModel):
    station_id: str
    report_time: datetime
    raw_text: str
    aircraft_type: Optional[str] = None
    altitude: Optional[int] = None
    location: Optional[str] = None
    
    # Weather elements from PIREP
    turbulence: Optional[str] = None
    icing: Optional[str] = None
    visibility: Optional[str] = None
    weather_conditions: Optional[str] = None
    wind: Optional[str] = None
    temperature: Optional[int] = None
    
    category: WeatherCategory
    reliability_score: float = 0.8  # PIREPs are generally reliable

class SigmetData(BaseModel):
    identifier: str
    issue_time: datetime  
    valid_from: datetime
    valid_until: datetime
    raw_text: str
    
    # SIGMET specifics
    phenomenon: str  # TS, ICE, TURB, MTN OBSCN, etc.
    severity: str    # ISOL, OCNL, FRQ, EMBD, etc.
    area: Optional[Dict[str, Any]] = None  # Geographic area
    movement: Optional[str] = None
    forecast: Optional[str] = None
    
    category: WeatherCategory = WeatherCategory.SEVERE  # SIGMETs are always severe

class GAirmetData(BaseModel):
    identifier: str
    issue_time: datetime
    valid_from: datetime
    valid_until: datetime
    raw_text: str
    
    # G-AIRMET specifics  
    hazard_type: str  # TURB, ICE, IFR, etc.
    severity: Optional[str] = None
    base_altitude: Optional[int] = None
    top_altitude: Optional[int] = None
    area_description: Optional[str] = None
    
    category: WeatherCategory

class AirmetData(BaseModel):
    identifier: str
    issue_time: datetime
    valid_from: datetime
    valid_until: datetime
    raw_text: str
    
    # AIRMET specifics
    series: str  # SIERRA, TANGO, ZULU
    hazard_type: str
    area: Optional[str] = None
    
    category: WeatherCategory

class CwaData(BaseModel):
    identifier: str
    issue_time: datetime
    valid_from: datetime
    valid_until: datetime
    raw_text: str
    
    # CWA specifics
    center: str  # Which ARTCC issued it
    phenomenon: str
    area: Optional[str] = None
    
    category: WeatherCategory

# Comprehensive weather briefing
class ComprehensiveWeatherBriefing(BaseModel):
    station_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Smart summary
    primary_source: WeatherProductType
    overall_category: WeatherCategory
    confidence_score: float
    pilot_summary: str
    recommendations: List[str] = []
    
    # Current conditions
    current_conditions: Dict[str, Any] = {}
    forecast: Dict[str, Any] = {}
    hazards: List[Dict[str, Any]] = []
    
    # Individual weather products
    metar_data: Optional["MetarData"] = None
    taf_data: Optional["TafData"] = None  
    pirep_data: List[PirepData] = []
    sigmet_data: List[SigmetData] = []
    gairmet_data: List[GAirmetData] = []
    airmet_data: List[AirmetData] = []
    cwa_data: List[CwaData] = []
    
    # Product availability
    available_products: List[WeatherProductType] = []
    missing_products: List[WeatherProductType] = []

class WeatherAlert(BaseModel):
    alert_type: str  # SEVERE, CAUTION, ADVISORY
    message: str
    source_product: WeatherProductType
    priority: int
    expires_at: Optional[datetime] = None
