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
    return out
