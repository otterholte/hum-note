"""Speed: ms per second of audio, CPU single thread (idle priority), plus warm GPU; and live-tuner style
per-update latency (one inference on the shortest window that yields a current frame).
usage: python speed.py   -> speed.json
"""
import lowprio  # noqa: F401
import json, os, time
import numpy as np
import torch
from models import MODELS, load_audio, _cache

HERE = os.path.dirname(os.path.abspath(__file__))
x = load_audio(os.path.join(HERE, "synth", "mid_vowels.wav"))[: 16000 * 5]
dur = len(x) / 16000


def bench(fn, reps=3):
    fn()  # warm-up / load
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter(); fn(); ts.append(time.perf_counter() - t0)
    return min(ts)


res = {}
for m, run in MODELS.items():
    r = {}
    r["cpu_ms_per_s"] = 1000 * bench(lambda: run(x, "cpu"), reps=2 if m == "crepe_full" else 3) / dur
    if torch.cuda.is_available() and m != "swiftf0":
        r["gpu_ms_per_s"] = 1000 * bench(lambda: run(x, "cuda")) / dur
    res[m] = r
    print(m, {k: round(v, 1) for k, v in r.items()}, flush=True)

# live-tuner style: one update = shortest audio chunk that produces an up-to-date frame
import torchcrepe
for size in ("tiny", "full"):
    fr = torch.from_numpy(x[:1024].copy())[None]
    def one():
        with torch.inference_mode():
            torchcrepe.predict(fr, 16000, hop_length=1024, fmin=50, fmax=1100, model=size, pad=False,
                               decoder=torchcrepe.decode.weighted_argmax, device="cpu", batch_size=1)
    res[f"crepe_{size}"]["cpu_ms_per_update"] = 1000 * bench(one, 10)
sw = [v for k, v in _cache.items() if k[0] == "swift"][0]
win = x[: 256 * 22]   # 11 frames of left context + 10 lookahead, as swift_f0's streaming code needs
res["swiftf0"]["cpu_ms_per_update"] = 1000 * bench(lambda: sw.detect(win, 16000), 20)
pm = [v for k, v in _cache.items() if k[0] == "pesto" and k[2] == "cpu"][0]
import pesto
wp = torch.from_numpy(x[: 16000 // 4].copy())
def pone():
    with torch.inference_mode():
        pesto.core._predict(wp, 16000, pm, num_chunks=1, convert_to_freq=True)
res["pesto"]["cpu_ms_per_update"] = 1000 * bench(pone, 10)
json.dump(res, open(os.path.join(HERE, "speed.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
