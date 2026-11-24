// Compares the app's notes on a take to an answer key (the user's corrections). node answer_key.js <dump.json> "<C3 D3 ...>"
const fs=require('fs'); const [,,f,key]=process.argv; const d=JSON.parse(fs.readFileSync(f,'utf8'));
const N=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'], nm=p=>N[p%12]+(Math.floor(p/12)-1);
const got=d.notes.map(n=>nm(n.pitch)), want=key.trim().split(/\s+/);
// edit distance with the alignment
const D=[...Array(got.length+1)].map(()=>Array(want.length+1).fill(0)); for(let i=0;i<=got.length;i++) D[i][0]=i; for(let j=0;j<=want.length;j++) D[0][j]=j;
for(let i=1;i<=got.length;i++) for(let j=1;j<=want.length;j++) D[i][j]=Math.min(D[i-1][j]+1,D[i][j-1]+1,D[i-1][j-1]+(got[i-1]===want[j-1]?0:1));
console.log(`got ${got.length} notes, key ${want.length}; differences: ${D[got.length][want.length]}`); console.log('got: '+got.join(' ')); console.log('key: '+want.join(' '));
