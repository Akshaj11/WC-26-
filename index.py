"""
Single WSGI entrypoint for Vercel.

Vercel's current Python runtime wants ONE entrypoint (app.py/index.py/etc.)
rather than many handler files. This app routes every /api/* path to the right
provider in api/_lib, and serves the static frontend for everything else.
No external dependencies — pure stdlib WSGI.
"""
import json
import os
import sys
from urllib.parse import urlparse, parse_qs

# Make api/_lib importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))

from _lib import venues, bracket, flights, hotels, scores, tickets  # noqa: E402

from datetime import datetime  # noqa: E402
from zoneinfo import ZoneInfo  # noqa: E402


def kickoff_in_zone(stadium_tz, home_tz, local_hhmm="20:00"):
    try:
        s, h = ZoneInfo(stadium_tz), ZoneInfo(home_tz)
    except Exception:
        return None
    hh, mm = (int(x) for x in local_hhmm.split(":"))
    dt = datetime(2026, 7, 4, hh, mm, tzinfo=s)
    return dt.astimezone(h).strftime("%a %H:%M")


# ---- Route handlers (return a JSON-able dict) -------------------------------

def h_meta(q, body):
    return {
        "venues": [venues.venue_public(k) for k in venues.VENUES],
        "groups": bracket.GROUPS,
        "finishes": bracket.finishes(),
    }


def h_path(q, body):
    group = body.get("group", "A")
    finish = body.get("finish", "win")
    group_city = body.get("group_city", "nyc")
    home_tz = body.get("home_tz", "America/New_York")
    if group_city not in venues.VENUES:
        return {"error": "Unknown city"}
    raw = bracket.path_for_team(group, finish, group_city)
    prev = group_city
    steps = []
    for step in raw:
        cities = []
        for ck in step["cities"]:
            v = venues.venue_public(ck)
            v["leg"] = venues.distance_between(prev, ck)
            v["sample_kickoff_home"] = kickoff_in_zone(v["tz"], home_tz)
            cities.append(v)
        if step["certain"]:
            prev = step["cities"][0]
        steps.append({**step, "cities": cities})
    return {"group": group, "finish": finish, "steps": steps}


def h_flights(q, body):
    origin = q.get("origin", "").upper()
    dest = q.get("dest", "").upper()
    date = q.get("date", "")
    if not (origin and dest and date):
        return {"error": "origin, dest, date required"}
    return flights.search_flights(origin, dest, date, adults=int(q.get("adults", 1)))


def h_hotels(q, body):
    city = q.get("city", "")
    ci = q.get("check_in", "")
    co = q.get("check_out", "")
    if city not in venues.VENUES or not (ci and co):
        return {"error": "valid city, check_in, check_out required"}
    v = venues.VENUES[city]
    return hotels.search_hotels(v.city, venues.COUNTRY_NAMES[v.country], ci, co,
                                adults=int(q.get("adults", 1)))


def h_scores(q, body):
    return scores.live_scores()


def h_tickets(q, body):
    city = q.get("city", "")
    round_label = q.get("round", "Match")
    city_label = venues.VENUES[city].city if city in venues.VENUES else city
    return tickets.tickets_for(city_label, round_label)


ROUTES = {
    "/api/meta": h_meta,
    "/api/path": h_path,
    "/api/flights": h_flights,
    "/api/hotels": h_hotels,
    "/api/scores": h_scores,
    "/api/tickets": h_tickets,
}


def _read_body(environ):
    try:
        size = int(environ.get("CONTENT_LENGTH", 0) or 0)
    except ValueError:
        size = 0
    if size <= 0:
        return {}
    raw = environ["wsgi.input"].read(size)
    try:
        return json.loads(raw.decode())
    except Exception:
        return {}


def _serve_index():
    path = os.path.join(os.path.dirname(__file__), "public", "index.html")
    with open(path, "rb") as f:
        return f.read()


def app(environ, start_response):
    path = urlparse(environ.get("PATH_INFO", "/")).path
    q = {k: v[0] for k, v in parse_qs(environ.get("QUERY_STRING", "")).items()}

    if path in ROUTES:
        body = _read_body(environ) if environ.get("REQUEST_METHOD") == "POST" else {}
        try:
            payload = ROUTES[path](q, body)
            status = "200 OK"
        except Exception as e:
            payload = {"error": str(e)}
            status = "500 Internal Server Error"
        data = json.dumps(payload).encode()
        start_response(status, [
            ("Content-Type", "application/json"),
            ("Cache-Control", "no-store"),
        ])
        return [data]

    # Static frontend for everything else
    try:
        html = _serve_index()
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [html]
    except Exception as e:
        start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
        return [str(e).encode()]
