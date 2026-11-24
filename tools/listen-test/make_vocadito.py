"""vocadito test sets (40 solo singers, 7 languages, two independent note annotations; CC BY 4.0, local only).
  voc = odd-numbered clips (tune on)   vocx = even (held back). Reference = annotator 1; also prints how often the
  two human annotators agree (the realistic ceiling). usage: python make_vocadito.py"""
import os, json, csv, math, shutil
import numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, "vocadito_src")
def notes(f): return [(float(r[0]), float(r[0]) + float(r[2]), int(round(69 + 12 * math.log2(float(r[1]) / 440)))) for r in csv.reader(open(f)) if r]
def ed(a, b):
    D = np.zeros((len(a) + 1, len(b) + 1), int); D[:, 0] = range(len(a) + 1); D[0, :] = range(len(b) + 1)
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1): D[i, j] = min(D[i - 1, j] + 1, D[i, j - 1] + 1, D[i - 1, j - 1] + (a[i - 1] != b[j - 1]))
    return D[-1, -1]
agree = []
for setname, par in (("voc", 1), ("vocx", 0)):
    out = os.path.join(HERE, setname); os.makedirs(out, exist_ok=True); idx = {}
    for k in range(1, 41):
        if k % 2 != par: continue
        a1 = notes(os.path.join(V, "Annotations", "Notes", f"vocadito_{k}_notesA1.csv")); a2 = notes(os.path.join(V, "Annotations", "Notes", f"vocadito_{k}_notesA2.csv"))
        y, sr = sf.read(os.path.join(V, "Audio", f"vocadito_{k}.wav"), dtype="float32")
        if y.ndim > 1: y = y.mean(1)
        sf.write(os.path.join(out, f"vocadito_{k}.wav"), y / (np.abs(y).max() + 1e-9) * 0.7, sr, subtype="PCM_16")
        r1 = [n[2] for n in a1]; r2 = [n[2] for n in a2]; agree.append(max(0, 1 - ed(r2, r1) / len(r1)))
        idx[f"vocadito_{k}"] = dict(kind="sung", ref=r1, times=[[round(a, 3), round(b, 3)] for a, b, _ in a1], ref2=r2, source="vocadito (CC BY 4.0)")
    json.dump(idx, open(os.path.join(out, "index.json"), "w"), indent=0); print(setname, len(idx))
print(f"human annotators agree on {100*np.mean(agree):.1f}% of notes (annotator 2 scored against annotator 1)")
