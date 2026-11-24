"""How much does SwiftF0 lose when a live tuner reads a frame before its full 10-frame (160 ms) lookahead exists?
For lookahead L, every frame i is computed from audio ending L frames after it (11 frames of left context).
usage: python swift_latency.py  -> swift_latency.json
"""
import lowprio  # noqa: F401
import json, os
import numpy as np
from models import load_audio, MODELS, _cache
from eval_synth import truth, metrics

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS["swiftf0"](np.zeros(16000, np.float32), "cpu")
sw = [v for k, v in _cache.items() if k[0] == "swift"][0]
HOP = 256
res = {}
for L in (0, 1, 2, 4, 10):
    pairs = []
    for name in ("mid_vowels", "hum_mid", "fast_runs", "quiet", "breathy", "low_ambiguous"):
        x = load_audio(os.path.join(HERE, "synth", name + ".wav"))
        n = len(x) // HOP
        P = np.zeros(n); C = np.zeros(n)
        for i in range(n):
            a = max(0, i - 11); b = min(len(x), (i + 1 + L) * HOP)
            p, c, _ = sw._run(x[a * HOP:b], 46.875, 2093.75)
            P[i], C[i] = p[i - a], c[i - a]
        tr = truth(name)
        t = np.arange(n) * HOP / 16000
        from eval_synth import sample
        s = sample(dict(t=t, f0=P, voiced=C >= 0.5, conf=C), tr["t"])
        pairs.append((tr, s))
    m = metrics(pairs)
    res[L] = dict(lookahead_ms=L * 16, vx_correct=m["vx_correct"], rpa50=m["rpa50"], octave=m["octave"], v_recall=m["v_recall"],
                  false_voiced=m["false_voiced_in_silence"], jitter=m["jitter_cents"])
    print(L, {k: round(v, 4) for k, v in res[L].items()}, flush=True)
json.dump(res, open(os.path.join(HERE, "swift_latency.json"), "w"), indent=1)
