"""SwiftF0 pitch tracks for every clip in a set (for the benchmark; the app runs the same model in the browser).
usage: python swift_tracks.py <set dir>  -> <set>_swift/<name>.json {t, f0, conf}"""
import os, sys, json, glob
HERE = os.path.dirname(os.path.abspath(__file__)); PC = os.path.join(HERE, "..", "pitch-compare"); sys.path.insert(0, PC)
sys.path.insert(0, os.path.join(PC, "pylib"))
import lowprio  # idle priority, one thread
import numpy as np, soundfile as sf, soxr
from swift_f0 import SwiftF0
SR = 16000; DET = SwiftF0(threads=1, spin=False)
def load_audio(path):
    x, sr = sf.read(path, dtype="float32", always_2d=True); x = x.mean(axis=1)
    if sr != SR: x = soxr.resample(x, sr, SR).astype(np.float32)
    return x * (0.9 / (np.abs(x).max() + 1e-9))
def swift(x):
    r = DET.detect(x, SR, fmin=46.875, fmax=2093.75); return dict(t=np.asarray(r.timestamps), f0=np.asarray(r.pitch_hz, float), conf=np.asarray(r.confidence, float))
s = sys.argv[1]; out = os.path.join(HERE, s + "_swift"); os.makedirs(out, exist_ok=True)
for f in sorted(glob.glob(os.path.join(HERE, s, "*.wav"))):
    x = load_audio(f); r = swift(x)
    json.dump(dict(t=[round(float(v), 4) for v in r["t"]], f0=[round(float(v), 2) for v in r["f0"]], conf=[round(float(v), 3) for v in r["conf"]]),
              open(os.path.join(out, os.path.basename(f)[:-4] + ".json"), "w"))
print("done", len(os.listdir(out)))
