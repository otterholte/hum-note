"""Renders note lists with Humnote's upright piano (same recipe as pianoVoice in index.html) to MP3.
python render_piano.py notes.json out_dir   (json: lists of [midi, start_s, end_s, velocity])"""
import json, os, sys, subprocess, numpy as np, imageio_ffmpeg
from scipy.signal import butter, sosfilt

FF = imageio_ffmpeg.get_ffmpeg_exe(); HERE = os.path.dirname(os.path.abspath(__file__)); PIANO = os.path.join(HERE, "..", "..", "piano"); SR = 48000
KEYS = list(range(31, 100, 2))

def load(path):
    raw = subprocess.run([FF, "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2)

BUF = {(v, k): load(os.path.join(PIANO, f"k{v}_{k}.ogg")) for v in (1, 2) for k in KEYS}

def key_detune(p):
    x = np.sin(p * 12.9898) * 43758.5453
    return ((x - np.floor(x)) - 0.5) * 7

def voice(p, vel, dur):
    k = min(KEYS, key=lambda q: abs(q - p)); x = min(1, max(0, (vel - 45) / 60)); rate = 2 ** ((p - k + key_detune(p) / 100) / 12)
    lvl = 0.55 * (0.35 + 0.65 * vel / 127); out = None
    for v, w in ((1, 1 - x), (2, x)):
        if w < 0.02: continue
        for dc, g0 in ((0, 1), (2.2, 0.28)):
            b = BUF[(v, k)]; r = rate * 2 ** (dc / 1200); n = int(len(b) / r); t = np.arange(n) * r
            y = np.stack([np.interp(t, np.arange(len(b)), b[:, c]) for c in (0, 1)], 1) * (lvl * w * g0)
            out = y if out is None else (np.pad(out, ((0, max(0, len(y) - len(out))), (0, 0)))[:max(len(out), len(y))] + np.pad(y, ((0, max(0, len(out) - len(y))), (0, 0))))
    sos = butter(2, min(20000, 1800 + 3800 * x), "low", fs=SR, output="sos"); out = sosfilt(sos, out, axis=0)
    rel = int(dur * SR)  # damper: exponential release (tau 0.11 s) from the note's end
    if rel < len(out):
        env = np.ones(len(out)); env[rel:] = np.exp(-np.arange(len(out) - rel) / (0.11 * SR)); out = out * env[:, None]; out = out[:rel + int(0.8 * SR)]
    return out

def render(notes, path):
    end = max(e for _, s, e, _ in notes) + 2.5; mix = np.zeros((int(end * SR), 2))
    for p, s, e, v in notes:
        y = voice(p, v, e - s); a = int(s * SR); b = min(len(mix), a + len(y)); mix[a:b] += y[:b - a]
    mix *= 0.8 / max(1e-6, np.abs(mix).max())
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-b:a", "192k", path], input=mix.astype(np.float32).tobytes(), check=True)

if __name__ == "__main__":
    d = json.load(open(sys.argv[1])); od = sys.argv[2]; os.makedirs(od, exist_ok=True)
    t0 = min(s for _, s, _, _ in d["midi"]) - 0.2; midi = [[p, s - t0, e - t0, v] for p, s, e, v in d["midi"]]
    for name, notes in (("1 - transcribed MIDI (as sung, piano)", midi), ("2 - cleaned up (piano)", d["clean"]), ("3 - cleaned up with chords (piano)", d["withCh"])):
        out = os.path.join(od, f"Humnote 01-58-26 - {name}.mp3"); render(notes, out); print("wrote", out)
