# How Humnote's note detection is tested and tuned

Everything here runs locally. The audio test sets are downloaded by scripts and never committed: several are
licensed for non-commercial research only. Only the note answer keys (`<set>/index.json`) are in git.

## Test sets

| Set | What it is | Notes known how | Use |
|---|---|---|---|
| `bench` | 38 VocalSet singers, "Row, Row, Row Your Boat", straight + vibrato (CC BY 4.0) | melody only, no timings | tune |
| `clips` | 4 synthetic tunes + 4 VocalSet clips (listening tests) | melody | tune |
| `ht` / `htx` | 40 + 40 hummed clips from HumTrans (CC BY-NC 4.0) | MIDI (timings are known to be off) | tune / held back |
| `csd` / `csdx` | 25 + 25 English children's songs, one pro singer, CSD (CC BY-NC-SA 4.0) | exact note + syllable timings | tune / held back |
| `voc` / `vocx` | 20 + 20 solo singers in 7 languages, vocadito (CC BY 4.0) | exact notes from two annotators | tune / held back |
| your take | `recordings/hum_2026-11-24_015826.wav` with your corrected notes | answer key | check |

The two vocadito annotators agree on only **73%** of notes with each other. Fast passing notes and scoops are
genuinely ambiguous, so 100% is not a meaningful target on every set.

## Building the sets

```
python make_clips.py            # bench / clips (VocalSet + synthetic)
python make_humtrans.py 40      # ht, htx   (pulls only the chosen clips out of the 14.7 GB zip)
python make_csd.py              # csd, csdx (20 s from each song)
python make_vocadito.py         # voc, vocx (needs vocadito_src/ unzipped from zenodo.org/records/5578807)
python swift_tracks.py <set>    # AI pitch tracks the app also computes in the browser
```

## Scoring

- `bash try_all.sh <app.html> vib`: bench + clips + your take.
- `bash run_ht.sh <set> <app.html> vib`: any fully labelled set. It reports notes right (edit distance, best
  transposition), note F1 (pitch right and start within 100 ms) and onset F1.
- `node error_types.js <set>` / `node err_detail.js <set> [clip]`: what kind of mistakes, and where.

## Learning from the data (the result is plain code in the app, no AI needed to run it)

- `learn_splits.py`, `learn_veto.py`: decision trees on every candidate split point. Result: a real new syllable
  on the same pitch comes back about 2.5 dB louder after the split. This rule is in the app.
- `learn_onsets.py`, `export_onsets.py`: a 56-weight note-start detector (logistic regression on 13 frames of
  voicing / loudness / sound colour / vibrato + pitch change + level rise and fall). `add_onsets.py` writes it into the app.
- `tune.js`: loads every clip once, then searches the app's note settings (`Hum.HP`) for the best average over
  the tuning sets. It reports the held-back sets so overfitting shows.
