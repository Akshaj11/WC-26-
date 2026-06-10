from http.server import BaseHTTPRequestHandler
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from _lib import flights
from _lib.responses import send_json, query_params


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        p = query_params(self)
        origin = p.get("origin", "").upper()
        dest = p.get("dest", "").upper()
        date = p.get("date", "")
        if not (origin and dest and date):
            return send_json(self, {"error": "origin, dest, date required"}, 400)
        send_json(self, flights.search_flights(origin, dest, date,
                                                adults=int(p.get("adults", 1))))
