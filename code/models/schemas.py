# models/schemas.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class FlightSegment:
    from_icao: str
    to_icao: str
    distance_nm: float
    flight_time_hours: float
    start_time: datetime
    end_time: datetime
    from_coords: Dict[str, float]
    to_coords: Dict[str, float]

@dataclass
class RiskAssessment:
    risk_level: str
    risk_percentage: float
    recommendation: str
    severe_segments: int
    significant_segments: int
    total_segments: int

@dataclass
class FlightPlanInput:
    departure: str
    destination: str
    waypoints: List[str] = field(default_factory=list)
    cruise_speed: int = 450
    departure_time: Optional[str] = None  # ISO string from client

@dataclass
class WeatherQueryContext:
    bbox: Optional[str] = None
    airports: List[str] = field(default_factory=list)
    departure_time: Optional[datetime] = None
