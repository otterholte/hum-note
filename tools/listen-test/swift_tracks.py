"""SwiftF0 pitch tracks for every clip in a set (for the benchmark; the app runs the same model in the browser).
usage: python swift_tracks.py <set dir>  -> <set>_swift/<name>.json {t, f0, conf}"""
import os, sys, json, glob
HERE = os.path.dirname(os.path.abspath(__file__)); PC = os.path.join(HERE, "..", "pitch-compare"); sys.path.insert(0, PC)
import lowprio  # idle priority, one thread
from models import MODELS, load_audio
s = sys.argv[1]; out = os.path.join(HERE, s + "_swift"); os.makedirs(out, exist_ok=True)
for f in sorted(glob.glob(os.path.join(HERE, s, "*.wav"))):
    x = load_audio(f); r = MODELS["swiftf0"](x, "cpu")
    json.dump(dict(t=[round(float(v), 4) for v in r["t"]], f0=[round(float(v), 2) for v in r["f0"]], conf=[round(float(v), 3) for v in r["conf"]]),
              open(os.path.join(out, os.path.basename(f)[:-4] + ".json"), "w"))
print("done", len(os.listdir(out)))
