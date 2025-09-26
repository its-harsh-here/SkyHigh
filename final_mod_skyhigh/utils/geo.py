# utils/geo.py
import math

EARTH_RADIUS_NM = 3440.065

def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1r, lon1r, lat2r, lon2r = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2r - lat1r
    dlon = lon2r - lon1r
    a = math.sin(dlat/2)**2 + math.cos(lat1r) * math.cos(lat2r) * math.sin(dlon/2)**2
    return 2 * EARTH_RADIUS_NM * math.asin(math.sqrt(a))
