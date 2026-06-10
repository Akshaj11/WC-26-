from http.server import BaseHTTPRequestHandler
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "_lib"))

from _lib import venues, bracket
from _lib.responses import send_json


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        send_json(self, {
            "venues": [venues.venue_public(k) for k in venues.VENUES],
            "groups": bracket.GROUPS,
            "finishes": bracket.finishes(),
        })
