"""Run every neural model on a set of WAVs.
usage: python run_models.py out_dir [--device cuda|cpu] [--models a,b] file1.wav ...
Writes out_dir/<model>/<name>.npz (t, f0, conf, voiced).
"""
import lowprio  # noqa: F401
import argparse, os, time
import numpy as np
import torch
from models import MODELS, load_audio

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("files", nargs="+")
ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
ap.add_argument("--models", default=",".join(MODELS))
a = ap.parse_args()
for m in a.models.split(","):
    os.makedirs(os.path.join(a.out, m), exist_ok=True)
    tot = 0; dur = 0
    for f in a.files:
        x = load_audio(f)
        t0 = time.perf_counter()
        r = MODELS[m](x, a.device)
        tot += time.perf_counter() - t0; dur += len(x) / 16000
        conf = r["conf"] if r["conf"] is not None else np.full(len(r["f0"]), np.nan)
        np.savez(os.path.join(a.out, m, os.path.splitext(os.path.basename(f))[0] + ".npz"),
                 t=r["t"], f0=r["f0"], conf=conf, voiced=r["voiced"])
    print(f"{m:12s} {1000 * tot / dur:8.1f} ms per s of audio on {a.device} (incl. first-call load)")
