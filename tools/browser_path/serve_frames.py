"""Tiny static server (with CORS) for the sampled frames, port 8199, bound to 127.0.0.1. Started and stopped by the benchmark only."""
import functools
import http.server
from pathlib import Path

HERE = Path(__file__).parent


class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, *a):
        pass


http.server.ThreadingHTTPServer(("127.0.0.1", 8199), functools.partial(H, directory=str(HERE / "frames"))).serve_forever()
