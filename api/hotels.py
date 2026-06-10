from http.server import BaseHTTPRequestHandler
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from _lib import hotels, venues
from _lib.responses import send_json, query_params


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        p = query_params(self)
        city = p.get("city", "")
        check_in = p.get("check_in", "")
        check_out = p.get("check_out", "")
        if city not in venues.VENUES or not (check_in and check_out):
            return send_json(self, {"error": "valid city, check_in, check_out required"}, 400)
        v = venues.VENUES[city]
        send_json(self, hotels.search_hotels(
            v.city, venues.COUNTRY_NAMES[v.country], check_in, check_out,
            adults=int(p.get("adults", 1))))
