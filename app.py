from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests, logging, math, re, concurrent.futures
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# ──────────────────────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────────────────────
def haversine_nm(lat1, lon1, lat2, lon2):
    """Great-circle distance in nautical miles."""
    R = 3440.065  # earth radius NM
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ, Δλ = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))

def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()

def fmt_utc(dt: datetime) -> str:
    return dt.strftime("%H:%M UTC")

# ──────────────────────────────────────────────────────────────
# Processor Class
# ──────────────────────────────────────────────────────────────
class Wx:
    def __init__(self):
        self.base = "https://aviationweather.gov/api/data"
        self.s = requests.Session()
        self.s.headers["User-Agent"] = "Hackathon-Wx-Brief/1.0"

    # ---------- DATA FETCHERS ----------
    def fetch(self, endpoint, params) -> List[Dict]:
        try:
            r = self.s.get(f"{self.base}/{endpoint}", params=params, timeout=15)
            if r.ok:
                return r.json()
        except Exception as e:
            logging.error(f"{endpoint} fetch error: {e}")
        return []

    def metars_bbox(self, box):      return self.fetch("metar",  dict(bbox=box, format="json", hours=3))
    def tafs_bbox(self, box):        return self.fetch("taf",    dict(bbox=box, format="json"))
    def pireps_bbox(self, box):      return self.fetch("pirep",  dict(bbox=box, format="json", age=6))
    def sigmets(self):               return self.fetch("airsigmet", dict(format="json"))
    def gairmets(self):              return self.fetch("gairmet",   dict(format="json"))
    def cwas(self):                  return self.fetch("cwa",       dict(format="json"))
    def station(self, icao):         return self.fetch("stationinfo", dict(ids=icao, format="json"))

    # ---------- CATEGORISATION ----------
    def category(self, wx: Dict) -> str:
        vis = wx.get("visib", "10")
        speed = wx.get("wspd", 0) or 0
        gust = wx.get("wgst", 0) or 0
        wxs = wx.get("wxString", "") or ""
        cld = wx.get("clouds", [])

        # visibility to miles
        if isinstance(vis, str):
            if "SM" in vis:
                vis = float(re.findall(r"[\\d.]+", vis)[0])
            elif vis == "9999" or vis == "CAVOK":
                vis = 10
            else:
                vis = float(vis) / 1609
        vis = float(vis)

        ceiling = min([c.get("base", 99999) for c in cld
                       if c.get("cover") in ("BKN", "OVC", "VV")] + [99999])

        if any(k in wxs for k in ["+TS", "TS", "+GR", "FC"]) or gust >= 35 or vis < 1 or ceiling < 500:
            return "Severe"
        if any(k in wxs for k in ["SN", "RA", "DZ", "FG"]) or gust >= 25 or vis < 3 or ceiling < 1000:
            return "Significant"
        return "Clear"

    # ---------- FLIGHT PATH ----------
    def path(self, dep, dest, wpts, speed, dep_time) -> List[Dict]:
        pts = [dep] + wpts + [dest]
        coords = {}
        for icao in pts:
            st = self.station(icao)
            if st:
                coords[icao] = dict(lat=st[0]["lat"], lon=st[0]["lon"], name=st[0]["site"])
        if len(coords) < 2:
            return []

        segs, t0 = [], dep_time
        for a, b in zip(pts[:-1], pts[1:]):
            lat1, lon1 = coords[a]["lat"], coords[a]["lon"]
            lat2, lon2 = coords[b]["lat"], coords[b]["lon"]
            dist = haversine_nm(lat1, lon1, lat2, lon2)
            hrs = dist / speed
            segs.append(dict(frm=a, to=b, start=t0, end=t0 + timedelta(hours=hrs),
                             lat1=lat1, lon1=lon1, lat2=lat2, lon2=lon2,
                             dist=dist, hrs=hrs))
            t0 += timedelta(hours=hrs)
        return segs

    # ---------- WEATHER TIMELINE ----------
    def timeline(self, segs, wxdata) -> List[Dict]:
        out = []
        for s in segs:
            intervals = max(1, int(s["hrs"] * 4))      # 15-min blocks
            dt = (s["end"] - s["start"]) / intervals
            for i in range(intervals):
                t1 = s["start"] + dt * i
                t2 = t1 + dt
                prog = (i + 0.5) / intervals
                lat = s["lat1"] + prog * (s["lat2"] - s["lat1"])
                lon = s["lon1"] + prog * (s["lon2"] - s["lon1"])
                cond = self.conditions(lat, lon, t1, wxdata)
                out.append(dict(start=iso(t1), end=iso(t2),
                                start_local=fmt_utc(t1), end_local=fmt_utc(t2),
                                segment=f"{s['frm']}→{s['to']}",
                                loc=self.loc_desc(prog, s),
                                lat=lat, lon=lon,
                                severity=cond["severity"],
                                conditions=cond))
        return out

    # ---------- CONDITION AT POINT ----------
    def conditions(self, lat, lon, time, wxd):
        def nearest(lst):
            best, dmin = None, 1e9
            for w in lst:
                if not w.get("lat"): continue
                d = haversine_nm(lat, lon, w["lat"], w["lon"])
                if d < dmin:
                    best, dmin = w, d
            return best

        met = nearest(wxd["metars"]) or {}
        sev = self.category(met) if met else "Clear"
        desc = []
        if met:
            desc.append(f"Weather: {met.get('wxString','Clear') or 'Clear'}")
            desc.append(f"Vis: {met.get('visib','N/A')}")
            if met.get("wspd"):
                desc.append(f"Wind {met['wdir']}°/{met['wspd']}kt")
        haz = []
        if wxd["sigmets"]:   haz.append("SIGMET active")
        if wxd["gairmets"]:  haz.append("G-AIRMET active")
        if wxd["cwas"]:      haz.append("CWA active")
        if haz: sev = "Severe"
        return dict(severity=sev,
                    condition="; ".join(desc) if desc else "No data",
                    hazards=haz,
                    nearest=met.get("icaoId"))

    def loc_desc(self, prog, seg):
        if prog < .2: return f"Departing {seg['frm']}"
        if prog > .8: return f"Approaching {seg['to']}"
        return f"En route {seg['frm']}→{seg['to']}"

# ──────────────────────────────────────────────────────────────
wx = Wx()

# ------------------------------------------------------------- API ROUTES
@app.route("/")
def root():   return send_from_directory(".", "enhanced_index.html")

@app.route("/<path:path>")
def static_files(path):   return send_from_directory(".", path)

@app.route("/api/enhanced-flight-plan", methods=["POST"])
def api_fp():
    data = request.get_json()
    dep, dest = data.get("departure","").upper(), data.get("destination","").upper()
    wpts = [w.strip().upper() for w in data.get("waypoints",[]) if w.strip()]
    speed = int(data.get("cruise_speed",450))
    dep_time = data.get("departure_time")
    dep_time = datetime.fromisoformat(dep_time.replace("Z","+00:00")) if dep_time else datetime.now(timezone.utc)

    segs = wx.path(dep, dest, wpts, speed, dep_time)
    if not segs: return jsonify(error="Invalid flight path"), 400

    # Build bounding box around path (+2° buffer)
    lats = [p for s in segs for p in (s['lat1'], s['lat2'])]
    lons = [p for s in segs for p in (s['lon1'], s['lon2'])]
    box = f"{min(lats)-2},{min(lons)-2},{max(lats)+2},{max(lons)+2}"

    wxdata = dict(
        metars   = wx.metars_bbox(box),
        tafs     = wx.tafs_bbox(box),
        pireps   = wx.pireps_bbox(box),
        sigmets  = wx.sigmets(),
        gairmets = wx.gairmets(),
        cwas     = wx.cwas(),
    )
    # add category to METARs
    for m in wxdata["metars"]:
        m["category"] = wx.category(m)

    timeline = wx.timeline(segs, wxdata)
    overall = ("Severe" if any(t["severity"]=="Severe" for t in timeline)
               else "Significant" if any(t["severity"]=="Significant" for t in timeline)
               else "Clear")

    return jsonify(
        route=dict(departure=dep, destination=dest, waypoints=wpts,
                   total_distance=sum(s['dist'] for s in segs),
                   total_flight_time=sum(s['hrs'] for s in segs),
                   overall_severity=overall),
        weather_summary=dict(metars_count=len(wxdata['metars']),
                             tafs_count=len(wxdata['tafs']),
                             pireps_count=len(wxdata['pireps']),
                             sigmets_count=len(wxdata['sigmets']),
                             gairmets_count=len(wxdata['gairmets']),
                             cwas_count=len(wxdata['cwas'])),
        timeline=timeline
    )

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
