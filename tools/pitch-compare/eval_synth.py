"""Score every model against the synthetic truth.
usage: python eval_synth.py   (reads synth/*.npz and out/synth/<model>/*, writes results_synth.json/.md)
"""
import lowprio  # noqa: F401
import glob, json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = ["yin_app", "yin_tuner", "crepe_tiny", "crepe_full", "swiftf0", "pesto", "rmvpe", "fcpe"]


def load_est(model, name, base=os.path.join(HERE, "out", "synth")):
    p = os.path.join(base, model, name)
    if os.path.exists(p + ".json"):
        d = json.load(open(p + ".json"))
        return dict(t=np.array(d["t"]), f0=np.array(d["f0"], float), voiced=np.array(d["voiced"], bool), conf=None)
    d = np.load(p + ".npz")
    c = d["conf"]
    return dict(t=d["t"], f0=d["f0"].astype(float), voiced=d["voiced"].astype(bool), conf=None if np.all(np.isnan(c)) else c)


def sample(est, tt):
    """Model pitch (cents re 10 Hz, NaN if none) and voicing at truth times tt."""
    t, f = est["t"], est["f0"]
    c = np.where((f > 0) & np.isfinite(f), 1200 * np.log2(np.maximum(f, 1e-9) / 10), np.nan)
    i = np.clip(np.searchsorted(t, tt) - 1, 0, len(t) - 2)
    w = np.clip((tt - t[i]) / (t[i + 1] - t[i]), 0, 1)
    a, b = c[i], c[i + 1]
    v = np.where(np.isnan(a), b, np.where(np.isnan(b), a, a + w * (b - a)))
    near = np.where(w < 0.5, i, i + 1)
    out = dict(c=v, voiced=est["voiced"][near])
    if est["conf"] is not None:
        out["conf"] = est["conf"][near]
    return out


def truth(name):
    d = np.load(os.path.join(HERE, "synth", name + ".npz"))
    tr = {k: d[k] for k in d.files}
    tr["c"] = np.where(tr["voiced"], 1200 * np.log2(np.maximum(tr["f0"], 1e-9) / 10), np.nan)
    return tr


def best_offset(model, names):
    lags = np.arange(-0.04, 0.0401, 0.002)
    errs = []
    for L in lags:
        e = []
        for n in names:
            tr = truth(n); s = sample(load_est(model, n), tr["t"] + L)
            m = tr["steady"]
            d = np.abs(s["c"][m] - tr["c"][m]); d = d[np.isfinite(d)]
            e.append(np.minimum(d, 100))
        errs.append(np.mean(np.concatenate(e)))
    return float(lags[int(np.argmin(errs))])


def metrics(pairs):
    """pairs: list of (truth, sampled) for one model."""
    V = UV = 0; r50 = r20 = octv = vx = 0
    tp = fp = fn = 0; jit = []; conf_all = []; lab_all = []
    for tr, s in pairs:
        g = ~tr["guard"]
        vt = tr["voiced"] & g
        err = s["c"] - tr["c"]
        ok = np.isfinite(err)
        V += vt.sum()
        r50 += (vt & ok & (np.abs(err) <= 50)).sum()
        r20 += (vt & ok & (np.abs(err) <= 20)).sum()
        oc = ok & (np.abs(err) > 50) & (np.abs(np.abs(err) - 1200) <= 100) | ok & (np.abs(np.abs(err) - 2400) <= 100)
        octv += (vt & oc).sum()
        vx += (vt & s["voiced"] & ok & (np.abs(err) <= 50)).sum()
        tp += (vt & s["voiced"]).sum(); fn += (vt & ~s["voiced"]).sum()
        fp += (~tr["voiced"] & g & s["voiced"]).sum(); UV += (~tr["voiced"] & g).sum()
        # jitter: std of error within each steady run, after removing that run's mean (truth already holds the vibrato)
        st = tr["steady"] & ok & (np.abs(np.nan_to_num(err, nan=1e9)) < 100)
        idx = np.where(st)[0]
        if len(idx):
            runs = np.split(idx, np.where(np.diff(idx) > 1)[0] + 1)
            for r in runs:
                if len(r) >= 8:
                    jit.append(err[r] - err[r].mean())
        if "conf" in s:
            conf_all.append(s["conf"][g]); lab_all.append(tr["voiced"][g])
    out = dict(rpa50=r50 / V, rpa20=r20 / V, octave=octv / V, vx_correct=vx / V,
               v_precision=tp / max(tp + fp, 1), v_recall=tp / max(tp + fn, 1), false_voiced_in_silence=fp / max(UV, 1),
               jitter_cents=float(np.sqrt(np.mean(np.concatenate(jit) ** 2))) if jit else np.nan)
    out["v_f1"] = 2 * out["v_precision"] * out["v_recall"] / (out["v_precision"] + out["v_recall"] + 1e-12)
    if conf_all:
        c = np.concatenate(conf_all); l = np.concatenate(lab_all); best = (0, 0)
        for th in np.linspace(0.02, 0.98, 49):
            p = c >= th; tp_ = (p & l).sum(); pr = tp_ / max(p.sum(), 1); rc = tp_ / max(l.sum(), 1)
            f1 = 2 * pr * rc / (pr + rc + 1e-12)
            if f1 > best[0]: best = (f1, th)
        out["v_f1_best"], out["v_best_thresh"] = float(best[0]), float(best[1])
    return {k: float(v) for k, v in out.items()}


def main():
    names = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(HERE, "synth", "*.npz")))
    calib = ["mid_vowels", "wide_vibrato", "snr30"]
    res = dict(offsets={}, overall={}, per_clip={})
    for m in MODELS:
        off = best_offset(m, calib); res["offsets"][m] = off
        pairs = {n: (truth(n), None) for n in names}
        pairs = {n: (tr, sample(load_est(m, n), tr["t"] + off)) for n, (tr, _) in pairs.items()}
        res["overall"][m] = metrics(list(pairs.values()))
        res["per_clip"][m] = {n: metrics([p]) for n, p in pairs.items()}
        print(m, "offset %+.0f ms" % (1000 * off), {k: round(v, 3) for k, v in res["overall"][m].items()})
    json.dump(res, open(os.path.join(HERE, "results_synth.json"), "w"), indent=1)
    # markdown
    L = ["| model | RPA ±50c | RPA ±20c | octave err | voiced & ±50c | voicing P | voicing R | false voiced in silence/breath | jitter (cents rms) | best-threshold voicing F1 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    pc = lambda v: f"{100 * v:.1f}%"
    for m in MODELS:
        o = res["overall"][m]
        L.append(f"| {m} | {pc(o['rpa50'])} | {pc(o['rpa20'])} | {pc(o['octave'])} | {pc(o['vx_correct'])} | {pc(o['v_precision'])} | {pc(o['v_recall'])} | {pc(o['false_voiced_in_silence'])} | {o['jitter_cents']:.1f} | "
                 + (f"{o['v_f1_best']:.3f} @ {o['v_best_thresh']:.2f}" if "v_f1_best" in o else "–") + " |")
    L += ["", "Per clip, **voiced & within 50 cents** (what a note decoder actually gets):", "",
          "| clip | " + " | ".join(MODELS) + " |", "|---" * (len(MODELS) + 1) + "|"]
    for n in names:
        L.append(f"| {n} | " + " | ".join(pc(res['per_clip'][m][n]['vx_correct']) for m in MODELS) + " |")
    L += ["", "Per clip, **octave errors**:", "", "| clip | " + " | ".join(MODELS) + " |", "|---" * (len(MODELS) + 1) + "|"]
    for n in names:
        L.append(f"| {n} | " + " | ".join(pc(res['per_clip'][m][n]['octave']) for m in MODELS) + " |")
    L += ["", "Per clip, **jitter on steady notes (cents rms)**:", "", "| clip | " + " | ".join(MODELS) + " |", "|---" * (len(MODELS) + 1) + "|"]
    for n in names:
        L.append(f"| {n} | " + " | ".join(f"{res['per_clip'][m][n]['jitter_cents']:.1f}" for m in MODELS) + " |")
    L += ["", "Time offsets applied (found by best fit on 3 clips): " + ", ".join(f"{m} {1000 * v:+.0f} ms" for m, v in res["offsets"].items())]
    open(os.path.join(HERE, "results_synth.md"), "w", encoding="utf8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
