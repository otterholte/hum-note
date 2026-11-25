"""Humnote live notes: mic -> pitch -> synth, all inside this program (no browser in the sound path).

Sound goes in and out through Windows' direct audio path (WDM-KS, a few ms each way on a USB interface), falling
back to WASAPI. Every audio block (~3 ms):
  1. pitch: YIN on the newest ~21 ms of the mic (fast and simple; the careful AI transcription still runs on the take)
  2. note: snapped to the chosen key's notes (or any semitone), with "stickiness": once a note plays it is held until
     the voice clearly moves to another note for a moment, so wobbles, scoops and vibrato don't flip it
  3. synth: a small built-in synth plays the note; how loud you start sets the velocity, and the vowel you sing
     (oo / ah / ee) opens or closes the tone filter. Your voice itself is never played back.
"""
import math, os, threading, time
os.environ.setdefault("SD_ENABLE_ASIO", "1")  # lets PortAudio use the interface's ASIO driver (a few ms each way)

try:
    import numpy as np
    import sounddevice as sd
    from scipy.signal import lfilter
    OK = True
except Exception:  # pragma: no cover
    OK = False

SOUNDS = ("pluck", "keys", "bass", "lead", "pad")


class Analyzer:
    """Pitch + note decisions. Fed audio blocks; returns note events. Independent of the sound card (testable)."""

    def __init__(self, sr):
        self.sr = sr
        self.Wmax = int(sr * 0.021)                   # longest analysis window
        self.W = int(sr * 0.014)                      # current window: ~2 cycles of the voice (shorter = quicker)
        self.tmin, self.tmax = int(sr / 1100), int(sr / 65)
        self.buf = np.zeros(self.Wmax + self.tmax + 8, np.float32)
        self.hop = max(16, int(sr * 0.0015))          # a fresh reading every ~1.5 ms
        self.acc = 0
        self.choked = False
        self.choke_t = 0.0
        self.hist = []            # (t, pitch) of the last 0.4 s of voice, for the octave check
        self.oct_t = None
        self.recent = []
        self.head_t = None
        self.on_t = 0.0
        self.dip_t = 0.0
        self.allowed = set(range(12))
        self.stick = 0.5
        self.noise = 0.003
        self.note = None          # midi note playing
        self.cand = None          # (note, since_t)
        self.quiet = 0.0
        self.t = 0.0
        self.peak = 0.0           # loudest moment of the current note (for re-sung syllables)
        self.dipped = False
        self.rms = 0.0
        self.tone = 0.5           # 0 = "oo" (dark) .. 1 = "ee" (bright)
        self.midi = float("nan")
        self.hann = np.hanning(1024).astype(np.float32)
        f = np.fft.rfftfreq(1024, 1 / sr)
        self.lo_band = (f >= 150) & (f < 900)
        self.hi_band = (f >= 1400) & (f < 4000)

    def yin(self, x):
        W, tmax = self.W, self.tmax
        a = x[:W]
        N = 1 << (2 * (W + tmax) - 1).bit_length()
        F = np.fft.rfft(x[: W + tmax], N)
        r = np.fft.irfft(np.conj(np.fft.rfft(a, N)) * F, N)[: tmax + 1]
        cs = np.concatenate(([0.0], np.cumsum(x.astype(np.float64) ** 2)))
        e0 = cs[W]
        et = cs[np.arange(tmax + 1) + W] - cs[np.arange(tmax + 1)]
        d = e0 + et - 2 * r
        d[0] = 0
        cm = np.ones_like(d)
        c = np.cumsum(d[1:])
        cm[1:] = d[1:] * np.arange(1, tmax + 1) / np.maximum(c, 1e-12)
        lo = self.tmin
        seg = cm[lo:]
        below = np.nonzero(seg < 0.15)[0]
        if below.size:
            i = below[0] + lo
            while i + 1 <= tmax and cm[i + 1] < cm[i]:
                i += 1
        else:
            i = int(np.argmin(seg)) + lo
        h = int(round(i / 2))
        if h >= self.tmin:
            j = max(self.tmin, h - 2) + int(np.argmin(cm[max(self.tmin, h - 2): h + 3]))
            if cm[j] < 0.2 or cm[j] < 1.3 * cm[i]:
                i = j
        ap = float(cm[i])
        if 1 <= i < tmax:
            s0, s1, s2 = cm[i - 1], cm[i], cm[i + 1]
            den = s0 - 2 * s1 + s2
            p = i + (0.5 * (s0 - s2) / den if abs(den) > 1e-12 else 0)
        else:
            p = float(i)
        return self.sr / p, ap

    def snap(self, m):
        best, bd = None, 99.0
        for p in range(int(math.floor(m)) - 3, int(math.ceil(m)) + 4):
            if p % 12 in self.allowed and abs(m - p) < bd:
                best, bd = p, abs(m - p)
        return best

    def feed(self, x):
        """x: mono block. Returns list of events: ('on', note, velocity 0..1) / ('off',)."""
        n = len(x)
        self.buf = np.roll(self.buf, -n)
        self.buf[-n:] = x[-len(self.buf):] if n > len(self.buf) else x
        self.t += n / self.sr
        self.acc += n
        if self.acc < self.hop:
            return []
        dt = self.acc / self.sr
        self.acc = 0
        w = self.buf[-(self.W + self.tmax):][::-1].copy()  # newest samples first, so the reading reflects the latest audio
        cur = self.buf[-self.W:]
        rms = float(np.sqrt(np.mean(cur * cur)) + 1e-9)
        self.rms = rms
        f, ap = self.yin(w)
        gate = max(0.002, 3.0 * self.noise)
        voiced = rms > gate and ap < 0.3 and 65 <= f <= 1100
        if not voiced:
            self.noise += (min(rms, 0.05) - self.noise) * min(1.0, dt / 0.5)
        ev = []
        s = self.stick
        if voiced:
            m = 69 + 12 * math.log2(f / 440.0)
            # octave slip guard: a sudden jump of about an octave from where the voice has just been is almost always
            # the tracker (a short window can lock onto half or double the pitch, e.g. vocal fry at a phrase end).
            # A drop of an octave must last 150 ms to be believed, a rise 80 ms.
            ref = self.note
            if ref is None and len(self.hist) >= 5 and self.t - self.hist[-1][0] < 0.3:
                ref = float(np.median([h[1] for h in self.hist]))
            if ref is not None:
                k = round((m - ref) / 12)
                if k and abs(m - 12 * k - ref) < 2.6:
                    if self.oct_t is None:
                        self.oct_t = self.t
                    if self.t - self.oct_t < (0.15 if k < 0 else 0.08):
                        m -= 12 * k
                else:
                    self.oct_t = None
            self.hist.append((self.t, m))
            while self.hist and self.t - self.hist[0][0] > 0.4:
                self.hist.pop(0)
            # steady = not mid-scoop: the pitch has stayed within ~1/3 semitone for a moment (4 ms at the
            # lowest stickiness, up to 20 ms at the highest, so a slide into a note doesn't play the note it slid from)
            self.recent.append((self.t, m))
            span = 0.004 + 0.016 * s
            while self.recent and self.t - self.recent[0][0] > span + 0.002:
                self.recent.pop(0)
            vals = [v for _, v in self.recent]
            steady = self.t - self.recent[0][0] >= span - 0.0015 and max(vals) - min(vals) < 0.35
            self.midi = m
            fc = 440.0 * 2 ** ((m - 69) / 12)   # size the next window from the corrected pitch, not a slip
            self.W = int(self.sr * min(0.021, max(0.007, 2.2 / fc)))
            seg = self.hann * self.buf[-1024:]
            sp = np.abs(np.fft.rfft(seg)) ** 2
            lo, hi = sp[self.lo_band].sum(), sp[self.hi_band].sum()
            b = hi / (lo + hi + 1e-12)
            tgt = min(1.0, max(0.0, (b - 0.02) / 0.35))
            self.tone += (tgt - self.tone) * min(1.0, dt / 0.04)
            self.quiet = 0.0
            p = self.snap(m)
            if self.note is None:
                if self.cand and self.cand[0] == p:
                    if self.t - self.cand[1] >= 0.004 and steady:
                        ev.append(("on", p, self.vel(rms)))
                        self.note, self.cand, self.peak, self.dipped, self.on_t = p, None, rms, False, self.t
                else:
                    self.cand = (p, self.t)
            else:
                self.peak = max(self.peak, rms)
                # the same note sung again (a new syllable): the voice dips, then comes back up
                if rms < 0.3 * self.peak:
                    if not self.dipped:
                        self.dipped, self.dip_t = True, self.t
                elif self.dipped and rms > 0.6 * self.peak:
                    self.dipped = False
                    if self.t - self.dip_t >= 0.025 and self.t - self.on_t >= 0.12:
                        self.peak, self.on_t = rms, self.t
                        ev.append(("on", self.note, self.vel(rms)))
                away = abs(m - self.note)
                heading = p != self.note and away - abs(m - p) > 0.05   # the voice is moving toward another note
                # choke: silence the old note only while the voice is clearly on its way to a DIFFERENT note,
                # and never for long: after ~40 ms the new note simply plays
                if heading and away > 0.6 + 0.4 * s:
                    if self.head_t is None:
                        self.head_t = self.t
                    if not self.choked and self.t - self.head_t >= 0.008 + 0.012 * s:  # sure it's a move, not a wobble
                        self.choked, self.choke_t = True, self.t
                        ev.append(("choke",))
                elif self.choked or self.head_t is not None:
                    self.head_t = None
                if not (heading and away > 0.6 + 0.4 * s) and self.choked:
                    self.choked = False
                    ev.append(("unchoke",))
                held = self.t - self.on_t
                if p != self.note:
                    margin = away - abs(m - p)
                    need = 0.12 + 0.45 * s
                    force = self.choked and self.t - self.choke_t > 0.04
                    if margin > need or force:
                        if self.cand and self.cand[0] == p:
                            if force or (steady and self.t - self.cand[1] >= 0.036 * s and held >= 0.03 + 0.05 * s):
                                ev.append(("on", p, self.vel(rms)))
                                self.note, self.cand, self.peak, self.dipped, self.choked, self.on_t = p, None, rms, False, False, self.t
                        else:
                            self.cand = (p, self.t)
                    else:
                        self.cand = None
                else:
                    self.cand = None
        else:
            self.midi = float("nan")
            self.cand = None
            self.W = int(self.sr * 0.014)
            self.recent = []
            if self.note is not None:
                self.quiet += dt
                if self.quiet > 0.02 + 0.08 * s:
                    ev.append(("off",))
                    self.note, self.choked = None, False
        return ev

    @staticmethod
    def vel(rms):
        db = 20 * math.log10(max(rms, 1e-6))
        return min(1.0, max(0.2, (db + 50) / 38))


class Synth:
    """One voice at a time (like singing). Band-limited oscillators + a low-pass filter per block."""

    def __init__(self, sr):
        self.sr = sr
        self.snd = "pluck"
        self.vol = 0.8
        self.f = 220.0
        self.ph = 0.0
        self.amp = 0.0
        self.age = 9.0
        self.gate = False
        self.v = 0.8
        self.zi = np.zeros(2)
        self.tone = 0.5
        self.vowel = True
        self.choke = False

    def on(self, note, v):
        self.f = 440.0 * 2 ** ((note - 69) / 12)
        self.v, self.gate, self.age, self.choke = v, True, 0.0, False

    def off(self):
        self.gate = False

    def render(self, n):
        sr, f, snd = self.sr, self.f, self.snd
        t = self.age + np.arange(n) / sr
        # amplitude envelope
        if self.gate and self.choke:
            a = self.amp * np.exp(-np.arange(1, n + 1) / (0.003 * sr))
        elif self.gate:
            if snd == "pluck":
                env = 0.25 + 0.75 * np.exp(-t / 0.35)
                att = 0.002
            elif snd == "keys":
                env = 0.35 + 0.65 * np.exp(-t / 0.6)
                att = 0.003
            elif snd == "bass":
                env = 0.55 + 0.45 * np.exp(-t / 0.4)
                att = 0.003
            elif snd == "pad":
                env = np.ones(n)
                att = 0.06
            else:
                env = np.ones(n)
                att = 0.004
            env = env * np.minimum(1.0, t / att)
            target = env * self.v
            # glide from the current level so a note change never clicks
            k = np.minimum(1.0, np.arange(1, n + 1) / (0.002 * sr))
            a = self.amp + (target - self.amp) * k
        else:
            rel = 0.12 if snd in ("pluck", "keys") else 0.05 if snd != "pad" else 0.25
            a = self.amp * np.exp(-np.arange(1, n + 1) / (rel * sr))
        self.amp = float(a[-1])
        self.age += n / sr
        if self.amp < 1e-4 and not self.gate:
            self.zi[:] = 0
            return np.zeros(n, np.float32)
        # oscillator
        inc = 2 * np.pi * f / sr
        ph = self.ph + inc * np.arange(1, n + 1)
        self.ph = float(ph[-1] % (2 * np.pi))
        K = max(1, min(30, int(0.45 * sr / f)))
        ks = np.arange(1, K + 1)[:, None]
        if snd == "keys":
            w = np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)
        elif snd == "pad":
            w = (np.sin(ks * ph) / ks).sum(0) * 0.6 + 0.4 * np.sin(ph * 1.003)
        elif snd == "lead":
            sq = (np.sin(ks[::2] * ph) / ks[::2]).sum(0)
            w = 0.6 * (np.sin(ks * ph) / ks).sum(0) + 0.6 * sq
        else:  # pluck, bass: saw
            w = (np.sin(ks * ph) / ks).sum(0)
        # tone: brighter for "ee", darker for "oo" (if vowel control is on); plucks also close over time
        base = self.tone if self.vowel else 0.55
        lo, hi = {"bass": (2.0, 10.0), "pad": (2.5, 14.0)}.get(snd, (3.0, 30.0))
        mult = lo * (hi / lo) ** base
        if snd == "pluck":
            mult *= 1 + 3.0 * math.exp(-self.age / 0.08)
        fc = min(0.45 * sr, max(80.0, f * mult))
        wc = math.tan(math.pi * fc / sr)
        q = 0.9
        k0 = 1 / (1 + wc / q + wc * wc)
        b = np.array([wc * wc * k0, 2 * wc * wc * k0, wc * wc * k0])
        aa = np.array([1.0, 2 * (wc * wc - 1) * k0, (1 - wc / q + wc * wc) * k0])
        y, self.zi = lfilter(b, aa, w, zi=self.zi)
        out = np.tanh(1.2 * self.vol * 0.35 * a * y)
        return out.astype(np.float32)


class LiveEngine:
    def __init__(self):
        self.ok = OK
        self.stream, self.mode = None, ""
        self.params = {"stick": 0.5, "snd": "pluck", "vel": True, "vowel": True, "vol": 0.8, "allowed": list(range(12))}
        self.A = self.S = None
        self.lock = threading.Lock()
        self.last = {"note": None, "midi": None, "t": 0}
        self.log = []          # (time, event) for the tests
        self.xruns = 0
        self.dec = 1
        self.fake = None

    def set(self, **p):
        self.params.update({k: v for k, v in p.items() if v is not None})
        self._apply()
        return self.status()

    def _apply(self):
        P = self.params
        if self.A:
            self.A.stick = float(P["stick"])
            self.A.allowed = set(int(x) % 12 for x in P["allowed"]) or set(range(12))
        if self.S:
            self.S.snd = P["snd"] if P["snd"] in SOUNDS else "pluck"
            self.S.vol = float(P["vol"])
            self.S.vowel = bool(P["vowel"])

    def _cb(self, indata, outdata, frames, t, status):
        x = indata.sum(axis=1).astype(np.float32)
        if self.fake is not None:  # tests only: a synthetic voice instead of the mic
            x = self.fake(len(x))
        if self.dec == 2:  # 88.2/96 kHz: analyse at half the rate (plenty for a voice, half the work)
            x = 0.5 * (x[0::2] + x[1::2])
        if status:
            self.xruns += 1
        for e in self.A.feed(x):
            if e[0] == "on":
                self.S.on(e[1], e[2] if self.params["vel"] else 0.8)
                self.last["note"] = e[1]
            elif e[0] == "choke":
                self.S.choke = True
            elif e[0] == "unchoke":
                self.S.choke = False
            else:
                self.S.off()
                self.last["note"] = None
        self.S.tone = self.A.tone
        m = self.A.midi
        self.last["midi"] = None if m != m else round(m, 2)
        outdata[:] = self.S.render(frames)[:, None]

    # The sound card is opened and closed on one dedicated thread prepared for Windows audio drivers (COM):
    # ASIO drivers refuse to load from the web helper's request threads.
    def _worker(self):
        import ctypes, queue
        try:
            ctypes.windll.ole32.CoInitialize(None)
        except Exception:
            pass
        while True:
            fn, box, done = self._q.get()
            try:
                box["r"] = fn()
            except Exception as e:  # never let the audio thread die
                box["r"] = self.status(); self.error = repr(e)
            done.set()

    def _run(self, fn):
        import queue
        with self.lock:
            if not getattr(self, "_q", None):
                self._q = queue.Queue()
                threading.Thread(target=self._worker, daemon=True, name="humnote-audio").start()
        box, done = {}, threading.Event()
        self._q.put((fn, box, done))
        done.wait(15)
        return box.get("r", self.status())

    def start(self):
        return self._run(self._start)

    def stop(self):
        return self._run(self._stop)

    def _start(self):
        if self.stream or not self.ok:
            return self.status()
        apis = sd.query_hostapis()
        win_sr = None
        for h in apis:
            if "WASAPI" in h["name"] and h["default_input_device"] >= 0:
                win_sr = int(sd.query_devices(h["default_input_device"])["default_samplerate"])
        tries = []
        for h in apis:   # the interface's ASIO driver: ~4 ms in + 4 ms out. Always at Windows' own sample rate:
            if h["name"] == "ASIO":  # another rate would switch the interface and cut off every other app's mic
                for d in h["devices"]:
                    dd = sd.query_devices(d)
                    if dd["max_input_channels"] > 0 and dd["max_output_channels"] > 0:
                        tries.append((d, d, "ASIO", win_sr or int(dd["default_samplerate"]), 32, 0.001))
        # fallback: Windows' shared path. (Not WDM-KS: it takes the mic for itself, so Humnote's window couldn't record.)
        for h in apis:
            if "WASAPI" in h["name"] and h["default_input_device"] >= 0 and h["default_output_device"] >= 0:
                tries.append((h["default_input_device"], h["default_output_device"], "shared", None, 0, 0.003))
        self.error = ""
        for di, do, label, sr0, bs, lat in tries:
            try:
                ind, outd = sd.query_devices(di), sd.query_devices(do)
                sr = sr0 or int(outd["default_samplerate"])
                self.dec = 2 if sr >= 88200 else 1
                if label == "ASIO" and self.dec == 2:
                    bs = 64
                self.A, self.S = Analyzer(sr // self.dec), Synth(sr)
                self._apply()
                self.xruns = 0
                s = sd.Stream(device=(di, do), samplerate=sr,
                              channels=(min(2, ind["max_input_channels"]), min(2, outd["max_output_channels"])),
                              dtype="float32", latency=lat, blocksize=bs, callback=self._cb)
                s.start()
                self.stream, self.mode = s, label
                self.inname = ind["name"]
                break
            except Exception as e:
                self.error = f"{label}: {e}"
                continue
        return self.status()

    def _stop(self):
        if self.stream:
            try:
                self.stream.stop(); self.stream.close()
            except Exception:
                pass
        self.stream = None
        return self.status()

    def status(self):
        d = round(sum(self.stream.latency) * 1000) if self.stream else None
        return {"available": self.ok, "on": bool(self.stream), "delay_ms": d, "mode": self.mode if self.stream else "", "xruns": self.xruns,
                "input": getattr(self, "inname", "") if self.stream else "", "level": round(float(self.A.rms), 4) if (self.stream and self.A) else 0, "error": getattr(self, "error", ""),
                "note": self.last["note"], "midi": self.last["midi"], **{k: self.params[k] for k in ("stick", "snd", "vel", "vowel", "vol")}}


LIVE = LiveEngine()
