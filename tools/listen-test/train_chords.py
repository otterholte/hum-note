"""Learns how folk/children's tunes are harmonised (from 80% of the Nottingham tunes; every 5th tune is held back):
  - how likely each chord is (relative to the key: I, IV, V, vi, ...),
  - how chords follow each other, and how likely a change is on each beat of the bar,
  - which melody notes (relative to the key) sit over each chord, on strong and on weak beats.
Writes chord_model.json (log-probabilities) for the app's chord picker. usage: python train_chords.py"""
import json, math
T = json.load(open("nott.json")); names = sorted(T); train = [n for i, n in enumerate(names) if i % 5]
Q = {"": 0, "7": 0, "m": 1, "m7": 1, "dim": 2}; S = 36  # state = degree*3 + quality (major, minor, diminished)
def beats(t):
    L = int(max(max(e for _, e, _ in t["mel"]), max(c[1] for c in t["chords"])) + 0.5); st = [-1] * L
    for s, e, r, q in t["chords"]:
        for b in range(int(s + 0.01), min(L, int(e - 0.01) + 1)): st[b] = ((r - t["tonic"]) % 12) * 3 + Q[q]
    return L, st
model = {}
for mode in (False, True):
    prior = [1.0] * S; trans = [[0.2] * S for _ in range(S)]; stay = {}; emis = [[[0.5] * 12 for _ in range(2)] for _ in range(S)]
    tunes = [T[n] for n in train if T[n]["minor"] == mode] or [T[n] for n in train]
    for t in tunes:
        L, st = beats(t); m = t["meter"]; prev = -1
        for b in range(L):
            s = st[b]
            if s < 0: continue
            if prev < 0: prior[s] += 1
            else:
                pos = b % m; k = f"{m}:{pos}"; a = stay.setdefault(k, [1, 1]); a[0 if s == prev else 1] += 1
                if s != prev: trans[prev][s] += 1
            prev = s
        for s0, e0, p in t["mel"]:
            for b in range(int(s0), int(math.ceil(e0 - 1e-6))):
                if b >= L or st[b] < 0: continue
                ov = min(e0, b + 1) - max(s0, b); strong = 1 if (b % t["meter"] == 0 or (t["meter"] == 4 and b % 4 == 2)) and s0 <= b + 0.01 else 0
                emis[st[b]][strong][(p - t["tonic"]) % 12] += ov
    lg = lambda v: [round(math.log(x / sum(v)), 3) for x in v]
    model["minor" if mode else "major"] = dict(prior=lg(prior), trans=[lg(r) for r in trans], emis=[[lg(e) for e in em] for em in emis],
                                               change={k: round(math.log(v[1] / sum(v)), 3) for k, v in stay.items()}, stay={k: round(math.log(v[0] / sum(v)), 3) for k, v in stay.items()})
json.dump(model, open("chord_model.json", "w")); print("trained on", len(train), "tunes; held back", len(names) - len(train))
