"""Tiny helpers shared by the /api serverless handlers."""
import json
import os
import sys

# Make `_lib` importable regardless of how Vercel invokes the handler.
sys.path.insert(0, os.path.dirname(__file__))


def send_json(handler, payload, status=200):
    body = json.dumps(payload).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def read_json_body(handler):
    length = int(handler.headers.get("Content-Length", 0) or 0)
    if not length:
        return {}
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw.decode())
    except Exception:
        return {}


def query_params(handler):
    from urllib.parse import urlparse, parse_qs
    qs = urlparse(handler.path).query
    return {k: v[0] for k, v in parse_qs(qs).items()}
