from http.server import BaseHTTPRequestHandler
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from _lib import scores
from _lib.responses import send_json


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        send_json(self, scores.live_scores())
