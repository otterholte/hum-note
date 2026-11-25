"""Records a walkthrough video of Humnote Studio from a normal user's point of view.

A hidden, muted Chrome (its own profile, so a fresh song) opens the running app at http://127.0.0.1:8765/ and goes
through the whole flow. Picture: Chrome's screencast frames. Sound: everything the app plays plus the demo "voice"
(a synthetic singer standing in for the microphone), recorded inside the page. ffmpeg joins them into an MP4.
The voice is synthetic test audio; every result on screen is the app's real analysis of it.

usage: python record_demo.py <out.mp4>
"""
import asyncio, base64, json, os, shutil, subprocess, sys, tempfile, time, urllib.request
import websockets

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
import imageio_ffmpeg
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
APP = "http://127.0.0.1:8765/"
W, H = 1366, 800

INIT = r"""
localStorage.setItem('hum2midi_liveN','1');
// the native live-notes engine would play on the real sound card: use the in-page live notes instead (recordable)
const _f=window.fetch; window.fetch=(u,o)=>String(u).includes('api/live')?Promise.resolve(new Response('{"available":false,"on":false}',{headers:{'Content-Type':'application/json'}})):_f(u,o);
// record everything the app plays
const _c=AudioNode.prototype.connect;
AudioNode.prototype.connect=function(t,...a){ const r=_c.call(this,t,...a); if(t instanceof AudioDestinationNode&&t.context instanceof AudioContext){ const ctx=t.context; if(!ctx.__rec) ctx.__rec=ctx.createMediaStreamDestination(); _c.call(this,ctx.__rec,...a); } return r; };
// the demo singer, standing in for the microphone
window.__vc=null;
function __voice(){ if(window.__vc) return window.__vc; const c=new AudioContext(), o=c.createOscillator(), lp=c.createBiquadFilter(), g=c.createGain(), lfo=c.createOscillator(), lg=c.createGain();
  o.type='sawtooth'; lp.frequency.value=1500; lp.Q.value=0.8; g.gain.value=0; lfo.frequency.value=5.2; lg.gain.value=14; lfo.connect(lg); lg.connect(o.detune);
  o.connect(lp); lp.connect(g); o.start(); lfo.start(); const tap=c.createMediaStreamDestination(); g.connect(tap); window.__vc={c,o,g,tap}; return window.__vc; }
navigator.mediaDevices.getUserMedia=async()=>{ const v=__voice(); if(v.c.state!=='running') await v.c.resume(); const d=v.c.createMediaStreamDestination(); v.g.connect(d); d.stream.getAudioTracks().forEach(t=>Object.defineProperty(t,'label',{get:()=>'USB microphone (demo voice)'})); return d.stream; };
"""

DEMO = r"""
window.demo={
  init(){ const c=document.createElement('div'); c.style.cssText='position:fixed;z-index:99999;left:700px;top:430px;width:26px;height:26px;pointer-events:none;transition:left .6s cubic-bezier(.3,.7,.3,1),top .6s cubic-bezier(.3,.7,.3,1);filter:drop-shadow(0 2px 3px rgba(0,0,0,.6))';
    c.innerHTML='<svg viewBox="0 0 24 24" width="26" height="26"><path d="M4 2.5l6.8 18.5 2.6-7.6 7.6-2.6z" fill="#fff" stroke="#111" stroke-width="1.3" stroke-linejoin="round"/></svg>'; document.body.appendChild(c); this.cur=c;
    const k=document.createElement('div'); k.style.cssText='position:fixed;z-index:99998;left:50%;bottom:26px;transform:translateX(-50%);background:rgba(8,9,20,.9);color:#fff;font:600 18px Inter,sans-serif;padding:11px 20px;border-radius:14px;border:1px solid #5b3fb0;max-width:82vw;text-align:center;opacity:0;transition:opacity .35s;box-shadow:0 10px 30px rgba(0,0,0,.5)';
    document.body.appendChild(k); this.cap=k;
    const kb=document.createElement('div'); kb.style.cssText='position:fixed;z-index:99998;right:40px;top:40px;min-width:54px;height:54px;padding:0 12px;border-radius:12px;background:#f1effa;color:#111;font:800 26px Inter;display:flex;align-items:center;justify-content:center;box-shadow:0 5px 0 #8d8fa8,0 12px 30px rgba(0,0,0,.5);opacity:0;transition:opacity .2s,transform .12s'; document.body.appendChild(kb); this.kb=kb; },
  caption(t){ this.cap.textContent=t||''; this.cap.style.opacity=t?1:0; },
  el(s){ const e=typeof s==='string'?document.querySelector(s):s; if(!e) throw new Error('missing '+s); return e; },
  async move(s){ const r=this.el(s).getBoundingClientRect(); this.cur.style.left=(r.left+r.width/2-5)+'px'; this.cur.style.top=(r.top+r.height/2-4)+'px'; await new Promise(z=>setTimeout(z,700)); },
  ripple(e){ const r=e.getBoundingClientRect(), p=document.createElement('div'); p.style.cssText=`position:fixed;z-index:99997;left:${r.left+r.width/2-20}px;top:${r.top+r.height/2-20}px;width:40px;height:40px;border-radius:50%;border:3px solid #c4b5fd;pointer-events:none;transition:transform .45s,opacity .45s`;
    document.body.appendChild(p); setTimeout(()=>{ p.style.transform='scale(1.9)'; p.style.opacity='0'; },20); setTimeout(()=>p.remove(),500); },
  async click(s){ const e=this.el(s); await this.move(e); this.ripple(e); e.click(); await new Promise(z=>setTimeout(z,300)); },
  async dbl(s){ const e=this.el(s); await this.move(e); this.ripple(e); e.dispatchEvent(new MouseEvent('dblclick',{bubbles:true})); await new Promise(z=>setTimeout(z,300)); },
  async waitFor(fn,ms=90000){ const t=performance.now(); while(performance.now()-t<ms){ try{ if(fn()) return true; }catch(e){} await new Promise(z=>setTimeout(z,200)); } return false; },
  async key(k,label){ this.kb.textContent=label||k.toUpperCase(); this.kb.style.opacity=1; this.kb.style.transform='translateY(4px)'; window.dispatchEvent(new KeyboardEvent('keydown',{key:k,bubbles:true}));
    setTimeout(()=>{ this.kb.style.transform=''; },140); setTimeout(()=>{ this.kb.style.opacity=0; },900); await new Promise(z=>setTimeout(z,300)); },
  sing(seq,bpm,delay){ const v=window.__vc, c=v.c; c.resume(); let t=c.currentTime+delay; const b=60/bpm;
    for(const [m,beats] of seq){ if(m){ v.o.frequency.setValueAtTime(440*2**((m-69)/12),t); v.g.gain.setValueAtTime(0,t); v.g.gain.linearRampToValueAtTime(0.32,t+0.03); v.g.gain.setValueAtTime(0.3,t+beats*b-0.09); v.g.gain.linearRampToValueAtTime(0,t+beats*b-0.03); } t+=beats*b; }
    return (t-c.currentTime); },
  async startAudio(){ const ctx=HN.ac(); await ctx.resume(); if(!ctx.__rec) ctx.__rec=ctx.createMediaStreamDestination();
    const v=__voice(); const vs=ctx.createMediaStreamSource(v.tap.stream), vg=ctx.createGain(); vg.gain.value=0.33; vs.connect(vg); vg.connect(ctx.__rec);
    const mr=new MediaRecorder(ctx.__rec.stream,{mimeType:'audio/webm;codecs=opus',audioBitsPerSecond:192000}); this.chunks=[]; mr.ondataavailable=e=>{ if(e.data.size) this.chunks.push(e.data); }; mr.start(250); this.mr=mr; return Date.now()/1000; },
  async stopAudio(){ await new Promise(r=>{ this.mr.onstop=r; this.mr.stop(); }); const b=new Blob(this.chunks,{type:'audio/webm'}); return await new Promise(r=>{ const fr=new FileReader(); fr.onload=()=>r(fr.result.split(',')[1]); fr.readAsDataURL(b); }); }
};
demo.init(); 'ok'
"""


class CDP:
    def __init__(self, ws, framedir):
        self.ws, self.n, self.pend, self.framedir, self.frames = ws, 0, {}, framedir, []

    async def reader(self):
        async for msg in self.ws:
            m = json.loads(msg)
            if "id" in m and m["id"] in self.pend:
                self.pend.pop(m["id"]).set_result(m)
            elif m.get("method") == "Page.screencastFrame":
                p = m["params"]; i = len(self.frames)
                path = os.path.join(self.framedir, f"{i:06d}.jpg")
                with open(path, "wb") as f:
                    f.write(base64.b64decode(p["data"]))
                self.frames.append((p["metadata"]["timestamp"], path))
                await self.send("Page.screencastFrameAck", {"sessionId": p["sessionId"]}, wait=False)

    async def send(self, method, params=None, wait=True):
        self.n += 1; i = self.n
        fut = asyncio.get_event_loop().create_future()
        if wait:
            self.pend[i] = fut
        await self.ws.send(json.dumps({"id": i, "method": method, "params": params or {}}))
        if wait:
            r = await asyncio.wait_for(fut, 200)
            if "error" in r:
                raise RuntimeError(f"{method}: {r['error']}")
            return r.get("result", {})

    async def ev(self, expr):
        r = await self.send("Runtime.evaluate", {"expression": f"(async()=>{{ {expr} }})()", "awaitPromise": True, "returnByValue": True})
        if r.get("exceptionDetails"):
            raise RuntimeError(json.dumps(r["exceptionDetails"])[:400])
        return r.get("result", {}).get("value")


async def walkthrough(cdp):
    S = asyncio.sleep
    d = lambda js: cdp.ev(js)
    cap = lambda t: d(f"demo.caption({json.dumps(t)})")
    await S(2.5)
    await cap("Humnote Studio: a new song, from humming to a full arrangement")
    await S(3)
    await d("await demo.click('#stGo')")
    # tempo
    await cap("Step 1: press T and sing a few seconds at the speed you imagine")
    await S(2.5)
    await d("await demo.key('t')")
    secs = await d("return demo.sing([55,59,62,59,60,57,55,62,59,55,57,59,60,62,59,55].map(m=>[m,1]),96,0.25)")
    await S(secs + 0.5)
    await d("await demo.key('t')")
    await cap("It finds the tempo from your singing")
    await d("await demo.waitFor(()=>!document.getElementById('sTRes').hidden)")
    await S(3)
    await d("await demo.click('#sTPlay')")
    await cap("Play tempo: hear the click to check it")
    await S(3.5)
    await d("await demo.click('#sTPlay')")
    await S(0.8)
    await d("await demo.click('#sTNext')")
    # key
    await cap("Step 2: sing to find the key (or enter chords, or pick it)")
    await S(2.5)
    await d("await demo.click('#sKBtn')")
    secs = await d("return demo.sing([[55,1],[59,1],[62,1],[59,.5],[60,.5],[57,1],[62,1],[67,1.5],[66,.5],[64,1],[62,1],[59,1],[57,1],[55,2]],100,0.25)")
    await S(secs + 0.4)
    await d("await demo.click('#sKBtn')")
    await cap("It suggests the key and plays the scale so you can check by ear")
    await d("await demo.waitFor(()=>document.getElementById('sKRes')&&!document.getElementById('sKRes').hidden)")
    await S(5)
    await d("await demo.move('[data-kt=chords]')")
    await d("await demo.click('[data-kt=chords]')")
    await cap("Know your chords instead? Add them, with a capo if you use one")
    await d("await demo.click('#sChEx')")
    await S(1)
    await d("const s=document.getElementById('sCapo'); await demo.move(s); s.value='2'; s.dispatchEvent(new Event('change')); return 1")
    await S(3.5)
    await d("await demo.click('[data-kt=manual]')")
    await cap("…or just pick the key you already know")
    await S(1)
    await d("await demo.click('[data-mk=\"7\"]')")
    await S(3)
    await d("await demo.click('#sKNext')")
    # instrument
    await cap("Step 3: choose your first instrument")
    await S(2)
    await d("await demo.click('[data-inst=piano]')")
    await S(1)
    await d("await demo.click('#sINext')")
    # record
    await cap("Step 4: record. One bar of count-in, then sing; your notes appear as you go")
    await S(3)
    secs = await d("await demo.click('#sRecBtn'); return demo.sing([[55,1],[59,1],[62,1],[59,1],[60,1],[57,1],[55,2],[62,1],[59,1],[55,1],[57,1],[59,2],[55,2]],96,4*60/96+0.05)")
    await S(secs + 0.6)
    await d("await demo.click('#sRecBtn')")
    await cap("It turns your voice into MIDI notes")
    await d("await demo.waitFor(()=>document.querySelector('.s-view.show')?.dataset.v==='review')")
    await S(2.5)
    # review
    await cap("Step 5: review. Play it back with the piano")
    await d("await demo.click('#sRvPlay')")
    await S(10.5)
    await cap("Quantize: Automatic snaps the notes to the beat")
    await d("await demo.click('[data-q=auto]')")
    await S(3)
    await cap("Edit notes opens the full-screen editor")
    await d("await demo.click('#sRvEdit')")
    await d("await demo.waitFor(()=>document.body.classList.contains('editor-on'))")
    await S(2.5)
    await d("await demo.click('#play')")
    await S(6)
    await d("await demo.click('#play')")
    await cap("Back to your song, nothing lost")
    await d("await demo.click('#edBack')")
    await S(2)
    await d("await demo.click('#sRvNext')")
    # second track
    await cap("Your first track is ready. Add another one")
    await S(2.5)
    await d("await demo.click('#sDAdd')")
    await S(1)
    await d("await demo.click('[data-inst=bass]')")
    await cap("Bass this time: sing the line where it's comfortable, it plays an octave lower")
    await S(2.5)
    await d("await demo.click('#sINext')")
    await S(2.5)
    secs = await d("await demo.click('#sRecBtn'); return demo.sing([[55,2],[55,2],[60,2],[62,2],[55,2],[57,2],[62,2],[55,2]],96,4*60/96+0.05)")
    await cap("Recording the bass line (the click keeps you in time)")
    await S(secs + 0.6)
    await d("await demo.click('#sRecBtn')")
    await d("await demo.waitFor(()=>document.querySelector('.s-view.show')?.dataset.v==='review')")
    await S(3)
    await d("await demo.click('#sRvNext')")
    await S(2)
    await cap("Open the whole song")
    await d("await demo.click('#sDWs')")
    await S(2.5)
    # workspace
    await cap("The song workspace: every track together on one timeline")
    await S(3)
    await d("await demo.click('#wsSecAdd')")
    await d("await demo.click('#wsSecAdd')")
    await cap("Label the parts of your song: intro, verse, chorus…")
    await S(2.5)
    await d("await demo.click('#wsPlay')")
    await cap("Play the whole song: piano and bass together")
    await S(11)
    await d("await demo.click('#wsPlay')")

    await cap("Export: MIDI for your DAW, audio, your voice, or sheet music")
    await d("await demo.click('#wsExport')")
    await S(3)
    await d("await demo.click('#xScore')")
    await cap("Sheet music lives in Export now, printable to PDF")
    await S(5)
    await d("await demo.click('#sMClose')")
    await cap("The AI assistant panel is a preview: coming soon")
    await d("await demo.move('.ws-ai .ask input')")
    await S(3.5)
    await cap("")
    await S(1)


async def main(out):
    work = tempfile.mkdtemp(prefix="humnote_demo_")
    framedir = os.path.join(work, "frames"); os.makedirs(framedir)
    prof = os.path.join(work, "profile")
    port = 9337
    chrome = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={prof}", f"--window-size={W},{H}",
                               "--autoplay-policy=no-user-gesture-required", "--mute-audio", "--hide-scrollbars", "--no-first-run", "--no-default-browser-check", "about:blank"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json").read()); break
            except Exception:
                time.sleep(0.2)
        page = next(t for t in tabs if t["type"] == "page")
        async with websockets.connect(page["webSocketDebuggerUrl"], max_size=2**30) as ws:
            cdp = CDP(ws, framedir); rd = asyncio.create_task(cdp.reader())
            await cdp.send("Page.enable"); await cdp.send("Runtime.enable")
            await cdp.send("Emulation.setDeviceMetricsOverride", {"width": W, "height": H, "deviceScaleFactor": 1, "mobile": False})
            await cdp.send("Page.addScriptToEvaluateOnNewDocument", {"source": INIT})
            await cdp.send("Page.navigate", {"url": APP})
            await asyncio.sleep(4)
            print("page:", await cdp.ev("return document.querySelector('.s-view.show h1')?.textContent"))
            await cdp.ev(DEMO.replace("demo.init(); 'ok'", "demo.init(); return 'ok'"))
            print("AI pitch:", await cdp.ev("await demo.waitFor(()=>/AI pitch on|unavailable/.test(document.getElementById('tDetS')?.textContent||''),60000); return document.getElementById('tDetS')?.textContent"))
            await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 88, "everyNthFrame": 1})
            await asyncio.sleep(0.6)
            t_audio = await cdp.ev("return await demo.startAudio()")
            await walkthrough(cdp)
            b64 = await cdp.ev("return await demo.stopAudio()")
            await cdp.send("Page.stopScreencast")
            await asyncio.sleep(0.5)
            rd.cancel()
        audio = os.path.join(work, "audio.webm")
        with open(audio, "wb") as f:
            f.write(base64.b64decode(b64))
        frames = cdp.frames
        print("frames:", len(frames), "audio bytes:", os.path.getsize(audio))
        # frames arrive when the screen changes: give each its real on-screen time
        lst = os.path.join(work, "frames.txt"); t0 = frames[0][0]
        with open(lst, "w") as f:
            for i, (ts, p) in enumerate(frames):
                dur = (frames[i + 1][0] - ts) if i + 1 < len(frames) else 1.0
                f.write(f"file '{p}'\nduration {max(0.001, dur):.4f}\n")
            f.write(f"file '{frames[-1][1]}'\n")
        off = t_audio - t0
        print("audio starts", round(off, 3), "s after the first frame")
        cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
               "-itsoffset", f"{off:.3f}", "-i", audio,
               "-map", "0:v", "-map", "1:a", "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
               "-c:a", "aac", "-b:a", "192k", "-af", "apad", "-shortest", "-movflags", "+faststart", out]
        subprocess.run(cmd, check=True)
        print("wrote", out)
    finally:
        chrome.terminate()
        try:
            chrome.wait(5)
        except Exception:
            chrome.kill()
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "humnote_walkthrough.mp4"))
