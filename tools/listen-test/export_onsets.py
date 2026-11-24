"""Fits the logistic onset detector on all sets with exact starts (csd, voc) and writes its weights for the app.
usage: python export_onsets.py   -> onset_weights.json"""
import json, os, sys, numpy as np
sys.argv = [sys.argv[0], "csd,voc", "csdx,vocx"]
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "learn_onsets.py"), encoding="utf-8").read().split("X, Y = load(")[0]
exec(src)
from sklearn.linear_model import LogisticRegression
X, Y = load("csd,voc", 2); mu = X.mean(0); sd = X.std(0) + 1e-6
mdl = LogisticRegression(max_iter=3000, C=0.5, class_weight="balanced").fit((X - mu) / sd, Y)
class M:  # same interface as sklearn for events()
    def predict_proba(self, Z): p = mdl.predict_proba((Z - mu) / sd); return p
_ev = open(os.path.join(HERE, "learn_onsets.py"), encoding="utf-8").read().split("# event level")[1]
exec(_ev[_ev.index("def events"):_ev.index("for th in")])
for th in (0.5, 0.6, 0.7, 0.8): print(f"logistic th {th}: held-back onset F {events(M(), 'csdx,vocx', th):.1f}")
w = (mdl.coef_[0] / sd).tolist(); b = float(mdl.intercept_[0] - (mdl.coef_[0] * mu / sd).sum())
json.dump(dict(off=OFF, w=[round(v, 5) for v in w], b=round(b, 5)), open(os.path.join(HERE, "onset_weights.json"), "w")); print("wrote", len(w), "weights")
