"""
Shared WC26 reference data + travel math.

Imported by the serverless functions in /api. Static, accurate tournament
data only — no live numbers here (those come from the provider modules).
"""
from dataclasses import dataclass, asdict
from math import radians, sin, cos, asin, sqrt


@dataclass(frozen=True)
class Venue:
    city: str
    stadium: str
    country: str           # US / MX / CA
    iata: str              # nearest major airport (for flight search)
    lat: float
    lon: float
    tz: str
    tz_label: str


# 16 host venues. IATA = primary airport used for flight/hotel queries.
VENUES = {
    "nyc":         Venue("New York / NJ", "MetLife Stadium",         "US", "EWR", 40.8135, -74.0745, "America/New_York",    "ET"),
    "philly":      Venue("Philadelphia",  "Lincoln Financial Field", "US", "PHL", 39.9008, -75.1675, "America/New_York",    "ET"),
    "boston":      Venue("Boston",        "Gillette Stadium",        "US", "BOS", 42.0909, -71.2643, "America/New_York",    "ET"),
    "miami":       Venue("Miami",         "Hard Rock Stadium",       "US", "MIA", 25.9580, -80.2389, "America/New_York",    "ET"),
    "atlanta":     Venue("Atlanta",       "Mercedes-Benz Stadium",   "US", "ATL", 33.7554, -84.4008, "America/New_York",    "ET"),
    "kansascity":  Venue("Kansas City",   "Arrowhead Stadium",       "US", "MCI", 39.0489, -94.4839, "America/Chicago",     "CT"),
    "dallas":      Venue("Dallas",        "AT&T Stadium",            "US", "DFW", 32.7473, -97.0945, "America/Chicago",     "CT"),
    "houston":     Venue("Houston",       "NRG Stadium",             "US", "IAH", 29.6847, -95.4107, "America/Chicago",     "CT"),
    "seattle":     Venue("Seattle",       "Lumen Field",             "US", "SEA", 47.5952, -122.3316,"America/Los_Angeles", "PT"),
    "bayarea":     Venue("SF Bay Area",   "Levi's Stadium",          "US", "SJC", 37.4030, -121.9700,"America/Los_Angeles", "PT"),
    "la":          Venue("Los Angeles",   "SoFi Stadium",            "US", "LAX", 33.9535, -118.3392,"America/Los_Angeles", "PT"),
    "toronto":     Venue("Toronto",       "BMO Field",               "CA", "YYZ", 43.6332, -79.4185, "America/Toronto",     "ET"),
    "vancouver":   Venue("Vancouver",     "BC Place",                "CA", "YVR", 49.2768, -123.1119,"America/Vancouver",   "PT"),
    "mexicocity":  Venue("Mexico City",   "Estadio Azteca",          "MX", "MEX", 19.3029, -99.1505, "America/Mexico_City", "CT"),
    "guadalajara": Venue("Guadalajara",   "Estadio Akron",           "MX", "GDL", 20.6817, -103.4628,"America/Mexico_City", "CT"),
    "monterrey":   Venue("Monterrey",     "Estadio BBVA",            "MX", "MTY", 25.6690, -100.2440,"America/Monterrey",   "CT"),
}

COUNTRY_NAMES = {"US": "United States", "MX": "Mexico", "CA": "Canada"}

# Stadium detail for fans. Capacities are FIFA tournament-config figures (approx,
# can shift with overlay). fifa_name = neutral name used during the tournament.
# tenant = usual occupant. region = FIFA's travel region grouping. roof/notes
# give a quick feel for the venue.
STADIUM_INFO = {
    "nyc":         {"fifa_name": "New York New Jersey Stadium", "capacity": 82500, "tenant": "NY Giants / NY Jets (NFL)", "region": "Eastern", "roof": "Open air", "note": "Hosts the Final on July 19. ~8 mi from Manhattan; NJ Transit to Meadowlands on match days."},
    "philly":      {"fifa_name": "Philadelphia Stadium",        "capacity": 69000, "tenant": "Philadelphia Eagles (NFL)", "region": "Eastern", "roof": "Open air", "note": "In the South Philly sports complex; Broad Street Line subway runs right to it."},
    "boston":      {"fifa_name": "Boston Stadium",              "capacity": 65000, "tenant": "New England Patriots (NFL)", "region": "Eastern", "roof": "Open air", "note": "In Foxborough, ~30 mi from Boston; special event trains from South Station."},
    "miami":       {"fifa_name": "Miami Stadium",               "capacity": 65000, "tenant": "Miami Dolphins (NFL)", "region": "Eastern", "roof": "Canopy over seats", "note": "Hosts the third-place playoff. In Miami Gardens, ~16 mi north of downtown."},
    "atlanta":     {"fifa_name": "Atlanta Stadium",             "capacity": 75000, "tenant": "Atlanta Falcons (NFL)", "region": "Eastern", "roof": "Retractable", "note": "Hosts a semi-final. Downtown, served by MARTA rail (GWCC/CNN Center)."},
    "kansascity":  {"fifa_name": "Kansas City Stadium",         "capacity": 73000, "tenant": "Kansas City Chiefs (NFL)", "region": "Central", "roof": "Open air", "note": "Famous for being one of the loudest stadiums in sport; big tailgating culture."},
    "dallas":      {"fifa_name": "Dallas Stadium",              "capacity": 94000, "tenant": "Dallas Cowboys (NFL)", "region": "Central", "roof": "Retractable", "note": "The tournament's largest venue and a semi-final host. In Arlington, between Dallas & Fort Worth."},
    "houston":     {"fifa_name": "Houston Stadium",             "capacity": 72000, "tenant": "Houston Texans (NFL)", "region": "Central", "roof": "Retractable", "note": "Climate-controlled comfort in the Texas summer; METRORail to the stadium district."},
    "seattle":     {"fifa_name": "Seattle Stadium",             "capacity": 69000, "tenant": "Seattle Seahawks (NFL)", "region": "Western", "roof": "Partial cover", "note": "Walkable from downtown Seattle; light rail stops nearby."},
    "bayarea":     {"fifa_name": "San Francisco Bay Area Stadium", "capacity": 71000, "tenant": "San Francisco 49ers (NFL)", "region": "Western", "roof": "Open air", "note": "In Santa Clara, ~45 mi south of SF; VTA light rail and Caltrain access."},
    "la":          {"fifa_name": "Los Angeles Stadium",         "capacity": 70000, "tenant": "LA Rams / LA Chargers (NFL)", "region": "Western", "roof": "Fixed canopy", "note": "Ultra-modern venue in Inglewood, near LAX; Metro K Line serves the area."},
    "toronto":     {"fifa_name": "Toronto Stadium",             "capacity": 43000, "tenant": "Toronto FC (MLS)", "region": "Eastern", "roof": "Open air", "note": "The tournament's most intimate venue; on the lakefront, streetcar access from downtown."},
    "vancouver":   {"fifa_name": "Vancouver Stadium",           "capacity": 54000, "tenant": "BC Lions (CFL) / Whitecaps", "region": "Western", "roof": "Retractable", "note": "Right downtown; SkyTrain Stadium–Chinatown station at the door."},
    "mexicocity":  {"fifa_name": "Mexico City Stadium",         "capacity": 80824, "tenant": "Club América / Cruz Azul", "region": "Central", "roof": "Open air", "note": "Hosts the opening match. The only stadium to host three World Cups; at 2,200m altitude."},
    "guadalajara": {"fifa_name": "Guadalajara Stadium",         "capacity": 48000, "tenant": "C.D. Guadalajara (Chivas)", "region": "Central", "roof": "Open air", "note": "Striking volcano-like design on the city's edge in Zapopan."},
    "monterrey":   {"fifa_name": "Monterrey Stadium",           "capacity": 53500, "tenant": "C.F. Monterrey (Rayados)", "region": "Central", "roof": "Open air", "note": "Dramatic mountain backdrop of Cerro de la Silla; in Guadalupe, near Monterrey."},
}


def stadium_info(key: str) -> dict:
    """Stadium detail for the info panel, or an empty dict if unknown."""
    return STADIUM_INFO.get(key, {})


# --- Map projection: lat/lon -> SVG x/y over a North America viewBox ---------
# Equirectangular projection tuned to the host-nation bounding box. Returns
# coordinates in an 880 x 620 viewBox used by the inline SVG map.
_MAP_W, _MAP_H = 880, 620
_LON_MIN, _LON_MAX = -125.5, -69.0
_LAT_MIN, _LAT_MAX = 17.5, 50.5


def project(lat: float, lon: float):
    x = (lon - _LON_MIN) / (_LON_MAX - _LON_MIN) * _MAP_W
    y = (_LAT_MAX - lat) / (_LAT_MAX - _LAT_MIN) * _MAP_H
    return round(x, 1), round(y, 1)


def map_points() -> dict:
    """All venues projected to map x/y, plus the viewBox dims."""
    pts = {}
    for k, v in VENUES.items():
        x, y = project(v.lat, v.lon)
        pts[k] = {"x": x, "y": y, "city": v.city, "country": v.country}
    return {"w": _MAP_W, "h": _MAP_H, "points": pts}


def haversine_km(a: Venue, b: Venue) -> float:
    r = 6371.0
    dlat = radians(b.lat - a.lat); dlon = radians(b.lon - a.lon)
    lat1, lat2 = radians(a.lat), radians(b.lat)
    h = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return 2 * r * asin(sqrt(h))


def distance_between(origin_key: str, dest_key: str) -> dict:
    """Geographic facts only — distance is real (computed), no fabricated prices."""
    o, d = VENUES[origin_key], VENUES[dest_key]
    km = haversine_km(o, d)
    return {
        "from": origin_key, "to": dest_key,
        "distance_km": round(km),
        "distance_mi": round(km * 0.621371),
        "cross_border": o.country != d.country,
        "same_city": origin_key == dest_key,
        "origin_iata": o.iata, "dest_iata": d.iata,
    }


def venue_public(key: str) -> dict:
    v = VENUES[key]
    out = asdict(v); out["key"] = key
    out["country_name"] = COUNTRY_NAMES[v.country]
    out["stadium_info"] = STADIUM_INFO.get(key, {})
    return out
