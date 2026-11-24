"""Compare models on recordings with NO ground truth (the user's takes, VocalSet excerpts).

Reference = consensus of the two best models on the synthetic set (rmvpe + swiftf0): a frame counts
as consensus-voiced when both say voiced and agree within 50 cents (pitch = their mean), and as
consensus-unvoiced when both say unvoiced. Scores are AGREEMENT with that consensus, not truth.
usage: python real_compare.py out/real real   (and)   python real_compare.py out/vocalset vocalset
Writes agreement_<set>.json/.md and, for the 'real' set, plot_*.png excerpts.
"""
import lowprio  # noqa: F401
import glob, json, os, sys
import numpy as np
from eval_synth import load_est, sample, MODELS

HERE = os.path.dirname(os.path.abspath(__file__))
REF = ("rmvpe", "swiftf0")
offs = json.load(open(os.path.join(HERE, "results_synth.json")))["offsets"]


def grid(outdir, name):
    S = {}
    T = None
    for m in MODELS:
        e = load_est(m, name, outdir)
        if T is None:
            T = np.arange(0.02, e["t"][-1] - 0.02, 0.01)
        S[m] = sample(e, T + offs[m])
    a, b = S[REF[0]], S[REF[1]]
    both = a["voiced"] & b["voiced"] & np.isfinite(a["c"]) & np.isfinite(b["c"])
    agree = both & (np.abs(a["c"] - b["c"]) <= 50)
    cons = np.where(agree, (a["c"] + b["c"]) / 2, np.nan)
    cons_uv = ~a["voiced"] & ~b["voiced"]
    return T, S, cons, agree, cons_uv, both


def score(sets):
    res = {}
    for m in MODELS:
        V = r50 = r20 = octv = tp = fp = U = 0
        for T, S, cons, agree, uv, both in sets:
            s = S[m]; err = s["c"] - cons; ok = np.isfinite(err)
            V += agree.sum()
            r50 += (agree & ok & s["voiced"] & (np.abs(err) <= 50)).sum()
            r20 += (agree & ok & s["voiced"] & (np.abs(err) <= 20)).sum()
            octv += (agree & ok & (np.abs(np.abs(err) - 1200) <= 100)).sum()
            tp += (agree & s["voiced"]).sum()
            fp += (uv & s["voiced"]).sum(); U += uv.sum()
        res[m] = dict(agree50=r50 / V, agree20=r20 / V, octave=octv / V, voiced_on_consensus=tp / V,
                      voiced_where_both_ref_unvoiced=fp / max(U, 1))
    return res


def main():
    outdir, wavdir = sys.argv[1], sys.argv[2]
    tag = os.path.basename(os.path.normpath(wavdir))
    names = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(wavdir, "*.wav")))
    G = {n: grid(outdir, n) for n in names}
    res = score(list(G.values()))
    ref_agree = sum(g[3].sum() for g in G.values()) / max(sum(g[5].sum() for g in G.values()), 1)
    secs = sum(len(g[0]) for g in G.values()) / 100
    json.dump(dict(models=res, ref_pair_agreement=ref_agree, seconds=secs), open(os.path.join(HERE, f"agreement_{tag}.json"), "w"), indent=1)
    pc = lambda v: f"{100 * v:.1f}%"
    L = [f"{len(names)} files, {secs:.0f} s. RMVPE and SwiftF0 agree within 50 cents on {pc(ref_agree)} of the frames both call voiced.", "",
         "| model | voiced & within ±50c of consensus | within ±20c | octave off | voiced where both refs unvoiced |", "|---|---|---|---|---|"]
    for m in MODELS:
        o = res[m]
        L.append(f"| {m} | {pc(o['agree50'])} | {pc(o['agree20'])} | {pc(o['octave'])} | {pc(o['voiced_where_both_ref_unvoiced'])} |")
    # per file for yin_app
    L += ["", "Per file, app YIN vs consensus (voiced & ±50c):", "", "| file | yin_app | yin_tuner | crepe_full |", "|---|---|---|---|"]
    for n, g in G.items():
        r = score([g]); L.append(f"| {n} | {pc(r['yin_app']['agree50'])} | {pc(r['yin_tuner']['agree50'])} | {pc(r['crepe_full']['agree50'])} |")
    open(os.path.join(HERE, f"agreement_{tag}.md"), "w", encoding="utf8").write("\n".join(L) + "\n")
    print("\n".join(L))
    if tag == "real":
        plots(G, wavdir)


def plots(G, wavdir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from models import load_audio
    # pick windows: most vibrato-like wobble, most note changes, most YIN disagreement
    cand = []
    for n, (T, S, cons, agree, uv, both) in G.items():
        W = 400
        for s0 in range(0, max(1, len(T) - W), 50):
            c = cons[s0:s0 + W]; fin = np.isfinite(c)
            if fin.mean() < 0.6: continue
            d = np.diff(c); d = d[np.isfinite(d)]
            jumps = (np.abs(d) > 70).sum()
            wob = np.nanstd(c - np.convolve(np.nan_to_num(c), np.ones(25) / 25, "same"))
            y = S["yin_app"]; e = np.abs(y["c"][s0:s0 + W] - c)
            dis = np.mean(((e > 50) | ~y["voiced"][s0:s0 + W])[fin])
            cand.append((n, s0, W, wob, jumps, dis))
    picks = []
    for key, label in ((3, "vibrato"), (4, "fast notes"), (5, "YIN disagrees most")):
        for c in sorted(cand, key=lambda c: -c[key]):
            if all(c[0] != p[0] or abs(c[1] - p[1]) > 400 for p in picks):
                picks.append(c + (label,)); break
    show = [("yin_app", "#2a78d6", "YIN (app today)"), ("swiftf0", "#eb6834", "SwiftF0"),
            ("rmvpe", "#1baf7a", "RMVPE"), ("crepe_full", "#eda100", "CREPE full")]
    for i, (n, s0, W, _, _, _, label) in enumerate(picks):
        T, S, cons, *_ = G[n]
        x = load_audio(os.path.join(wavdir, n + ".wav"))
        t0, t1 = T[s0], T[min(s0 + W, len(T) - 1)]
        seg = x[int(t0 * 16000):int(t1 * 16000)]
        fig, ax = plt.subplots(figsize=(11, 4.6), dpi=110)
        fig.patch.set_facecolor("#fcfcfb"); ax.set_facecolor("#fcfcfb")
        # spectrogram (gray) on a MIDI axis as visual evidence
        nfft, hop = 2048, 160
        win = np.hanning(nfft); frames = []
        for k in range(0, len(seg) - nfft, hop):
            frames.append(np.abs(np.fft.rfft(seg[k:k + nfft] * win)))
        Sp = 20 * np.log10(np.array(frames).T + 1e-6)
        fr = np.fft.rfftfreq(nfft, 1 / 16000)
        mid = np.arange(30, 96, 0.25); fm = 440 * 2 ** ((mid - 69) / 12)
        img = np.array([np.interp(fm, fr, col) for col in Sp.T]).T
        vmax = img.max()
        ax.imshow(img, origin="lower", aspect="auto", cmap="Greys", vmin=vmax - 60, vmax=vmax,
                  extent=[t0 + nfft / 32000, t0 + nfft / 32000 + img.shape[1] * hop / 16000, mid[0], mid[-1]], alpha=0.45)
        allm = []
        for m, col, lab in show:
            s = S[m]; mm = s["c"][s0:s0 + W] / 100 + 12 * np.log2(10 / 440) + 69
            mm = np.where(s["voiced"][s0:s0 + W], mm, np.nan)
            ax.plot(T[s0:s0 + W], mm, color=col, lw=2 if m != "yin_app" else 2.4, label=lab, alpha=0.95 if m == "yin_app" else 0.85)
            allm.append(mm)
        allm = np.concatenate(allm); lo, hi = np.nanpercentile(allm, 1) - 3, np.nanpercentile(allm, 99) + 3
        ax.set_ylim(lo, hi); ax.set_xlim(t0, t1)
        names_ = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        ticks = np.arange(np.ceil(lo), np.floor(hi) + 1)
        ax.set_yticks(ticks); ax.set_yticklabels([names_[int(k) % 12] + str(int(k) // 12 - 1) if names_[int(k) % 12] in ("C", "E", "G", "A") else "" for k in ticks])
        ax.grid(axis="y", color="#e4e3df", lw=0.6)
        for sp in ("top", "right"): ax.spines[sp].set_visible(False)
        ax.set_xlabel("seconds", color="#52514e"); ax.set_ylabel("pitch", color="#52514e")
        ax.set_title(f"{n}  ({label})  - lines = voiced frames only; gray = spectrogram", color="#0b0b0b", fontsize=11, loc="left")
        ax.legend(loc="upper right", frameon=False, ncol=4, fontsize=9)
        fig.tight_layout()
        fn = os.path.join(HERE, f"plot_{i + 1}_{label.split()[0].lower()}.png")
        fig.savefig(fn, facecolor=fig.get_facecolor()); plt.close(fig)
        print("wrote", fn, n, f"{t0:.1f}-{t1:.1f}s")


if __name__ == "__main__":
    main()
