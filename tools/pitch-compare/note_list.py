import json, sys, numpy as np
t, m = np.load(sys.argv[1]); notes = json.load(open(sys.argv[2]))["notes"]
N = ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B']; nm = lambda p: N[int(round(p)) % 12] + str(int(round(p)) // 12 - 1)
rows = []
for n in notes:
    sel = (t >= n["start"]) & (t < n["end"]) & ~np.isnan(m)
    if sel.sum() < 3: rows.append((n, None)); continue
    rows.append((n, np.median(m[sel])))
g = np.median([md - n["pitch"] for n, md in rows if md is not None])
for n, md in rows:
    if md is None: print(f"{n['start']:6.2f}s  {nm(n['pitch']):<4} (no clear pitch)"); continue
    d = md - n["pitch"] - g; flag = "  <-- off" if abs(d) > 0.5 else ""
    print(f"{n['start']:6.2f}s  {(n['end']-n['start']):.2f}s  note {nm(n['pitch']):<4}  you sang {nm(md - g):<4} ({100*d:+4.0f}c){flag}")
