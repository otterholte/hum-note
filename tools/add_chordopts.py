"""Sheet-music chords: choose how often chords change, shift them a beat earlier/later, and an accompaniment style.
Also makes the score's play button say what it plays (cleaned-up or not). Run once on index.html."""
import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "index.html"); s = open(p, encoding="utf-8").read()
def rep(a, b):
    global s; assert s.count(a) == 1, (s.count(a), a[:90]); s = s.replace(a, b)

# ---------- UI ----------
rep('<button type="button" id="scorePlay" title="Plays the notes exactly as written, on the beat, on the piano">▶ Play as written</button>',
    '<button type="button" id="scorePlay" title="Plays the sheet music on the piano, on the beat">▶ Play</button>')
rep('  <p class="status" id="scoreMsg"></p>\n',
    '  <div class="chOpts" id="chOpts" hidden>\n'
    '    <label>Style <select id="chStyle"><option value="held">Held chords</option><option value="oompah">Oom-pah (bass, chord)</option><option value="arp">Arpeggio (flowing)</option><option value="rhythm">Rhythm (bass + offbeats)</option></select></label>\n'
    '    <label>Changes <select id="chRate"><option value="auto">Auto</option><option value="bar">Every bar</option><option value="half">Twice a bar</option><option value="beat">Every beat</option></select></label>\n'
    '    <span class="chShift"><button type="button" id="chEarly" title="All chords one beat earlier">◀</button><span id="chShiftV">on the beat</span><button type="button" id="chLate" title="All chords one beat later">▶</button></span>\n'
    '    <span class="hint">Tap a chord name to hear others and pick one. With “Every beat”, pick a chord at any beat to change there.</span>\n'
    '  </div>\n'
    '  <p class="status" id="scoreMsg"></p>\n')
a = "#scClean[aria-pressed=true],#scChords[aria-pressed=true]"
rep(a, ".chOpts{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;margin:6px 0 4px;font-size:14px;font-weight:600;color:var(--mute)}\n"
       ".chOpts select{font:600 14px Inter,sans-serif;min-height:36px;border-radius:10px;border:1px solid var(--line);background:var(--panel);color:var(--ink);padding:0 8px;margin-left:4px}\n"
       ".chShift{display:inline-flex;align-items:center;gap:6px}.chShift button{min-height:34px;padding:0 10px}.chOpts .hint{flex-basis:100%;font-weight:400;font-size:13px}\n" + a)

# ---------- clean up: say what plays ----------
rep("function stopScore(){ if(scorePb){ scorePb.srcs.forEach(o=>{ try{ o.stop(); }catch(e){} }); clearTimeout(scorePb.to); scorePb=null; } $('scorePlay').textContent='▶ Play as written'; }",
    "const scorePlayLabel=()=>st.scoreClean?'▶ Play cleaned-up':'▶ Play';\n"
    "function stopScore(){ if(scorePb){ scorePb.srcs.forEach(o=>{ try{ o.stop(); }catch(e){} }); clearTimeout(scorePb.to); scorePb=null; } $('scorePlay').textContent=scorePlayLabel(); }")
rep("$('scClean').addEventListener('click',()=>{ st.scoreClean=!st.scoreClean; $('scClean').setAttribute('aria-pressed',st.scoreClean); $('scApply').hidden=!st.scoreClean; stopScore(); drawScore(); });",
    "$('scClean').addEventListener('click',()=>{ st.scoreClean=!st.scoreClean; $('scClean').setAttribute('aria-pressed',st.scoreClean); $('scApply').hidden=!st.scoreClean; stopScore(); drawScore();\n"
    "  toast(st.scoreClean?'Cleaned up: press ▶ Play cleaned-up to hear it (your own notes are untouched)':'Back to your notes as sung'); });")
rep("  st.scoreClean=false; $('scClean').setAttribute('aria-pressed','false'); $('scApply').hidden=true; commit();",
    "  st.scoreClean=false; $('scClean').setAttribute('aria-pressed','false'); $('scApply').hidden=true; stopScore(); commit();")

# ---------- chord timing ----------
rep("""  const segs=[]; for(let b=0;b<bars;b++){ const a=b*barLen; const whole=C.map(c=>fit(c,a,a+barLen)), h1=C.map(c=>fit(c,a,a+half)), h2=C.map(c=>fit(c,a+half,a+barLen));
    const bw=Math.max(...whole), bh=Math.max(...h1)+Math.max(...h2); if(bh/2>bw+1.2&&barLen%2===0) segs.push([a,a+half],[a+half,a+barLen]); else segs.push([a,a+barLen]); }""",
"""  // where chords change: Auto (each bar, or each half bar when the tune clearly asks for it), or a fixed rate;
  // then the whole grid can be shifted by whole beats (a tune that starts before beat 1)
  const rate=st.chRate||'auto', shift=(st.chShift||0)*4; let segs=[];
  for(let b=0;b<bars;b++){ const a=b*barLen;
    if(rate==='bar') segs.push([a,a+barLen]); else if(rate==='half'&&barLen%2===0) segs.push([a,a+half],[a+half,a+barLen]);
    else if(rate==='beat'){ for(let u=a;u<a+barLen;u+=4) segs.push([u,u+4]); }
    else { const whole=C.map(c=>fit(c,a,a+barLen)), h1=C.map(c=>fit(c,a,a+half)), h2=C.map(c=>fit(c,a+half,a+barLen));
      const bw=Math.max(...whole), bh=Math.max(...h1)+Math.max(...h2); if(bh/2>bw+1.2&&barLen%2===0) segs.push([a,a+half],[a+half,a+barLen]); else segs.push([a,a+barLen]); } }
  if(shift){ const cuts=segs.map(x=>x[0]+shift).filter(u=>u>0&&u<end); segs=[0,...cuts].map((u,i,A)=>[u,i+1<A.length?A[i+1]:Math.max(end,u+4)]).filter(x=>x[1]>x[0]); }""")
rep("const v=cost[k]+((move[d.nm]||{})[c.nm]||0)+(k===j?-0.15:0);", "const v=cost[k]+((move[d.nm]||{})[c.nm]||0)+(k===j?(rate==='beat'?0.9:-0.15):0);")
# merge repeats (same chord, not separately chosen) into one longer chord, then voice it in the chosen style
rep("""  const notes=[], names=[]; let prev=null; const top=59;
  path.forEach((ci,i)=>{ const c=C[ci], [a,b]=segs[i];""",
"""  const notes=[], names=[]; let prev=null; const top=59;
  { const ms=[], mp=[]; path.forEach((ci,i)=>{ const L=ms.length-1; if(L>=0&&mp[L]===ci&&forced[i]<0){ ms[L]=[ms[L][0],segs[i][1]]; return; } ms.push([...segs[i]]); mp.push(ci); }); segs=ms; path.splice(0,path.length,...mp); }
  const style=st.chStyle||'held', beatsPerBar=barLen/4;
  const play=(a,b,r,v)=>{ const P=(u0,u1,p,vel)=>{ if(u1>u0) notes.push({u0,u1,p,n:{vel},vib:false,chord:1}); };
    if(style==='held'){ [r,...v].forEach(p=>P(a,b,p,52)); return; }
    if(style==='arp'){ const seq=[r,v[0],v[1],v[2],v[1],v[0]]; let k=0; for(let u=a;u<b;u+=2,k++) P(u,Math.min(b,u+2),seq[k%seq.length],k%seq.length===0?58:48); return; }
    if(style==='oompah'){ for(let u=a;u<b;u+=4){ const beat=Math.round((u%barLen)/4); if(beat===0||(beatsPerBar===4&&beat===2)) P(u,Math.min(b,u+4),beat===0?r:r+7>v[0]?r:r+7,58); else v.forEach(p=>P(u,Math.min(b,u+3),p,44)); } return; }
    // rhythm: bass on the beat, chord on the "and" of 1, on 2-and-a-bit and on 4 (a light pop pattern)
    for(let u=a;u<b;u+=4){ const beat=Math.round((u%barLen)/4); if(beat===0||beat===2) P(u,Math.min(b,u+3),r,58); }
    for(let u=a;u<b;u+=2){ const e8=Math.round((u%barLen)/2); if([1,3,6].includes(e8%8)||(beatsPerBar===3&&[1,3,5].includes(e8))) v.forEach(p=>P(u,Math.min(b,u+2),p,46)); } };
  path.forEach((ci,i)=>{ const c=C[ci], [a,b]=segs[i];""")
rep("    prev=pick; [r,...pick].forEach(p=>notes.push({u0:a,u1:b,p,n:{vel:52},vib:false,chord:1})); });",
    "    prev=pick; play(a,b,r,pick); });")

# ---------- wiring ----------
rep("$('scClean').addEventListener('click',()=>{",
    """{ const CK='hum2midi_chords'; try{ const o=JSON.parse(localStorage.getItem(CK)||'{}'); st.chStyle=o.style||'held'; st.chRate=o.rate||'auto'; st.chShift=0; }catch(e){}
  const save=()=>{ try{ localStorage.setItem(CK,JSON.stringify({style:st.chStyle,rate:st.chRate})); }catch(e){} };
  const shiftLbl=()=>{ const k=st.chShift||0; $('chShiftV').textContent=k?`${Math.abs(k)} beat${Math.abs(k)>1?'s':''} ${k>0?'later':'earlier'}`:'on the beat'; };
  $('chStyle').value=st.chStyle; $('chRate').value=st.chRate; shiftLbl();
  $('chStyle').addEventListener('change',()=>{ st.chStyle=$('chStyle').value; save(); stopScore(); drawScore(); });
  $('chRate').addEventListener('change',()=>{ st.chRate=$('chRate').value; st.chordOver={}; save(); stopScore(); drawScore(); });
  const sh=d=>{ const bpb=st.ts||4; st.chShift=Math.max(-(bpb-1),Math.min(bpb-1,(st.chShift||0)+d)); st.chordOver={}; shiftLbl(); stopScore(); drawScore(); };
  $('chEarly').addEventListener('click',()=>sh(-1)); $('chLate').addEventListener('click',()=>sh(1)); }
$('scClean').addEventListener('click',()=>{""")
rep("  const CH=st.scoreChords?scoreChords(N,barLen):{notes:[],names:[]};", "  $('chOpts').hidden=!st.scoreChords; const CH=st.scoreChords?scoreChords(N,barLen):{notes:[],names:[]};")
open(p, "w", encoding="utf-8").write(s); print("chord options added")
