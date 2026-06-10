from http.server import BaseHTTPRequestHandler
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "_lib"))

from _lib import tickets, venues
from _lib.responses import send_json, query_params


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        p = query_params(self)
        city = p.get("city", "")
        round_label = p.get("round", "Match")
        city_label = venues.VENUES[city].city if city in venues.VENUES else city
        send_json(self, tickets.tickets_for(city_label, round_label))
