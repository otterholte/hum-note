# Pitch tracker comparison for Hum to MIDI: YIN vs. neural models on singing voice

Measured 2026-11-24 on this machine: laptop RTX 3060 (6 GB), and one CPU thread at idle priority. All scripts are in this folder; `run_all.sh` reruns everything.

## Recommendation

**Switch the live tuner to SwiftF0. Switching transcription to SwiftF0 is worthwhile too, but less urgent.**

* **SwiftF0** (MIT, 135 KB ONNX) is the clear practical winner.
  * On synthetic sung audio with known pitch it gets 99.9% of voiced frames within 50 cents. The app's YIN gets 95.8%.
  * It makes no octave errors, and its jitter is 30% lower (4.9 vs 7.3 cents).
  * It is about as fast as YIN even in the browser: 21 ms per second of audio in WASM, against ~20 ms for YIN in Node.
  * It already runs in Chrome: `browser/index.html` reproduces the Python output frame for frame.
* **The live tuner is the biggest problem.**
  * Its own `yin()`, emulated, reads **an octave low on 17% of frames** of the user's 13 takes, with 76% agreement against 95% for the transcription YIN.
  * The octave snap keeps it locked on the wrong octave.
  * Its absolute RMS gate (0.006) loses quiet singing.
  * SwiftF0 needs only 16–32 ms of lookahead to be fully accurate, so it suits a tuner.
* **The transcription YIN holds up on the user's takes**, which are clean, close-miked humming. It misses 4.8% of consensus frames:
  * 3.4 points: right pitch, thrown away by the `db > peak-32` loudness gate. This drops the whole quiet first phrase of `hum_2026-11-23_212658`.
  * 1.4 points: wrong pitch.

  So the cheapest transcription win needs no ML: loosen that gate. YIN's real weaknesses are breathy and quiet singing (synthetic: 69% and 84%, with 21% octave errors on breathy).
* **RMVPE** is the most accurate (100%, 2.3 cents jitter) but is 181 MB and takes ~96 ms per second of audio on one CPU thread. It only fits server-side.
* **Not recommended:**
  * CREPE full: 89 MB, 4.3 s per second of audio on CPU.
  * CREPE tiny: 10% octave errors on low notes.
  * PESTO: LGPL-3.0, weak on high and quiet notes.
  * FCPE: calls 10–12% of breath and silence voiced.

## Test 1: synthetic singing with known pitch (174 s, 12 clips, `synth.py`)

| model | RPA ±50c | RPA ±20c | octave err | voiced & ±50c | voicing P | voicing R | false voiced | jitter (cents) |
|---|---|---|---|---|---|---|---|---|
| yin_app | 97.1% | 93.1% | 1.7% | 95.8% | 100.0% | 98.3% | 0.0% | 7.3 |
| yin_tuner | 91.5% | 88.4% | 2.1% | 89.8% | 100.0% | 92.5% | 0.0% | 7.6 |
| crepe_tiny | 98.3% | 94.4% | 0.7% | 97.7% | 99.9% | 98.8% | 0.4% | 8.0 |
| crepe_full | 99.5% | 96.3% | 0.1% | 99.0% | 100.0% | 99.3% | 0.1% | 7.8 |
| swiftf0 | 99.9% | 98.8% | 0.0% | 99.9% | 100.0% | 100.0% | 0.0% | 4.9 |
| pesto | 98.4% | 90.0% | 1.4% | 93.5% | 100.0% | 95.1% | 0.0% | 9.5 |
| rmvpe | 100.0% | 99.4% | 0.0% | 100.0% | 99.7% | 100.0% | 1.4% | 2.3 |
| fcpe | 98.9% | 97.7% | 0.9% | 98.9% | 99.3% | 100.0% | 3.0% | 3.8 |

Worst clips for YIN: breathy (yin_app 68.8% with 21% octave errors; tuner 25.7%), quiet (84.1% / 79.5%), snr10 (tuner 80.3%). Per-clip tables are in `results_synth.md`.

## Test 2: real audio, scored as agreement with the RMVPE + SwiftF0 consensus

| model (user's 13 takes, 225 s) | voiced & ±50c | ±20c | octave off | false voiced |
|---|---|---|---|---|
| yin_app | 95.2% | 93.3% | 0.5% | 0.0% |
| yin_tuner | 75.8% | 74.3% | 17.1% (all low) | 0.0% |
| crepe_tiny | 96.7% | 94.3% | 0.3% | 0.2% |
| crepe_full | 97.5% | 95.1% | 0.7% | 0.1% |
| pesto | 96.2% | 87.8% | 0.4% | 0.4% |
| fcpe | 99.5% | 98.4% | 0.4% | 10.2% |

VocalSet (CC BY 4.0, 65 s): yin_app 95.2%, yin_tuner 67.5%, crepe_full 99.2%, pesto 97.8%.

Plots: `plot_1_vibrato.png`, `plot_2_fast.png`, `plot_3_yin.png` (the quiet phrase YIN gates out).

## Speed

| model | CPU ms per s of audio | GPU ms per s |
|---|---|---|
| yin_app (Node) | ~20 | – |
| swiftf0 (native / Chrome WASM) | 8.7 / 21 | – |
| crepe_tiny | 201 | 16 |
| crepe_full | 4279 | 77 |
| pesto | 167 | 2.5 |
| rmvpe | 96 | 6.7 |
| fcpe | 44 | 1.0 |

SwiftF0 lookahead needed for a live tuner: 16 ms gives 99.5%, 32 ms gives 99.9%.

## Browser practicality

* `browser/swiftf0.onnx` (135 KB, MIT) and `browser/index.html` use onnxruntime-web 1.20.1. Verified in Chromium: it matches the Python output.
* Download cost: `ort.min.js` 0.45 MB plus `ort-wasm-simd-threaded.wasm` 11.2 MB. Both can be vendored for offline use.
* Live tuner budget: about 5–8 ms of WASM every 32 ms, in a Worker.

## Integration plan (not done)

1. **Tuner:**
   * Run SwiftF0 in a Worker on 16 kHz audio, newest 14 frames every 32 ms.
   * Voiced = confidence ≥0.5. Drop the RMS gate and the octave snap; keep the display smoothing.
2. **Transcription:**
   * Run SwiftF0 on the whole take and interpolate it onto the 10 ms grid.
   * Fill `m`/`voiced`, keep `db`/`ds`, and leave the HMM unchanged.
3. **No-ML quick fix:** loosen `db > peak-32` in `frames()` (for example −45 dB when aperiodicity is below 0.1), and fix the tuner's absolute gate and octave snap.
