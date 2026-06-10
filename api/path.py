from http.server import BaseHTTPRequestHandler
from datetime import datetime
from zoneinfo import ZoneInfo
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from _lib import venues, bracket
from _lib.responses import send_json, read_json_body


def kickoff_in_zone(stadium_tz, home_tz, local_hhmm="20:00"):
    try:
        s, h = ZoneInfo(stadium_tz), ZoneInfo(home_tz)
    except Exception:
        return None
    hh, mm = (int(x) for x in local_hhmm.split(":"))
    dt = datetime(2026, 7, 4, hh, mm, tzinfo=s)
    return dt.astimezone(h).strftime("%a %H:%M")


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = read_json_body(self)
        group = body.get("group", "A")
        finish = body.get("finish", "win")
        group_city = body.get("group_city", "nyc")
        home_tz = body.get("home_tz", "America/New_York")

        if group_city not in venues.VENUES:
            return send_json(self, {"error": "Unknown city"}, 400)

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

        send_json(self, {"group": group, "finish": finish, "steps": steps})
