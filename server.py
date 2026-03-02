from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import time
import subprocess

# ── Monitor name map ──────────────────────────────────────────────
MONITOR_NAMES = {
    "1": "My Server",
    "2": "Some Service",
    "3": "Another Monitor",
}

# ── Weather cache (fetched once every 30 mins = max 48 calls/day) ─
weather_cache = {"data": None, "last_fetched": 0}
WEATHER_TTL = 30 * 60  # 30 minutes in seconds

def get_weather():
    now = time.time()
    if weather_cache["data"] and (now - weather_cache["last_fetched"]) < WEATHER_TTL:
        return weather_cache["data"]
    try:
        result = subprocess.run([
            "curl", "-s",
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=54.9558&longitude=-7.7183"
            "&hourly=temperature_2m,weathercode,windspeed_10m"
            "&timezone=Europe%2FDublin"
            "&forecast_days=1"
        ], capture_output=True, text=True, timeout=15)
        data = json.loads(result.stdout)
        weather_cache["data"] = data
        weather_cache["last_fetched"] = now
        print(f"[Weather] Fetched fresh data at {time.strftime('%H:%M:%S')}")
        return data
    except Exception as e:
        print(f"[Weather] Fetch failed: {e}")
        return weather_cache["data"]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):

        # ── Uptime Kuma heartbeat proxy ───────────────────────────
        if self.path == "/api/heartbeat":
            try:
                import urllib.request
                with urllib.request.urlopen(
                    "http://172.17.0.1:3001/api/status-page/heartbeat/atu",
                    timeout=10
                ) as r:
                    data = json.loads(r.read())

                data["monitorList"] = {
                    k: {"id": k, "name": v} for k, v in MONITOR_NAMES.items()
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())

            except Exception as e:
                print(f"[Heartbeat] Error: {e}")
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error": "upstream failed"}')

        # ── Weather endpoint ──────────────────────────────────────
        elif self.path == "/api/weather":
            data = get_weather()
            if data:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
            else:
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error": "weather unavailable"}')

        # ── Static file serving ───────────────────────────────────
        else:
            path = self.path.lstrip("/") or "index.html"
            filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
            try:
                with open(filepath, "rb") as f:
                    content = f.read()
                ext = path.split(".")[-1]
                types = {
                    "html": "text/html",
                    "css": "text/css",
                    "js": "application/javascript",
                    "svg": "image/svg+xml",
                    "png": "image/png",
                }
                self.send_response(200)
                self.send_header("Content-Type", types.get(ext, "text/plain"))
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"404 Not Found")

    def log_message(self, format, *args):
        pass


HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
