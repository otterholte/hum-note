"""Hum to MIDI local server.

Serves the page at http://127.0.0.1:8765/ (only reachable from this computer) and saves
takes straight into the recordings folder, so nothing goes to Downloads and Chrome can
remember the microphone permission for this address.
"""
import json, os, re, sys
os.environ.setdefault("SD_ENABLE_ASIO", "1")  # must be set before sounddevice is first imported
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.abspath(__file__))
REC = os.path.join(ROOT, "recordings")
PORT = 8765
AUDIO = re.compile(r"\.(wav|m4a|mp3|ogg|webm|aac|flac)$", re.I)
SAFE = re.compile(r"^[A-Za-z0-9_\-. ()]+\.(wav|m4a|mp3|ogg|webm|aac|flac|json|mid)$", re.I)


class Monitor:
    """'Hear myself': mic -> headphones through Windows kernel streaming (about 20 ms on a USB interface).
    Falls back to WASAPI shared if the direct path isn't available."""

    def __init__(self):
        self.stream, self.gain, self.mode = None, 0.8, ""
        try:
            import numpy, sounddevice  # noqa: F401
            self.ok = True
        except Exception:
            self.ok = False

    def _cb(self, indata, outdata, frames, t, status):
        import numpy as np
        x = indata.sum(axis=1) * self.gain  # mic may be on input 1 or 2: hear both
        np.clip(x, -1, 1, out=x)
        outdata[:] = x[:, None]

    def start(self):
        if self.stream or not self.ok:
            return self.status()
        import sounddevice as sd
        apis = sd.query_hostapis()
        tries = []
        for word, label in (("WDM-KS", "direct"), ("WASAPI", "shared")):
            for i, h in enumerate(apis):
                if word in h["name"] and h["default_input_device"] >= 0 and h["default_output_device"] >= 0:
                    tries.append((h["default_input_device"], h["default_output_device"], label))
        for di, do, label in tries:
            try:
                ind, outd = sd.query_devices(di), sd.query_devices(do)
                s = sd.Stream(device=(di, do), samplerate=int(outd["default_samplerate"]),
                              channels=(min(2, ind["max_input_channels"]), min(2, outd["max_output_channels"])),
                              dtype="float32", latency=0.003, blocksize=0, callback=self._cb)
                s.start()
                self.stream, self.mode = s, label
                break
            except Exception:
                continue
        return self.status()

    def stop(self):
        if self.stream:
            try:
                self.stream.stop(); self.stream.close()
            except Exception:
                pass
        self.stream = None
        return self.status()

    def status(self):
        d = round(sum(self.stream.latency) * 1000) if self.stream else None
        return {"available": self.ok, "on": bool(self.stream), "delay_ms": d, "mode": self.mode if self.stream else ""}


MON = Monitor()
from live_engine import LIVE  # noqa: E402  (native live notes)


class Handler(SimpleHTTPRequestHandler):
    # module scripts and wasm need their proper types (the pitch model's runtime loads both)
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.mjs': 'text/javascript', '.js': 'text/javascript', '.wasm': 'application/wasm', '.onnx': 'application/octet-stream'}
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def log_message(self, *a):  # keep quiet
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _local_only(self):
        # only pages served by this server may save (blocks other websites from writing files)
        origin = self.headers.get("Origin")
        return origin in (None, f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}")

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/ping":
            return self._json({"ok": True})
        if u.path == "/api/monitor":
            return self._json(MON.status())
        if u.path == "/api/live":
            return self._json(LIVE.status())
        if u.path == "/api/takes":
            os.makedirs(REC, exist_ok=True)
            items = sorted((f for f in os.listdir(REC) if AUDIO.search(f)), reverse=True)
            return self._json(items)
        return super().do_GET()

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/monitor" and self._local_only():
            q = parse_qs(u.query)
            if "vol" in q:
                MON.gain = max(0.0, min(1.5, float(q["vol"][0])))
            if "on" in q:
                return self._json(MON.start() if q["on"][0] == "1" else MON.stop())
            return self._json(MON.status())
        if u.path == "/api/live" and self._local_only():
            # live notes: ?on=1|0  &snd=pluck|keys|bass|lead|pad  &stick=0..1  &vel=1|0  &vowel=1|0  &vol=0..1.5  &key=0,2,4,... (allowed pitch classes)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            p = {}
            if "snd" in q: p["snd"] = q["snd"]
            if "stick" in q: p["stick"] = max(0.0, min(1.0, float(q["stick"])))
            if "vel" in q: p["vel"] = q["vel"] == "1"
            if "vowel" in q: p["vowel"] = q["vowel"] == "1"
            if "vol" in q: p["vol"] = max(0.0, min(1.5, float(q["vol"])))
            if "key" in q: p["allowed"] = [int(x) % 12 for x in q["key"].split(",") if x.strip().lstrip("-").isdigit()] or list(range(12))
            LIVE.set(**p)
            if "on" in q:
                if q["on"] == "1":
                    MON.stop()
                    return self._json(LIVE.start())
                return self._json(LIVE.stop())
            return self._json(LIVE.status())
        if u.path == "/api/delete" and self._local_only():
            # delete one take file (name=) or every file of one take (base=), only inside recordings
            q = parse_qs(u.query)
            names = []
            if "name" in q:
                n = os.path.basename(q["name"][0])
                if SAFE.match(n):
                    names = [n]
            elif "base" in q:
                b = os.path.basename(q["base"][0])
                if b and re.match(r"^[A-Za-z0-9_\-. ()]+$", b) and ".." not in b and os.path.isdir(REC):
                    names = [f for f in os.listdir(REC) if SAFE.match(f) and os.path.splitext(f)[0] == b]
            if not names and "name" not in q:
                return self._json({"error": "nothing to delete"}, 400)
            gone = []
            for n in names:
                fp = os.path.join(REC, n)
                if os.path.isfile(fp):
                    os.remove(fp); gone.append(n)
            return self._json({"deleted": gone})
        if u.path != "/api/save" or not self._local_only():
            return self._json({"error": "not allowed"}, 403)
        name = os.path.basename(parse_qs(u.query).get("name", [""])[0])
        if not SAFE.match(name):
            return self._json({"error": "bad name"}, 400)
        n = int(self.headers.get("Content-Length", "0"))
        if n <= 0 or n > 300 * 1024 * 1024:
            return self._json({"error": "bad size"}, 400)
        data = self.rfile.read(n)
        os.makedirs(REC, exist_ok=True)
        tmp = os.path.join(REC, name + ".part")
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, os.path.join(REC, name))
        return self._json({"saved": name})


def make_server():
    """Returns a server, or None if one is already running on this port."""
    try:
        return ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        return None


if __name__ == "__main__":
    srv = make_server()
    if not srv:
        sys.exit(0)  # already running
    srv.serve_forever()
