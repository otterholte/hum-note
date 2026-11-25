# Humnote Studio — the guided songwriting layer

`studio.js` + `studio.css` sit on top of the existing app (`index.html`). They add the guided walkthrough, the multi-track
song workspace and the export menu. All audio work is the existing engine, reached through `window.HN` (a small bridge at
the end of the main script). Nothing in the studio analyses audio by itself.

## What each screen reuses

| Screen | Existing functionality used |
|---|---|
| 1 Start | — |
| 2 Tempo | mic capture (`openLive`, `wuCap`), transcription (`analyze` + `Hum.decode`), `Hum.tempo` + `Hum.meter` (beat speed, 3/4 vs 4/4); metronome (`startMetro`) for “Play tempo” |
| 3 Key — sing | same capture + `rankKeys` (key finder fitted on folk tunes), `playScale` |
| 3 Key — chords | new: chord list, capo transposition, key-from-chords scoring; piano samples to hear them |
| 3 Key — manual | `setKey` (also locks live notes to the key) |
| 4 Instrument | maps to a playback sound (`tone`, new voices: guitar, electric, bass, synth, strings, drums) and a live-notes sound |
| 5 Record | `startRec` / `stopRec` (recording, saving the take to `recordings/`, full transcription), count-in + click (`startMetro`, aligned through the click’s own timing), live notes (native engine), live note view (`lrTick` drawing into the studio canvas) |
| 6 Review | `Hum.quantize` (Automatic picks 1/8, 1/16 or triplets from how the notes sit), per-track undo, instrument change |
| Editor | the existing note editor, loaded with the track (`st.buf`, `st.F`, notes, song tempo/key); velocity slider added to the selection bar |
| Workspace | new: tracks timeline, mute / solo / volume, sections (duplicate and move carry the notes), song playback through `tone` |
| Export | new multi-track MIDI writer; audio via `OfflineAudioContext` + `tone`; original voice WAV; sheet music = the existing score, shown in its own window and printable to PDF |

The project (tempo, key, chords, capo, instrument, tracks, notes, sections) is saved in IndexedDB after every change
(`studio:project`); each track’s recording is saved alongside it (`studio:audio:<id>`) and also as a take in `recordings/`.

Track notes are stored in recording time; `offset` = where bar 1 of the song falls in that recording (from the count-in click).

## Developer mode

Add `?dev` to the address (or press **Ctrl+Shift+D**). The DEV button bottom-left can:
jump to any step, reset the current step or the whole walkthrough, load a sample song (the built-in test voice really
analysed + a generated bass line and drum beat), run the real analysis of the test voice as a new track, and fill in a
simulated tempo / key or example chords. Test and simulated data are always labelled TEST / SIMULATED on screen.

Settings (⚙ in the workspace) holds the microphone choice, live-note settings and a link to the classic full view.
