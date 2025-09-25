from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional
from models.extended_weather_models import *
from services.comprehensive_weather_service import weather_service

router = APIRouter(prefix="/weather", tags=["comprehensive-weather"])

@router.get("/comprehensive/{station_id}", response_model=ComprehensiveWeatherBriefing)
async def get_comprehensive_briefing(
    station_id: str = Path(..., description="4-letter ICAO station identifier"),
    radius_nm: int = Query(50, description="Radius in nautical miles for area products")
) -> ComprehensiveWeatherBriefing:
    """Get comprehensive weather briefing with all available products"""
    
    if len(station_id) != 4:
        raise HTTPException(status_code=400, detail="Station ID must be 4 characters")
    
    try:
        briefing = await weather_service.fetch_all_weather_data(
            station_id.upper(), radius_nm
        )
        return briefing
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error generating comprehensive briefing: {str(e)}"
        )

@router.get("/products/{station_id}/metar", response_model=Optional[MetarData])
async def get_station_metar(station_id: str = Path(...)) -> Optional[MetarData]:
    """Get METAR data only"""
    briefing = await weather_service.fetch_all_weather_data(station_id.upper())
    return briefing.metar_data

@router.get("/products/{station_id}/taf", response_model=Optional[TafData])
async def get_station_taf(station_id: str = Path(...)) -> Optional[TafData]:
    """Get TAF data only"""
    briefing = await weather_service.fetch_all_weather_data(station_id.upper())
    return briefing.taf_data

@router.get("/products/{station_id}/pireps", response_model=List[PirepData])
async def get_station_pireps(
    station_id: str = Path(...),
    radius_nm: int = Query(50)
) -> List[PirepData]:
    """Get PIREP data only"""
    briefing = await weather_service.fetch_all_weather_data(station_id.upper(), radius_nm)
    return briefing.pirep_data

@router.get("/products/{station_id}/sigmets", response_model=List[SigmetData])
async def get_station_sigmets(
    station_id: str = Path(...),
    radius_nm: int = Query(100)
) -> List[SigmetData]:
    """Get SIGMET data only"""
    briefing = await weather_service.fetch_all_weather_data(station_id.upper(), radius_nm)
    return briefing.sigmet_data

@router.get("/products/{station_id}/gairmets", response_model=List[GAirmetData])
async def get_station_gairmets(
    station_id: str = Path(...),
    radius_nm: int = Query(100)
) -> List[GAirmetData]:
    """Get G-AIRMET data only"""
    briefing = await weather_service.fetch_all_weather_data(station_id.upper(), radius_nm)
    return briefing.gairmet_data

@router.get("/products/{station_id}/airmets", response_model=List[AirmetData])
async def get_station_airmets(
    station_id: str = Path(...),
    radius_nm: int = Query(100)
) -> List[AirmetData]:
    """Get AIRMET data only"""
    briefing = await weather_service.fetch_all_weather_data(station_id.upper(), radius_nm)
    return briefing.airmet_data

@router.get("/products/{station_id}/cwas", response_model=List[CwaData])
async def get_station_cwas(
    station_id: str = Path(...),
    radius_nm: int = Query(100)
) -> List[CwaData]:
    """Get CWA data only"""
    briefing = await weather_service.fetch_all_weather_data(station_id.upper(), radius_nm)
    return briefing.cwa_data

@router.get("/summary/{station_id}")
async def get_pilot_summary(station_id: str = Path(...)):
    """Get pilot-focused summary optimized for quick decision making"""
    
    briefing = await weather_service.fetch_all_weather_data(station_id.upper())
    
    return {
        "station": station_id.upper(),
        "category": briefing.overall_category.value,
        "confidence": briefing.confidence_score,
        "pilot_summary": briefing.pilot_summary,
        "recommendations": briefing.recommendations,
        "primary_source": briefing.primary_source.value,
        "available_products": [p.value for p in briefing.available_products],
        "hazard_count": len(briefing.hazards),
        "generated_at": briefing.generated_at.isoformat()
    }

@router.get("/hazards/{station_id}")
async def get_weather_hazards(
    station_id: str = Path(...),
    radius_nm: int = Query(100)
):
    """Get all weather hazards (SIGMETs, AIRMETs, G-AIRMETs) for area"""
    
    briefing = await weather_service.fetch_all_weather_data(station_id.upper(), radius_nm)
    
    return {
        "station": station_id.upper(),
        "hazards": briefing.hazards,
        "hazard_summary": {
            "total_hazards": len(briefing.hazards),
            "sigmets": len(briefing.sigmet_data),
            "gairmets": len(briefing.gairmet_data), 
            "airmets": len(briefing.airmet_data),
            "cwas": len(briefing.cwa_data)
        },
        "recommendations": [r for r in briefing.recommendations if "WARNING" in r or "AVOID" in r]
    }

@router.get("/raw/{station_id}/{product_type}")
async def get_raw_weather_data(
    station_id: str = Path(...),
    product_type: str = Path(..., description="metar, taf, pireps, sigmets, etc.")
):
    """Get raw weather data for specific product type"""
    
    briefing = await weather_service.fetch_all_weather_data(station_id.upper())
    
    raw_data = []
    
    if product_type.lower() == "metar" and briefing.metar_data:
        raw_data.append({"raw_text": briefing.metar_data.raw_text})
    
    elif product_type.lower() == "taf" and briefing.taf_data:
        raw_data.append({"raw_text": briefing.taf_data.raw_text})
    
    elif product_type.lower() == "pireps":
        raw_data = [{"raw_text": p.raw_text} for p in briefing.pirep_data]
    
    elif product_type.lower() == "sigmets":
        raw_data = [{"raw_text": s.raw_text} for s in briefing.sigmet_data]
    
    elif product_type.lower() == "gairmets":
        raw_data = [{"raw_text": g.raw_text} for g in briefing.gairmet_data]
    
    elif product_type.lower() == "airmets":
        raw_data = [{"raw_text": a.raw_text} for a in briefing.airmet_data]
    
    elif product_type.lower() == "cwas":
        raw_data = [{"raw_text": c.raw_text} for c in briefing.cwa_data]
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown product type: {product_type}")
    
    return {
        "station": station_id.upper(),
        "product_type": product_type.upper(),
        "count": len(raw_data),
        "raw_data": raw_data
    }
