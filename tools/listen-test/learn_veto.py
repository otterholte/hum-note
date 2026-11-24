"""Learns which of the app's same-pitch splits are real (new syllable) vs false (consonant / diphthong inside one note),
from sets with exact note timings. Features are measured at each split the current app makes.
usage: python learn_veto.py train_sets test_sets   (comma-separated; out_<set>/ must hold the app's output)"""
import sys, os, json, numpy as np
from sklearn.tree import DecisionTreeClassifier, export_text
HERE = os.path.dirname(os.path.abspath(__file__)); NAMES = ["rise", "fall", "nv", "durP", "durN", "dmin", "unv", "vib"]
def feats(set_):
    idx = json.load(open(os.path.join(HERE, set_, "index.json"))); X = []; Y = []
    for k, c in idx.items():
        f = os.path.join(HERE, "out_" + set_, k + ".json")
        if not os.path.exists(f): continue
        A = json.load(open(f)); ds = np.array([v if v is not None else -99 for v in A["ds"]], float); nv = np.array(A["nv"], float); N = A["notes"]
        for j in range(1, len(N)):
            p, n = N[j - 1], N[j]
            if p["pitch"] != n["pitch"] or n["start"] - p["end"] > 0.08: continue
            i = int(round((n["start"] - A["t0"]) / A["dt"])); lo = ds[i - 6:i + 4].min(); R = ds[i:i + 13].max(); L = ds[i - 14:i - 4].max()
            unv = sum(1 for q in range(i - 8, i + 2) if not A["voiced"][q])
            X.append([R - lo, L - lo, nv[i - 6:i + 4].max(), p["end"] - p["start"], n["end"] - n["start"], min(p["end"] - p["start"], n["end"] - n["start"]), unv, A["vib"][i]])
            Y.append(int(any(abs(t[0] - n["start"]) < 0.08 for t in c["times"])))
    return np.array(X), np.array(Y)
def load(sets): XY = [feats(s) for s in sets.split(",")]; return np.vstack([a for a, _ in XY]), np.concatenate([b for _, b in XY])
X, Y = load(sys.argv[1]); Xt, Yt = load(sys.argv[2]); print(f"train {len(Y)} splits ({Y.sum()} real) | test {len(Yt)} ({Yt.sum()} real)")
for d in (1, 2, 3):
    t = DecisionTreeClassifier(max_depth=d, min_samples_leaf=8, random_state=0).fit(X, Y); p = t.predict(Xt)
    print(f"depth {d}: test accuracy {np.mean(p == Yt):.2f} (keep-all {np.mean(Yt):.2f}); false kept {((p==1)&(Yt==0)).sum()} real lost {((p==0)&(Yt==1)).sum()}")
    print(export_text(t, feature_names=NAMES, decimals=2))
