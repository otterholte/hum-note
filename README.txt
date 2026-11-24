Humnote (Hum to MIDI)

Open it like any program: Start menu or Desktop > "Hum to MIDI" (or double-click "Hum to MIDI.pyw" here).
It opens in its own window. Closing the window shuts everything down.

- Every take saves straight into the "recordings" folder (wav + json of the notes). Nothing goes to Downloads.
- The first time, it asks for the microphone once: choose "Allow while visiting the site". The app window remembers it.
- "Microphone" (under Record) picks the input, e.g. "Analogue 1 + 2 (Focusrite USB Audio)". The green bar next to it
  is a live level meter: it should jump when you sing. The choice is remembered.
- "Hear myself while recording" (next to Record) plays your mic into your headphones with about 20 ms delay.
  It is only on while recording. Wired headphones only. Zero delay = Direct Monitor on the Focusrite itself.

Files: index.html (the app), server.py (saving + hear-myself helper), Hum to MIDI.pyw (opens the window),
icon.*, tools\ (scripts Claude uses to check takes: node tools/run.js recordings/<take>.wav).

Tuner (while recording): dark, neon orange. Big note name, arc meter, and a label: In tune (within 10 cents),
  A little sharp / flat (10-25), Sharp / Flat. The needle only moves while you hold a note, so fast runs don't
  make it swing; the glowing wave at the bottom just shows the mic is hearing you.
Tempo + quantize: the Tempo bar shows the BPM it found (fix with - + 1/2x 2x). Pick a grid (1/4, 1/8, 1/16,
  triplets). Quantize pulls notes toward the grid by the Humanize amount - drag the lever right after to adjust
  live; Snap exactly puts them right on it. Undo / Ctrl+Z goes back. With a loop set, only that part is quantized.
Vibrato: a wavy line on a note = vibrato it found (4+ evenly spaced turns, 4-9 a second). "Keep" plays it back
  and writes it into the MIDI as pitch bend. Subtle / Normal / Wide only = how big a swing counts. V toggles it
  on the selected note.
Copy: Shift + drag a note to drop a copy (with its vibrato) anywhere - quick harmonies. Ctrl+C / Ctrl+V copies the
  selected note to the playhead.
Sheet music: under the piano roll, a grand staff (treble from middle C up, bass below) in the key it heard,
  4/4 or 3/4, redrawn after every change.

Humnote update:
- Open it from the "Humnote" icon on the Desktop or Start menu. Right-click its taskbar icon > Pin to taskbar:
  it pins as Humnote with its own icon (taskbar_id.py gives the window its own identity instead of Chrome's).
- Listen: tuner + click on before recording, to find your note. Record keeps it going.
- Setup (top right): microphone, MIDI keyboard (plays as piano in your headphones), save folder. Theme: Auto / Dark / Light.
- Cut a part out: drag across it in the roll, then "Cut this part out" (sound + notes). Shift+Delete on a note does the same for that note.
- Roll: Ctrl + scroll zooms the timeline only (box stays the same size); the full-screen button fills the screen.
- Sheet music: "Play as written" plays it on the beat; wavy lines above notes = vibrato.

Later update:
- Notes: judged against your own tuning more like a listener: in-between notes lean into the key, a note that holds two
  pitches becomes two notes, quick real notes aren't swallowed by the note next to them.
- Tuner: switches notes quicker, no octave-low slips on low notes; the click stops when you stop recording.
- Piano: real upright piano samples (VCSL "Upright Piano, Knight", Ivy Audio, CC0 - see piano/CREDITS.txt) for
  Play as written, the MIDI keyboard and the "Piano" playback sound.
- Roll: drag across part of it to select every note there (the view slides if you drag past the edge). Then
  Delete, Shift+Delete (cut with the sound), Ctrl+C / Ctrl+V, arrow keys, or drag (Shift+drag = copy) them together.
  The timeline shows bar numbers; seconds are the small grey marks.
- Sheet music: Clean up (tidy timing, drop slips, stray notes into the key), octave down/up (into treble), Chords
  (chords that fit the whole tune, in the bass clef). These change only the sheet music. More > Save sheet music as MIDI.
- Pitch model comparison: tools/pitch-compare/REPORT.md.

- Follow my drift (Detection settings, on): if you slowly go sharp/flat or start a phrase a little off, notes are read
  in the key relative to where your voice has drifted, and the key is chosen to fit how the take starts.
- Tuner pitch: AI (SwiftF0, MIT - models/swiftf0.onnx, runtime vendor/ort = onnxruntime-web 1.20.1, MIT) or Classic,
  under Tuner settings > Pitch detector. Falls back to Classic if the model can't load.
- Sheet music: click a chord name to pick a different chord there (the rest re-fit around it); "Apply to my notes"
  (with Clean up on) makes the cleaned-up notes your real notes.
- A take recorded with the click keeps that exact tempo when you reopen it.
- tools/render/render_piano.py renders note lists with the piano to MP3 (demo-audio/).
