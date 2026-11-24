"""Learns when one held pitch is really two notes (a new syllable) from sets with exact note timings.
Every candidate split point inside a steady pitch stretch gets measurements; the answer key says whether a real
note boundary is there. A small decision tree is fitted and printed as rules to hand-code into the app.
usage: python learn_splits.py train_set[,set2] test_set"""
import sys, os, json, numpy as np
from sklearn.tree import DecisionTreeClassifier, export_text
HERE = os.path.dirname(os.path.abspath(__file__))
NAMES = ["gap", "dip", "nv", "vib", "rise", "fall", "lvl", "dpitch", "nvdip"]
def feats(set_):
    idx = json.load(open(os.path.join(HERE, set_, "index.json"))); X = []; Y = []
    for name, c in idx.items():
        f = os.path.join(HERE, "out_" + set_, name + ".json")
        if not os.path.exists(f) or "times" not in c: continue
        J = json.load(open(f)); t0, dt = J["t0"], J["dt"]; m = np.array([v if v is not None else np.nan for v in J["m"]]); ds = np.array(J["ds"], float)
        nv = np.array(J["nv"], float); vib = np.array(J["vib"], float); vo = np.array(J["voiced"], float); n = len(m); peak = np.nanpercentile(ds, 97)
        fr = lambda t: int(round((t - t0) / dt))
        # true same-pitch boundaries (end of one note -> start of the next, same pitch, < 0.25 s apart)
        R = c["ref"]; T = c["times"]; bounds = []; inside = []
        for k in range(len(R)):
            inside.append((fr(T[k][0]) + 8, fr(T[k][1]) - 8))
            if k and R[k] == R[k - 1] and T[k][0] - T[k - 1][1] < 0.25: bounds.append((fr(T[k - 1][1]), fr(T[k][0])))
        cand = set()
        for i in range(12, n - 12):
            w = ds[i - 3:i + 4]
            if ds[i] == w.min() and (max(ds[i - 12:i - 2].max(), ds[i + 3:i + 13].max()) - ds[i] > 1.0): cand.add(i)
            if nv[i] == nv[i - 5:i + 6].max() and nv[i] > 2: cand.add(i)
            if not vo[i] and vo[i - 1]: cand.add(i)
        for i in sorted(cand):
            a = m[max(0, i - 18):i - 3]; b = m[i + 3:i + 18]; a = a[~np.isnan(a) & (vo[max(0, i - 18):i - 3] > 0)]; b = b[~np.isnan(b) & (vo[i + 3:i + 18] > 0)]
            if len(a) < 5 or len(b) < 5: continue
            dp = abs(np.median(a) - np.median(b))
            if dp > 0.6: continue                       # a pitch change: the decoder handles those
            pos = any(lo - 6 <= i <= hi + 6 for lo, hi in bounds); neg = any(lo <= i <= hi for lo, hi in inside) and not pos
            if not pos and not neg: continue
            g = 0; j = i
            while j < n and not vo[j]: g += 1; j += 1
            L = ds[i - 12:i - 2].max(); Rr = ds[i + 3:i + 13].max(); lo = ds[i - 3:i + 4].min()
            X.append([g, min(L, Rr) - lo, nv[i - 3:i + 4].max(), vib[i - 10:i + 10].mean(), Rr - lo, L - lo, max(L, Rr) - peak, dp, nv[i - 3:i + 4].max() * (min(L, Rr) - lo)]); Y.append(int(pos))
    return np.array(X), np.array(Y)
tr = sys.argv[1].split(","); te = sys.argv[2].split(",")
Xs, Ys = zip(*[feats(s) for s in tr]); X = np.vstack(Xs); Y = np.concatenate(Ys)
Xt, Yt = zip(*[feats(s) for s in te]); Xt = np.vstack(Xt); Yt = np.concatenate(Yt)
print(f"train {len(Y)} candidates ({Y.sum()} real boundaries) | test {len(Yt)} ({Yt.sum()})")
for d in (2, 3, 4):
    t = DecisionTreeClassifier(max_depth=d, min_samples_leaf=15, class_weight="balanced", random_state=0).fit(X, Y); p = t.predict(Xt)
    tp = ((p == 1) & (Yt == 1)).sum(); fp = ((p == 1) & (Yt == 0)).sum(); fn = ((p == 0) & (Yt == 1)).sum()
    print(f"depth {d}: test precision {tp/(tp+fp+1e-9):.2f} recall {tp/(tp+fn+1e-9):.2f}  F {2*tp/(2*tp+fp+fn):.2f}")
    if d == 3: print(export_text(t, feature_names=NAMES, decimals=2))
