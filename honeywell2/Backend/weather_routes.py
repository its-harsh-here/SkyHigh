from fastapi import APIRouter, HTTPException, Path
from models import WeatherBriefing
from weather_service import weather_service  # ✅ ADDED MISSING IMPORT

router = APIRouter(prefix="/weather", tags=["weather"])

@router.get("/comprehensive/{station_id}", response_model=WeatherBriefing)
async def get_comprehensive_briefing(
    station_id: str = Path(..., description="4-letter ICAO station identifier")
) -> WeatherBriefing:
    """Get comprehensive weather briefing with all available products"""
    
    if len(station_id) != 4:
        raise HTTPException(status_code=400, detail="Station ID must be 4 characters")
    
    try:
        briefing = await weather_service.fetch_comprehensive_weather(station_id.upper())
        return briefing
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating briefing: {str(e)}")

@router.get("/metar/{station_id}")
async def get_metar(station_id: str = Path(...)):
    """Get METAR data only"""
    try:
        briefing = await weather_service.fetch_comprehensive_weather(station_id.upper())
        return briefing.metar_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching METAR: {str(e)}")

@router.get("/taf/{station_id}")
async def get_taf(station_id: str = Path(...)):
    """Get TAF data only"""
    try:
        briefing = await weather_service.fetch_comprehensive_weather(station_id.upper())
        return briefing.taf_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching TAF: {str(e)}")

@router.get("/pireps/{station_id}")
async def get_pireps(station_id: str = Path(...)):
    """Get PIREP data only"""
    try:
        briefing = await weather_service.fetch_comprehensive_weather(station_id.upper())
        return briefing.pirep_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching PIREPs: {str(e)}")

@router.get("/hazards/{station_id}")
async def get_hazards(station_id: str = Path(...)):
    """Get all hazard products"""
    try:
        briefing = await weather_service.fetch_comprehensive_weather(station_id.upper())
        return {
            "sigmets": briefing.sigmet_data,
            "gairmets": briefing.gairmet_data,
            "airmets": briefing.airmet_data,
            "cwas": briefing.cwa_data,
            "hazard_summary": briefing.hazards
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching hazards: {str(e)}")

@router.get("/summary/{station_id}")
async def get_pilot_summary(station_id: str = Path(...)):
    """Get pilot-focused quick summary"""
    try:
        briefing = await weather_service.fetch_comprehensive_weather(station_id.upper())
        return {
            "station": station_id.upper(),
            "category": briefing.overall_category.value,
            "summary": briefing.pilot_summary,
            "recommendations": briefing.recommendations,
            "confidence": briefing.confidence_score,
            "hazard_count": len(briefing.hazards),
            "products_available": len(briefing.available_products)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")
