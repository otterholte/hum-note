"""Trains a small note-onset detector from frame measurements (pitch, voicing, level, sound colour, vibrato) on sets
with exact note starts, and reports how well it finds onsets on held-back sets. usage: python learn_onsets.py train test"""
import sys, os, json, numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
HERE = os.path.dirname(os.path.abspath(__file__)); OFF = [-12, -8, -5, -3, -2, -1, 0, 1, 2, 3, 5, 8, 12]
def clip_feats(J):
    m = np.array([v if v is not None else np.nan for v in J["m"]], float); vo = np.array(J["voiced"], float); ds = np.array(J["ds"], float)
    nv = np.array(J["nv"], float); vib = np.array(J["vib"], float); n = len(m); peak = np.nanpercentile(ds, 97)
    mm = np.where(vo > 0, m, np.nan); base = []
    for o in OFF:
        sh = lambda a: np.roll(a, -o)
        base += [sh(vo), sh(ds) - peak, sh(nv), sh(vib)]
    # pitch change across the frame (median of 8 frames after minus before), and level rise
    def med(a, lo, hi):
        out = np.full(n, np.nan)
        for i in range(n):
            w = a[max(0, i + lo):max(0, i + hi)]; w = w[~np.isnan(w)]
            if len(w) >= 3: out[i] = np.median(w)
        return out
    dp = np.abs(med(mm, 1, 9) - med(mm, -8, 0)); dp = np.nan_to_num(dp, nan=0.0)
    rise = np.array([ds[i:i + 10].max() - ds[max(0, i - 4):i + 2].min() if i + 2 <= n else 0 for i in range(n)])
    fall = np.array([ds[max(0, i - 12):i].max() - ds[max(0, i - 4):i + 2].min() if i > 0 else 0 for i in range(n)])
    X = np.stack(base + [dp, np.minimum(dp, 3), rise, fall], 1); return np.nan_to_num(X, nan=0.0)
def load(sets, step=1):
    Xs, Ys = [], []
    for s in sets.split(","):
        idx = json.load(open(os.path.join(HERE, s, "index.json")))
        for k, c in idx.items():
            f = os.path.join(HERE, "out_" + s, k + ".json")
            if not os.path.exists(f): continue
            J = json.load(open(f)); X = clip_feats(J); n = len(X); y = np.zeros(n)
            for a, _ in c["times"]:
                i = int(round((a - J["t0"]) / J["dt"]))
                y[max(0, i - 3):min(n, i + 4)] = 1
            Xs.append(X[::step]); Ys.append(y[::step])
    return np.vstack(Xs), np.concatenate(Ys)
X, Y = load(sys.argv[1], 2); Xt, Yt = load(sys.argv[2], 2); print("train frames", len(Y), "onset share %.3f" % Y.mean())
for name, mdl in [("logistic", LogisticRegression(max_iter=2000, C=0.5, class_weight="balanced")), ("trees", HistGradientBoostingClassifier(max_iter=150, max_depth=4, learning_rate=0.1, class_weight="balanced"))]:
    mdl.fit(X, Y); p = mdl.predict(Xt); tp = ((p == 1) & (Yt == 1)).sum(); fp = ((p == 1) & (Yt == 0)).sum(); fn = ((p == 0) & (Yt == 1)).sum()
    print(f"{name}: frame precision {tp/(tp+fp):.2f} recall {tp/(tp+fn):.2f}")

# event level: pick peaks of the onset probability and match to true starts within 100 ms (same test as score_ht's "onsets")
def events(mdl, sets, th):
    F = []
    for s in sets.split(","):
        idx = json.load(open(os.path.join(HERE, s, "index.json")))
        for k, c in idx.items():
            f = os.path.join(HERE, "out_" + s, k + ".json")
            if not os.path.exists(f): continue
            J = json.load(open(f)); p = mdl.predict_proba(clip_feats(J))[:, 1]; p = np.convolve(p, np.ones(3) / 3, "same")
            pk = [i for i in range(len(p)) if p[i] >= th and p[i] == p[max(0, i - 6):i + 7].max()]
            got = [J["t0"] + i * J["dt"] for i in pk]; ref = [a for a, _ in c["times"]]; used = set(); tp = 0
            for g in got:
                j = next((j for j, r in enumerate(ref) if j not in used and abs(r - g) <= 0.1), None)
                if j is not None: used.add(j); tp += 1
            F.append(2 * tp / (len(got) + len(ref)))
    return 100 * np.mean(F)
for th in (0.5, 0.6, 0.7, 0.8):
    print(f"trees, threshold {th}: onset F (100 ms) held-back {events(mdl, sys.argv[2], th):.1f}")
