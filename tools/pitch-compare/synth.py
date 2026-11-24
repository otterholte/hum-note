"""Synthesize sung-like test clips with KNOWN pitch.

Additive glottal source (harmonics with spectral tilt) shaped by a vowel/hum formant
envelope sampled at each harmonic, plus vibrato, scoops, drift, breathiness, breath noises
between phrases, quiet passages, background noise at several SNRs, octave-ambiguous low
notes (weak fundamental, period-doubling) and high notes.

Writes synth/<name>.wav (48 kHz, 16-bit) and synth/<name>.npz with the 10 ms truth grid:
  t, f0 (Hz, 0 = unvoiced), voiced, guard (frames to skip for voicing metrics),
  steady (note interiors, away from scoops/onsets), band (0 mid, 1 low, 2 high).
usage: python synth.py
"""
import os, json
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

FS = 48000
HOP_T = 0.01
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "synth")

VOWELS = {  # (freq, bandwidth, gain dB)
    "a": [(800, 80, 0), (1150, 90, -4), (2900, 120, -20), (3900, 130, -28)],
    "e": [(400, 60, 0), (1700, 90, -10), (2600, 110, -16), (3800, 130, -26)],
    "i": [(270, 60, 0), (2290, 90, -14), (3010, 110, -18), (3800, 130, -26)],
    "o": [(450, 70, 0), (800, 80, -6), (2830, 120, -26), (3800, 130, -32)],
    "u": [(325, 60, 0), (700, 70, -12), (2530, 120, -30), (3500, 130, -36)],
    "m": [(250, 50, 0), (1000, 300, -26), (2200, 200, -34), (3300, 250, -40)],  # hum (nasal murmur)
}


def envelope_db(f, vowel):
    """Formant envelope in dB at frequencies f for a vowel (sum of resonances)."""
    H = np.zeros_like(f) + 1e-4
    for F, B, g in VOWELS[vowel]:
        mag = F * F / np.sqrt((F * F - f * f) ** 2 + (B * f) ** 2 + 1e-9)
        H = H + (10 ** (g / 20)) * mag
    return 20 * np.log10(H)


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def pink(n, rng):
    w = rng.standard_normal(n)
    W = np.fft.rfft(w)
    f = np.arange(len(W)); f[0] = 1
    y = np.fft.irfft(W / np.sqrt(f), n)
    return y / (np.std(y) + 1e-12)


def make_clip(spec, rng):
    """spec: dict with phrases [[(midi, dur, vowel), ...], ...] and options."""
    o = dict(vib_rate=(5.0, 7.0), vib_pp=(1.0, 2.0), tilt=1.6, hnr_db=30, snr_db=None,
             gap=(0.35, 0.8), breath=True, phrase_gain_db=None, weak_f0=False, fry=False,
             detune_c=15, scoop=(0.05, 0.11), hum=False)
    o.update(spec.get("opt", {}))
    phrases = spec["phrases"]
    # ---- control-rate contour (1 ms) ----
    cr = 1000
    segs = []  # (start, end, midi, vowel, phrase_idx, first_in_phrase)
    t = 0.3
    for pi, ph in enumerate(phrases):
        for ni, (midi, dur, vow) in enumerate(ph):
            segs.append([t, t + dur, midi + rng.uniform(-1, 1) * o["detune_c"] / 100, vow, pi, ni == 0, ni == len(ph) - 1])
            t += dur
        t += rng.uniform(*o["gap"])
    T = t + 0.3
    nc = int(T * cr) + 1
    tc = np.arange(nc) / cr
    midi_c = np.full(nc, np.nan)
    amp_c = np.zeros(nc)
    steady_c = np.zeros(nc, bool)
    vow_idx = np.zeros(nc, int)
    vnames = list(VOWELS)
    pgain = []
    for pi in range(len(phrases)):
        if o["phrase_gain_db"] is not None:
            pgain.append(10 ** (o["phrase_gain_db"][pi % len(o["phrase_gain_db"])] / 20))
        else:
            pgain.append(10 ** (rng.uniform(-4, 0) / 20))
    prev_m = None
    for (a, b, m, vow, pi, first, last) in segs:
        i0, i1 = int(a * cr), int(b * cr)
        L = i1 - i0
        tt = (np.arange(L)) / cr
        dur = b - a
        cur = np.full(L, m)
        sc = rng.uniform(*o["scoop"])
        if first:
            # onset scoop from below (1-3 semitones), fast
            depth = rng.uniform(0.6, 2.5)
            cur = cur - depth * (1 - smoothstep(tt / sc))
            prev_m = None
        elif prev_m is not None:
            # glide from previous note with slight overshoot
            d = prev_m - m
            g = 1 - smoothstep(tt / sc)
            over = -0.15 * np.sign(d) * min(abs(d), 3) * np.sin(np.pi * np.clip((tt - sc) / 0.08, 0, 1)) * (tt > sc)
            cur = cur + d * g + over * 0.5
        # vibrato on longer notes
        if dur > 0.45:
            rate = rng.uniform(*o["vib_rate"])
            pp = rng.uniform(*o["vib_pp"])
            onset = rng.uniform(0.15, 0.3)
            fade = smoothstep((tt - onset) / 0.25)
            rate_t = rate * (1 + 0.04 * np.sin(2 * np.pi * 0.7 * tt))
            ph = 2 * np.pi * np.cumsum(rate_t) / cr + rng.uniform(0, 2 * np.pi)
            cur = cur + 0.5 * pp * fade * np.sin(ph)
        # slow drift (truth too)
        dr = np.cumsum(rng.standard_normal(L)) / cr
        dr = np.convolve(dr - np.linspace(dr[0], dr[-1], L), np.ones(60) / 60, "same")
        cur = cur + 0.08 * dr / (np.std(dr) + 1e-9) * 0.5
        midi_c[i0:i1] = cur
        # amplitude: attack/release only at phrase edges, small dip between notes
        env = np.ones(L)
        if first:
            env *= smoothstep(tt / 0.035)
        if last:
            env *= smoothstep((dur - tt) / 0.06)
        env *= 10 ** (rng.uniform(-3, 0) / 20)
        # syllable articulation ("la-la", "hm-hm"): a short dip in loudness at each new note inside a phrase
        if not first and o.get("artic_db"):
            dip = 1 - (1 - 10 ** (-o["artic_db"] / 20)) * np.exp(-0.5 * ((tt - 0.025) / 0.022) ** 2)
            env *= dip
        amp_c[i0:i1] = env * pgain[pi]
        st = (tt > max(sc + 0.08, 0.12)) & (tt < dur - 0.05)
        steady_c[i0:i1] = st
        vow_idx[i0:i1] = vnames.index(vow)
        prev_m = m
    # fill unvoiced midi with nearest for phase continuity (irrelevant, amp=0)
    idx = np.where(~np.isnan(midi_c))[0]
    midi_fill = np.interp(np.arange(nc), idx, midi_c[idx])
    # ---- audio rate ----
    n = int(T * FS)
    ta = np.arange(n) / FS
    midi_a = np.interp(ta, tc, midi_fill)
    amp_a = np.interp(ta, tc, amp_c)
    f0_a = 440 * 2 ** ((midi_a - 69) / 12)
    # small cycle-level jitter (~3 cents rms, white-ish at 200 Hz) - part of the source, not truth
    jit = np.interp(ta, np.arange(0, T, 0.005), rng.standard_normal(len(np.arange(0, T, 0.005)))) * 0.03
    f_inst = f0_a * 2 ** (jit / 12)
    phase = 2 * np.pi * np.cumsum(f_inst) / FS
    y = np.zeros(n)
    # harmonic amplitudes at control rate, interpolated
    tcb = np.arange(0, T, 0.0025)
    f0_cb = np.interp(tcb, ta, f0_a)
    vow_cb = np.interp(tcb, tc, vow_idx).round().astype(int)
    # smooth vowel changes: crossfade envelopes in dB over 40 ms
    K = int(min(9000 / f0_a.min(), 120))
    envs = np.zeros((len(tcb), K))
    for vi, vn in enumerate(vnames):
        sel = vow_cb == vi
        if not sel.any():
            continue
        f = np.outer(f0_cb[sel], np.arange(1, K + 1))
        envs[sel] = envelope_db(f, vn)
    ker = np.ones(16) / 16
    for k in range(K):
        envs[:, k] = np.convolve(envs[:, k], ker, "same")
    kk = np.arange(1, K + 1)
    tilt = o["tilt"] + (1.2 if o["hum"] else 0)
    src_db = -20 * tilt * np.log10(kk)
    if o["weak_f0"]:
        src_db[0] -= 18; src_db[1] += 2
    hd = envs + src_db[None, :]
    for k in range(K):
        fk = f0_cb * (k + 1)
        g = 10 ** (hd[:, k] / 20) * (fk < 0.45 * FS) * np.clip((9000 - fk) / 1500, 0, 1)
        if not g.any():
            continue
        y += np.interp(ta, tcb, g) * np.sin((k + 1) * phase + 0.3 * k * k)
    if o["fry"]:  # period doubling: half-harmonics at -18 dB, on lowest notes
        for k in range(1, 30, 2):
            g = 10 ** ((-18 - 20 * tilt * np.log10(k / 2 + 0.5)) / 20)
            y += 0.6 * g * np.sin(k * phase / 2)
    y *= amp_a
    v_rms = np.sqrt(np.mean(y[amp_a > 0.05] ** 2))
    # breathiness: aspiration noise modulated by glottal cycle
    asp = rng.standard_normal(n)
    asp = sosfilt(butter(2, [1200, 7000], "band", fs=FS, output="sos"), asp)
    asp *= (0.55 + 0.45 * np.cos(phase)) * amp_a
    asp *= v_rms / (np.sqrt(np.mean(asp[amp_a > 0.05] ** 2)) + 1e-12) * 10 ** (-o["hnr_db"] / 20)
    y += asp
    # breaths in gaps + onset aspirations
    if o["breath"]:
        for i, s in enumerate(segs):
            if s[5]:  # first note of phrase -> breath just before
                a = s[0] - rng.uniform(0.25, 0.32)
                L = int(rng.uniform(0.15, 0.22) * FS)
                i0 = int(a * FS)
                if i0 < 0:
                    continue
                b = sosfilt(butter(2, [400, 5000], "band", fs=FS, output="sos"), rng.standard_normal(L))
                b *= np.sin(np.pi * np.arange(L) / L) ** 2
                b *= v_rms * 10 ** (rng.uniform(-22, -14) / 20) / (np.std(b) + 1e-12)
                y[i0:i0 + L] += b
    # background noise
    floor = pink(n, rng) * v_rms * 10 ** (-58 / 20) + rng.standard_normal(n) * v_rms * 10 ** (-66 / 20)
    y += floor
    if o["snr_db"] is not None:
        nz = 0.7 * pink(n, rng) + 0.3 * rng.standard_normal(n)
        nz = sosfilt(butter(2, 60, "high", fs=FS, output="sos"), nz)
        y += nz / np.std(nz) * v_rms * 10 ** (-o["snr_db"] / 20)
    y = y / (np.max(np.abs(y)) + 1e-9) * 0.7
    # ---- truth at 10 ms ----
    tf = np.arange(0, T - 0.05, HOP_T)
    f0_t = np.interp(tf, ta, f0_a)
    a_t = np.interp(tf, tc, amp_c)
    # voiced where source amplitude is above -20 dB of its own phrase level
    ph_level = np.zeros(nc)
    for s in segs:
        ph_level[int(s[0] * cr):int(s[1] * cr)] = pgain[s[4]]
    lev_t = np.interp(tf, tc, ph_level)
    voiced = (a_t > 0.1 * np.maximum(lev_t, 1e-9)) & (lev_t > 0)
    # guard: +/-2 frames around voicing boundaries
    edge = np.zeros_like(voiced)
    ch = np.where(np.diff(voiced.astype(int)) != 0)[0]
    for c in ch:
        edge[max(0, c - 2):c + 4] = True
    steady = (np.interp(tf, tc, steady_c.astype(float)) > 0.5) & voiced
    band = np.where(f0_t < 160, 1, np.where(f0_t > 550, 2, 0))
    f0_t = np.where(voiced, f0_t, 0.0)
    return y.astype(np.float32), dict(t=tf, f0=f0_t, voiced=voiced, guard=edge, steady=steady, band=band)


def melody(rng, lo, hi, n, dur=(0.25, 0.9), vowels="aeiou", step=(1, 2, 2, 3, 4, 5, 7)):
    m = rng.integers(lo + 3, hi - 3)
    out = []
    for _ in range(n):
        m = int(np.clip(m + rng.choice(step) * rng.choice([-1, 1]), lo, hi))
        out.append((m, float(rng.uniform(*dur)), rng.choice(list(vowels))))
    return out


def phrases(rng, lo, hi, nphr, nn=(3, 7), **kw):
    return [melody(rng, lo, hi, int(rng.integers(*nn)), **kw) for _ in range(nphr)]


def build_specs(rng):
    S = {}
    S["mid_vowels"] = dict(phrases=phrases(rng, 45, 64, 4), opt={})                      # A2..E4
    S["hum_mid"] = dict(phrases=phrases(rng, 50, 65, 4, vowels="m"), opt=dict(hum=True))  # hum, D3..F4
    S["fast_runs"] = dict(phrases=phrases(rng, 50, 67, 4, nn=(8, 14), dur=(0.07, 0.16), step=(1, 2, 2, 3)),
                          opt=dict(scoop=(0.025, 0.05)))
    S["low_ambiguous"] = dict(phrases=phrases(rng, 39, 50, 4, vowels="ao"), opt=dict(weak_f0=True, fry=True))  # ~78-147 Hz
    S["high"] = dict(phrases=phrases(rng, 74, 82, 4, vowels="aeio"), opt=dict(tilt=1.3))  # ~587-932 Hz
    S["breathy"] = dict(phrases=phrases(rng, 48, 64, 4), opt=dict(hnr_db=6))
    S["wide_vibrato"] = dict(phrases=phrases(rng, 48, 64, 4, dur=(0.7, 1.4)), opt=dict(vib_pp=(1.8, 2.4), vib_rate=(6, 7.5)))
    S["quiet"] = dict(phrases=phrases(rng, 48, 64, 4), opt=dict(phrase_gain_db=[0, -24, -30, -18], snr_db=35))
    base = phrases(rng, 47, 64, 4)
    for snr in (30, 20, 10):
        S[f"snr{snr}"] = dict(phrases=base, opt=dict(snr_db=snr))
    hb = phrases(rng, 50, 65, 4, vowels="m")
    S["hum_snr15"] = dict(phrases=hb, opt=dict(hum=True, snr_db=15))
    return S


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(1234)
    specs = build_specs(rng)
    info = {}
    for name, spec in specs.items():
        y, tr = make_clip(spec, np.random.default_rng(len(info) + 7))
        sf.write(os.path.join(OUT, name + ".wav"), y, FS, subtype="PCM_16")
        np.savez(os.path.join(OUT, name + ".npz"), **tr)
        info[name] = dict(sec=round(len(y) / FS, 2), voiced_frames=int(tr["voiced"].sum()),
                          f0_range=[round(float(tr["f0"][tr["voiced"]].min())), round(float(tr["f0"][tr["voiced"]].max()))])
        print(name, info[name])
    json.dump(info, open(os.path.join(OUT, "index.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
