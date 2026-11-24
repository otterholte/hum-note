"""Adds the voice warm-up to index.html (run once). The JavaScript itself lives in tools/warmup.js."""
import os
HERE = os.path.dirname(os.path.abspath(__file__)); p = os.path.join(HERE, "..", "index.html"); s = open(p, encoding="utf-8").read()
def rep(a, b):
    global s; assert s.count(a) == 1, (s.count(a), a[:90]); s = s.replace(a, b)

# ---------- core: use the warm-up ----------
rep("  function recenter(tune,key){ const c=tune.curve; if(!c.length) return key; let s=0; for(let i=0;i<c.length;i++) s+=c[i]; const mean=s/c.length; const sh=mean>0.5?-1:mean<-0.5?1:0; if(!sh) return key;",
    "  // prior = the singer's usual tuning from their warm-up (semitones; 0 = standard A440)\n  function recenter(tune,key,prior){ const c=tune.curve; if(!c.length) return key; let s=0; for(let i=0;i<c.length;i++) s+=c[i]; const mean=s/c.length-(prior||0); const sh=mean>0.5?-1:mean<-0.5?1:0; if(!sh) return key;")
a = "    // octave slips: a note an octave away from BOTH neighbours, which fits if moved, was a tracker error\n"
rep(a, "    // your range (from the warm-up): a note well outside it that fits an octave away was the tracker locking onto an overtone\n"
       "    if(opt.range){ const [rl,rh]=opt.range; for(const o of kept){ if(o.pitch>rh&&o.pitch-12>=rl){ o.pitch-=12; o.oct=(o.oct||0)-12; } else if(o.pitch<rl&&o.pitch+12<=rh){ o.pitch+=12; o.oct=(o.oct||0)+12; } } }\n" + a)

# ---------- page: detection uses the voice profile ----------
rep("  const F=st.F; const opt={keyStrength:st.key,keyMode:st.key===0?'off':'on',switchCost:st.stick};",
    "  const F=st.F, VP=voiceProfile(); const opt={keyStrength:st.key,keyMode:st.key===0?'off':'on',switchCost:st.stick,...(VP&&VP.low!=null&&VP.high!=null?{range:[VP.low-3,VP.high+3]}:{})};\n"
    "  Hum.HP.veto=VP&&VP.rise!=null&&VP.rise<5.5?Math.max(1.2,0.45*VP.rise):HP0.veto; // gentle syllables -> trust smaller rises")
rep("key=Hum.recenter(tune,k2); notes=Hum.decode(F,tune,key,{...opt,shape:1}); }\n  addVib(notes);",
    "key=Hum.recenter(tune,k2,VP&&VP.offset!=null?VP.offset/100:0); notes=Hum.decode(F,tune,key,{...opt,shape:1}); }\n  addVib(notes);")

# ---------- HTML ----------
rep('  <div class="tuner" id="tuner" hidden>\n', '  <div class="tuner" id="tuner" hidden>\n'
    '    <div class="wu" id="wu" hidden aria-live="polite">\n'
    '      <div class="wuTop"><b id="wuTitle">Warm-up</b><span class="wuDots" id="wuDots"></span></div>\n'
    '      <p class="wuSay" id="wuSay"></p>\n'
    '      <div class="wuBar"><i id="wuBar"></i></div>\n'
    '      <p class="wuHint" id="wuHint"></p>\n'
    '      <ul class="wuRes" id="wuRes" hidden></ul>\n'
    '      <div class="wuBtns"><button type="button" id="wuGo" class="primary" hidden>&#9679; Start recording</button><button type="button" id="wuSkip">Skip</button><button type="button" id="wuAgain" hidden>Do it again</button></div>\n'
    '    </div>\n')
a = '  <button id="listen" type="button" title="Tuner and click on, without recording — find your note first">🎧 Listen</button>'
rep(a, a + '\n  <button id="wuB" type="button" class="q" title="About 15 seconds: Humnote learns your range, your tuning and how you sing syllables">Warm up</button>')

# ---------- CSS ----------
a = "@media(max-width:760px){.recArea{flex-direction:column}.recArea .tuner{flex:none;width:auto}}"
rep(a, a + """
/* warm-up: sits at the top of the tuner panel */
.wu{width:100%;border:1px solid #3a2a1c;background:#16120e;border-radius:14px;padding:12px 14px;margin-bottom:8px}
.wuTop{display:flex;justify-content:space-between;align-items:center;gap:10px;color:#ffd2b0;font-size:15px}
.wuDots{display:flex;gap:5px}.wuDots i{width:9px;height:9px;border-radius:50%;background:#3a3b44}.wuDots i.on{background:var(--neon)}.wuDots i.done{background:var(--good)}
.wuSay{margin:8px 0;font:700 20px/1.25 'Familjen Grotesk',Inter,sans-serif;color:var(--tink)}
.wuBar{height:8px;border-radius:5px;background:#24252c;overflow:hidden}.wuBar i{display:block;height:100%;width:0;background:var(--good);transition:width .12s}
.wuHint{margin:8px 0 0;color:var(--tmute);font-size:14px;min-height:1.4em}
.wuRes{margin:10px 0 0;padding-left:18px;color:var(--tink);font-size:14px;line-height:1.5}.wuRes li{margin:2px 0}.wuRes b{color:#ffd2b0}
.wuBtns{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}.wuBtns button{min-height:36px;font-size:14px;background:#15161b;color:var(--tink);border-color:var(--tline)}
.wuBtns button.primary{background:var(--acc);border-color:var(--acc);color:#fff}
.recArea .wuSay{font-size:16px}.recArea .tuner:has(.wu:not([hidden])){flex-basis:340px;width:340px}
@media(max-width:760px){.recArea .tuner:has(.wu:not([hidden])){width:auto}}""")

# ---------- JS hooks ----------
rep("    if(!R.recording) return; if(R.firstT==null)", "    if(R.wuCap) R.wuCap.push(new Float32Array(d));\n    if(!R.recording) return; if(R.firstT==null)")
rep("  if(guideOn){ if(!r.gd) guideStart(r); guideFollow(r); }\n  drawTrace(r);", "  if(guideOn){ if(!r.gd) guideStart(r); guideFollow(r); }\n  if(WU.on===true) wuTick(r,m,steady,now,dt);\n  drawTrace(r);")
rep("$('rec').addEventListener('click',()=>{ if(rec&&rec.recording) stopRec(false); else startRec(null); });",
    "$('rec').addEventListener('click',()=>{ if(rec&&rec.recording) stopRec(false); else if(WU.on==='done') wuFinish(true); else if(WU.on) return; else if(!voiceProfile()) startWarmup('full'); else if(wuWant()) startWarmup('quick'); else startRec(null); });")
JS = open(os.path.join(HERE, "warmup.js"), encoding="utf-8").read()
rep("run(demoBuffer(),true);\ninitFolder();", JS + "run(demoBuffer(),true);\ninitFolder();")
open(p, "w", encoding="utf-8").write(s); print("warm-up added")
