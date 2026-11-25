"""Humnote live notes: mic -> pitch -> synth, all inside this program (no browser in the sound path).

Sound goes in and out through Windows' direct audio path (WDM-KS, a few ms each way on a USB interface), falling
back to WASAPI. Every audio block (~3 ms):
  1. pitch: YIN on the newest ~21 ms of the mic (fast and simple; the careful AI transcription still runs on the take)
  2. note: snapped to the chosen key's notes (or any semitone), with "stickiness": once a note plays it is held until
     the voice clearly moves to another note for a moment, so wobbles, scoops and vibrato don't flip it
  3. synth: a small built-in synth plays the note; how loud you start sets the velocity, and the vowel you sing
     (oo / ah / ee) opens or closes the tone filter. Your voice itself is never played back.
"""
import math, threading, time

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
        self.W = int(sr * 0.021)                      # analysis window (~21 ms)
        self.tmin, self.tmax = int(sr / 1100), int(sr / 65)
        self.buf = np.zeros(self.W + self.tmax + 8, np.float32)
        n = self.W + self.tmax
        self.N = 1 << (2 * n - 1).bit_length()
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
        F = np.fft.rfft(x, self.N)
        r = np.fft.irfft(np.conj(np.fft.rfft(a, self.N)) * F, self.N)[: tmax + 1]
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
        dt = n / self.sr
        self.t += dt
        w = self.buf[-(self.W + self.tmax):][::-1].copy()  # newest samples first, so the reading reflects the latest ~21 ms
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
            # octave slip guard: a sudden exact-octave jump from the note being held is almost always the tracker
            if self.note is not None:
                k = round((m - self.note) / 12)
                if k and abs(m - 12 * k - self.note) < 0.8:
                    m -= 12 * k
            self.midi = m
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
                    if self.t - self.cand[1] >= 0.004:
                        ev.append(("on", p, self.vel(rms)))
                        self.note, self.cand, self.peak, self.dipped = p, None, rms, False
                else:
                    self.cand = (p, self.t)
            else:
                self.peak = max(self.peak, rms)
                # the same note sung again (a new syllable): the voice dips, then comes back up
                if rms < 0.35 * self.peak:
                    self.dipped = True
                elif self.dipped and rms > 0.6 * self.peak:
                    self.dipped = False
                    self.peak = rms
                    ev.append(("on", self.note, self.vel(rms)))
                if p != self.note:
                    margin = abs(m - self.note) - abs(m - p)
                    need = 0.1 + 0.5 * s
                    if margin > need:
                        if self.cand and self.cand[0] == p:
                            if self.t - self.cand[1] >= 0.003 + 0.03 * s:
                                ev.append(("on", p, self.vel(rms)))
                                self.note, self.cand, self.peak, self.dipped = p, None, rms, False
                        else:
                            self.cand = (p, self.t)
                    else:
                        self.cand = None
                else:
                    self.cand = None
        else:
            self.midi = float("nan")
            self.cand = None
            if self.note is not None:
                self.quiet += dt
                if self.quiet > 0.03 + 0.09 * s:
                    ev.append(("off",))
                    self.note = None
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

    def on(self, note, v):
        self.f = 440.0 * 2 ** ((note - 69) / 12)
        self.v, self.gate, self.age = v, True, 0.0

    def off(self):
        self.gate = False

    def render(self, n):
        sr, f, snd = self.sr, self.f, self.snd
        t = self.age + np.arange(n) / sr
        # amplitude envelope
        if self.gate:
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
        for e in self.A.feed(x):
            if e[0] == "on":
                self.S.on(e[1], e[2] if self.params["vel"] else 0.8)
                self.last["note"] = e[1]
            else:
                self.S.off()
                self.last["note"] = None
        self.S.tone = self.A.tone
        m = self.A.midi
        self.last["midi"] = None if m != m else round(m, 2)
        outdata[:] = self.S.render(frames)[:, None]

    def start(self):
        if self.stream or not self.ok:
            return self.status()
        apis = sd.query_hostapis()
        tries = []
        for word, label in (("WDM-KS", "direct"), ("WASAPI", "shared")):
            for h in apis:
                if word in h["name"] and h["default_input_device"] >= 0 and h["default_output_device"] >= 0:
                    tries.append((h["default_input_device"], h["default_output_device"], label))
        for di, do, label in tries:
            try:
                ind, outd = sd.query_devices(di), sd.query_devices(do)
                sr = int(outd["default_samplerate"])
                self.A, self.S = Analyzer(sr), Synth(sr)
                self._apply()
                s = sd.Stream(device=(di, do), samplerate=sr,
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
        return {"available": self.ok, "on": bool(self.stream), "delay_ms": d, "mode": self.mode if self.stream else "",
                "note": self.last["note"], "midi": self.last["midi"], **{k: self.params[k] for k in ("stick", "snd", "vel", "vowel", "vol")}}


LIVE = LiveEngine()
