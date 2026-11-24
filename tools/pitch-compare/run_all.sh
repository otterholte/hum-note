#!/usr/bin/env bash
# Re-runs the whole comparison at idle priority (bash, from this folder).
set -e
source "/s/Coding Projects/Halo/ai/env.sh"
PY='S:\Coding Projects\Halo\ai\rvc-venv\Scripts\python.exe'
low(){ cmd //c start "" //low //b //wait "$@"; }
low "$PY" synth.py                                   # synthetic clips with known pitch -> synth/
low node yin_app.js out/synth synth/*.wav            # app's own YIN (transcription + live tuner)
low "$PY" run_models.py out/synth synth/*.wav        # neural models (GPU when available)
low "$PY" eval_synth.py                              # -> results_synth.md/json
cp ../../recordings/*.wav real/ 2>/dev/null || true  # snapshot of the user's takes
low node yin_app.js out/real real/*.wav
low "$PY" run_models.py out/real real/*.wav
low "$PY" prep_vocalset.py
low node yin_app.js out/vocalset vocalset/*.wav
low "$PY" run_models.py out/vocalset vocalset/*.wav
low "$PY" real_compare.py out/real real              # -> agreement_real.md, plot_*.png
low "$PY" real_compare.py out/vocalset vocalset      # -> agreement_vocalset.md
low "$PY" yin_split.py
low "$PY" swift_latency.py
low "$PY" speed.py                                   # CPU timing last
