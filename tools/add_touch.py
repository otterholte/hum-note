"""Phone changes (run once on index.html):
 1. takes save inside Humnote (this browser's storage) instead of downloading, when there is no PC helper or folder;
    a MIDI you save on a phone opens the share sheet instead of downloading
 2. a Delete bar appears on the roll whenever notes are selected (no keyboard needed)
 3. touch on the roll: a swipe scrolls through the recording; press-and-hold, then drag, selects (or moves a note);
    a tap jumps there (or selects and plays a note)"""
import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "index.html"); s = open(p, encoding="utf-8").read()
def rep(a, b):
    global s; assert s.count(a) == 1, (s.count(a), a[:90]); s = s.replace(a, b)

# ---------- 1. in-app storage ----------
rep('<span class="status" id="folderS">Not set — new recordings will go to Downloads.</span>',
    '<span class="status" id="folderS">Not set: takes are kept inside Humnote in this browser.</span>')
rep("async function kv(k,v){", """async function kvDel(k){ try{ const db=await idb(); return await new Promise((res,rej)=>{ const r=db.transaction('kv','readwrite').objectStore('kv').delete(k); r.onsuccess=()=>res(); r.onerror=()=>rej(r.error); }); }catch(e){} }
async function kvKeys(){ try{ const db=await idb(); return await new Promise((res,rej)=>{ const r=db.transaction('kv','readonly').objectStore('kv').getAllKeys(); r.onsuccess=()=>res(r.result||[]); r.onerror=()=>rej(r.error); }); }catch(e){ return []; } }
// no PC helper and no folder chosen: takes live inside Humnote (this browser's storage on this device)
const APP=()=>!SERVER&&!dir;
async function kv(k,v){""")
rep("  if(!window.showDirectoryPicker){ $('pick').hidden=true; $('folderS').textContent='This browser can’t write to a folder — takes go to Downloads.'; return; }",
    "  if(!window.showDirectoryPicker){ $('pick').hidden=true; $('folderS').textContent='Takes are kept inside Humnote on this device.'; listTakes(); return; }")
rep("  const h=await kv('dir'); if(h){ dir=h;", "  const h=await kv('dir'); if(!h) listTakes(); if(h){ dir=h;")
rep("  try{ const f=SERVER?await (await fetch('recordings/'+encodeURIComponent(b.dataset.f),{cache:'no-store'})).blob():await (await dir.getFileHandle(b.dataset.f)).getFile();",
    "  try{ const f=SERVER?await (await fetch('recordings/'+encodeURIComponent(b.dataset.f),{cache:'no-store'})).blob():APP()?await kv('f:'+b.dataset.f):await (await dir.getFileHandle(b.dataset.f)).getFile();")
rep("  if(!dir) return; const items=[]; try{ for await",
    "  if(APP()){ const ks=(await kvKeys()).filter(k=>typeof k==='string'&&/^f:.*\\.(wav|m4a|mp3|ogg|webm|aac|flac)$/i.test(k)).map(k=>k.slice(2)); ks.sort().reverse(); showTakes(ks); return; }\n  if(!dir) return; const items=[]; try{ for await")
rep("  const a=document.createElement('a'); a.href=URL.createObjectURL(data instanceof Blob?data:new Blob([data])); a.download=name;",
    """  const blob=data instanceof Blob?data:new Blob([data]);
  if(!/\\.mid$/i.test(name)){ await kv('f:'+name,blob); return 'app'; }
  // a MIDI file on a phone: the share sheet (save to Files, send it…) instead of a download
  try{ const file=new File([blob],name,{type:'audio/midi'}); if(navigator.canShare&&navigator.canShare({files:[file]})&&matchMedia('(pointer:coarse)').matches){ await navigator.share({files:[file],title:name}); return 'shared'; } }catch(e){ if(e&&e.name==='AbortError') return 'shared'; }
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=name;""")
rep("  toast(where==='folder'?`Saved ${curName}.${ext} + notes to “${SERVER?'recordings':dir.name}”`:`Saved ${curName}.${ext} to Downloads — choose a save folder to keep takes together`); listTakes(); }",
    "  toast(where==='folder'?`Saved ${curName}.${ext} + notes to “${SERVER?'recordings':dir.name}”`:`Saved ${curName} in Humnote on this device`); listTakes(); }")
rep("async function loadEdits(){ try{ if(!curName||(!dir&&!SERVER)) return; const txt=SERVER?await (await fetch('recordings/'+encodeURIComponent(curName+'.json'),{cache:'no-store'})).text():",
    "async function loadEdits(){ try{ if(!curName) return; const txt=SERVER?await (await fetch('recordings/'+encodeURIComponent(curName+'.json'),{cache:'no-store'})).text():APP()?await (await kv('f:'+curName+'.json')).text():")
rep("const resave=()=>{ if(curName&&(dir||SERVER))", "const resave=()=>{ if(curName)")
rep("  try{ const where=await writeFile(nm,new Blob([midiBytes()],{type:'audio/midi'})); toast(`Saved ${nm}`+(where==='folder'?` to “${SERVER?'recordings':dir.name}”`:' to Downloads')); }catch(e){ toast('Could not save'); } });",
    "  try{ const where=await writeFile(nm,new Blob([midiBytes()],{type:'audio/midi'})); if(where!=='shared') toast(`Saved ${nm}`+(where==='folder'?` to “${SERVER?'recordings':dir.name}”`:' to Downloads')); }catch(e){ toast('Could not save'); } });")
rep("function showTakeBar(){ const on=!!(curName&&curFile&&(SERVER||dir)&&!(rec&&rec.recording));", "function showTakeBar(){ const on=!!(curName&&curFile&&!(rec&&rec.recording));")
rep("  if(dir&&await ensureDir()){ for await(const [n,h] of dir.entries()){",
    "  if(APP()){ for(const k of await kvKeys()){ if(typeof k!=='string'||!k.startsWith('f:')) continue; const n=k.slice(2); if(only?n===only:n.replace(/\\.[^.]+$/,'')===base) await kvDel(k); } return; }\n  if(dir&&await ensureDir()){ for await(const [n,h] of dir.entries()){")
rep("  if(!confirm(`Delete “${curFile}” and its notes from the recordings folder?\\n\\nThis can't be undone.`)) return;",
    "  if(!confirm(`Delete “${curFile}” and its notes${APP()?' from Humnote':' from the recordings folder'}?\\n\\nThis can't be undone.`)) return;")

# ---------- 2. Delete bar on the roll ----------
rep('    <button type="button" class="fsB" id="fsB" title="Full screen (Esc to leave)">⛶</button>\n',
    '    <button type="button" class="fsB" id="fsB" title="Full screen (Esc to leave)">⛶</button>\n'
    '    <div class="selBar" id="selBar" hidden><span id="selN"></span><button type="button" id="selDel">🗑 Delete</button><button type="button" id="selNone" aria-label="Unselect">✕</button></div>\n')
a = ".fsB{"
rep(a, ".selBar{position:absolute;left:52px;top:28px;z-index:4;display:flex;align-items:center;gap:6px;padding:4px 4px 4px 10px;border-radius:12px;border:1px solid var(--line);background:var(--panel);box-shadow:0 4px 16px rgba(0,0,0,.18);font-size:14px;font-weight:600}\n"
       ".selBar button{min-height:34px;padding:0 12px;font-size:14px;border-radius:9px}.selBar #selDel{background:var(--acc);border-color:var(--acc);color:#fff}\n"
       ".roll #cv{touch-action:none}\n" + a)
rep("function draw(){\n  if(!st.F) return;", "function draw(){\n  if(!st.F) return; updSel();")
rep("const cv=$('cv');\n", """function updSel(){ const n=selSet.size||(st.notes[st.sel]?1:0); $('selBar').hidden=!n; if(n) $('selN').textContent=n===1?'1 note':`${n} notes`; }
function deleteSelected(){ const g=selSet.size?[...selSet]:st.notes[st.sel]?[st.notes[st.sel]]:[]; if(!g.length) return; pushUndo(); const del=new Set(g);
  st.notes=st.notes.filter(n=>!del.has(n)); selSet=new Set(); st.sel=-1; commit(); toast(g.length===1?'Deleted 1 note (Undo brings it back)':`Deleted ${g.length} notes (Undo brings them back)`); }
$('selDel').addEventListener('click',deleteSelected);
$('selNone').addEventListener('click',()=>{ selSet=new Set(); if(st.loop){ st.loop=null; showLoop(); } select(-1); });
const cv=$('cv');
""")

# ---------- 3. touch: swipe scrolls, press-and-hold then drag selects/moves ----------
rep("""cv.addEventListener('pointerdown',e=>{ if(!G||e.button!==0) return; const h=hit(e), on=noteAt(h); cv.setPointerCapture(e.pointerId);
  if(on.i>=0""", """const HOLD_MS=380, PAN_PX=9;
cv.addEventListener('pointerdown',e=>{ if(!G||e.button!==0) return; const h=hit(e), on=noteAt(h); cv.setPointerCapture(e.pointerId);
  if(e.pointerType==='touch'){ const sc=$('sc'); // decide on a swipe (scroll), a tap, or a press-and-hold (select / move)
    drag={mode:'pending',h0:h,on,x0:e.clientX,y0:e.clientY,ly:e.clientY,sl0:sc.scrollLeft,moved:false};
    drag.timer=setTimeout(()=>{ if(!drag||drag.mode!=='pending') return; const t=drag; startDrag(t.h0,t.on,false); drag.cx=t.x0; drag.cy=t.y0; drag.raf=requestAnimationFrame(autoScroll); if(navigator.vibrate) navigator.vibrate(12);
      if(drag.mode==='time') toast('Selecting: drag across the notes'); },HOLD_MS);
    return; }
  startDrag(h,on,e.shiftKey); drag.cx=e.clientX; drag.cy=e.clientY; drag.shift=e.shiftKey; drag.raf=requestAnimationFrame(autoScroll); });
function startDrag(h,on,shift){ const e={shiftKey:shift};
  if(on.i>=0""")
rep("""  else drag={mode:'time',h0:h,moved:false};
  drag.cx=e.clientX; drag.cy=e.clientY; drag.shift=e.shiftKey; drag.raf=requestAnimationFrame(autoScroll); });""",
    """  else drag={mode:'time',h0:h,moved:false}; }""")
rep("cv.addEventListener('pointermove',e=>{ if(drag){",
    """cv.addEventListener('pointermove',e=>{
  if(drag&&drag.mode==='pending'){ if(Math.hypot(e.clientX-drag.x0,e.clientY-drag.y0)>PAN_PX){ clearTimeout(drag.timer); drag.mode='pan'; } else return; }
  if(drag&&drag.mode==='pan'){ $('sc').scrollLeft=drag.sl0-(e.clientX-drag.x0); window.scrollBy(0,drag.ly-e.clientY); drag.ly=e.clientY; return; }
  if(drag){""")
rep("cv.addEventListener('pointerup',e=>{ const d=drag; drag=null; st.guide=null; if(d) cancelAnimationFrame(d.raf); if(!d||!G) return;",
    """cv.addEventListener('pointerup',e=>{ const d=drag; drag=null; st.guide=null; if(d){ cancelAnimationFrame(d.raf); clearTimeout(d.timer); } if(!d||!G) return;
  if(d.mode==='pan') return;
  if(d.mode==='pending'){ if(d.on.i>=0){ if(!selSet.has(st.notes[d.on.i])) clearSel(); select(d.on.i); playOne(d.on.i); } else { clearSel(); select(-1); seek(d.h0.t); } return; }""")
rep("cv.addEventListener('pointercancel',()=>{ if(drag) cancelAnimationFrame(drag.raf);", "cv.addEventListener('pointercancel',()=>{ if(drag){ cancelAnimationFrame(drag.raf); clearTimeout(drag.timer); }")
open(p, "w", encoding="utf-8").write(s); print("touch + storage changes added")
