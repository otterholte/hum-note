"""Two test sets from the Children's Song Dataset (one pro singer, exact note + syllable timings; CC BY-NC-SA 4.0, local only).
  csd  = odd-numbered English songs (to tune on)    csdx = even-numbered (held back)
Each clip: 20 s from the first note. usage: python make_csd.py"""
import os, io, json, csv
import numpy as np, soundfile as sf
from remotezip import RemoteZip
HERE = os.path.dirname(os.path.abspath(__file__)); L = 20.0
z = RemoteZip("https://zenodo.org/records/4916302/files/CSD.zip?download=1")
for setname, par in (("csd", 1), ("csdx", 0)):
    out = os.path.join(HERE, setname); os.makedirs(out, exist_ok=True); idx = {}
    for k in range(1, 51):
        if k % 2 != par: continue
        sid = f"en{k:03d}a"; rows = list(csv.DictReader(io.StringIO(z.read(f"CSD/english/csv/{sid}.csv").decode())))
        t0 = max(0.0, float(rows[0]["start"]) - 0.3); notes = [r for r in rows if float(r["start"]) >= t0 and float(r["start"]) < t0 + L - 0.2]
        dst = os.path.join(out, sid + ".wav")
        if not os.path.exists(dst):
            y, sr = sf.read(io.BytesIO(z.read(f"CSD/english/wav/{sid}.wav")), dtype="float32")
            if y.ndim > 1: y = y.mean(1)
            y = y[int(t0 * sr):int((t0 + L) * sr)]; sf.write(dst, y / (np.abs(y).max() + 1e-9) * 0.7, sr, subtype="PCM_16")
        idx[sid] = dict(kind="sung", ref=[int(r["pitch"]) for r in notes], times=[[round(float(r["start"]) - t0, 3), round(min(L, float(r["end"]) - t0), 3)] for r in notes],
                        syl=[r["syllable"] for r in notes], source="CSD (CC BY-NC-SA 4.0)")
        print(sid, len(notes), flush=True)
    json.dump(idx, open(os.path.join(out, "index.json"), "w"), indent=0)
