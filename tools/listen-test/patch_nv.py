"""Adds a sound-colour change curve (nv) to track() and uses it to split same-pitch syllables.
usage: python patch_nv.py <in.html> <out.html> <TH> <DIP>   (TH<=0: compute nv only, no splitting)"""
import sys
src, dst, TH, DIP = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]); VIBX = sys.argv[5] if len(sys.argv)>5 else "1"
s = open(src, encoding="utf-8").read()

old_ret = "    return {f0,ap,db,ds,n,dt:hop/sr,t0:W/2/sr};\n  }"
new_ret = """    return {f0,ap,db,ds,nv:colourChange(x,sr,hop,W,n),n,dt:hop/sr,t0:W/2/sr};
  }
  // How fast the sound's colour (vowel/consonant) changes, frame by frame: log energy in 14 bands
  // (100 Hz - 5 kHz) with loudness removed, compared 60 ms before vs after. Peaks = new syllables,
  // even when the voice doesn't get quieter between them ("row, row, row" sung smoothly).
  function colourChange(x,sr,hop,W,n){
    const N=512, half=N/2, re=new Float64Array(N), im=new Float64Array(N), win=new Float64Array(N); for(let j=0;j<N;j++) win[j]=0.5-0.5*Math.cos(2*Math.PI*j/N);
    const NB=14, mel=f=>2595*Math.log10(1+f/700), imel=m=>700*(10**(m/2595)-1), m0=mel(100), m1=mel(Math.min(5000,sr/2-100));
    const edges=[]; for(let k=0;k<=NB;k++) edges.push(Math.max(1,Math.round(imel(m0+(m1-m0)*k/NB)*N/sr)));
    const B=new Float32Array(n*NB), nv=new Float32Array(n);
    for(let i=0;i<n;i++){ const s=i*hop+((W-N)>>1);
      for(let j=0;j<N;j++){ const v=x[s+j]; re[j]=(v===undefined?0:v)*win[j]; im[j]=0; } fft(re,im);
      let mean=0; for(let k=0;k<NB;k++){ let e=1e-10; for(let b=edges[k];b<Math.max(edges[k]+1,edges[k+1]);b++) e+=re[b]*re[b]+im[b]*im[b]; const l=10*Math.log10(e); B[i*NB+k]=l; mean+=l; }
      mean/=NB; for(let k=0;k<NB;k++) B[i*NB+k]-=mean; }
    const H=6; for(let i=H;i<n-H;i++){ let d=0; for(let k=0;k<NB;k++){ let a=0,b=0; for(let j=1;j<=H;j++){ a+=B[(i-j)*NB+k]; b+=B[(i+j)*NB+k]; } const q=(b-a)/H; d+=q*q; } nv[i]=Math.sqrt(d/NB); }
    return nv; }
  function fft(re,im){ const n=re.length; for(let i=1,j=0;i<n;i++){ let bit=n>>1; for(;j&bit;bit>>=1) j^=bit; j^=bit; if(i<j){ let t=re[i]; re[i]=re[j]; re[j]=t; t=im[i]; im[i]=im[j]; im[j]=t; } }
    for(let len=2;len<=n;len<<=1){ const a=-2*Math.PI/len, wr=Math.cos(a), wi=Math.sin(a); for(let i=0;i<n;i+=len){ let cr=1,ci=0; for(let j=0;j<len/2;j++){ const ur=re[i+j],ui=im[i+j], k=i+j+len/2, vr=re[k]*cr-im[k]*ci, vi=re[k]*ci+im[k]*cr; re[i+j]=ur+vr; im[i+j]=ui+vi; re[k]=ur-vr; im[k]=ui-vi; const t=cr*wr-ci*wi; ci=cr*wi+ci*wr; cr=t; } } } }"""
assert s.count(old_ret) == 1; s = s.replace(old_ret, new_ret)

old_fr = "return {m:ms,mv,vib,voiced,stable,db,ds:tr.ds,peak,n,dt:tr.dt,t0:tr.t0};"
assert s.count(old_fr) == 1; s = s.replace(old_fr, "return {m:ms,mv,vib,voiced,stable,db,ds:tr.ds,nv:tr.nv,peak,n,dt:tr.dt,t0:tr.t0};")

if TH > 0:
    old_sort = "      cuts.sort((x,y)=>x[0]-y[0]);\n      const out=[]; let st=a;"
    new_sort = (f"""      // a change of vowel/consonant on one pitch (a new syllable), with at least a small dip in level
      if(F.nv) for(let i=a+8;i<b-8;i++){{ const v=F.nv[i]; if(v<{TH}*((F.vib&&F.vib[i])?VIBX:1)) continue; let pk=true; for(let q=i-5;q<=i+5;q++) if(F.nv[q]>v){{ pk=false; break; }} if(!pk) continue;
        let L=-99,R=-99,lo=99; for(let q=i-12;q<i-2;q++) if(q>=a) L=Math.max(L,ds[q]); for(let q=i+3;q<=i+12;q++) if(q<b) R=Math.max(R,ds[q]); for(let q=i-3;q<=i+3;q++) lo=Math.min(lo,ds[q]);
        if(lo<Math.min(L,R)-{DIP}&&!cuts.some(c=>Math.abs(c[0]-i)<12)) cuts.push([i,i+1]); }}
""").replace("VIBX",VIBX)
    assert s.count(old_sort) == 1; s = s.replace(old_sort, new_sort + old_sort)
open(dst, "w", encoding="utf-8").write(s); print("wrote", dst)
