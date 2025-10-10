import fs from 'fs';
import path from 'path';

function toSRT(sec){
  const s = Number(sec||0);
  const h = Math.floor(s/3600);
  const m = Math.floor((s%3600)/60);
  const sec_i = Math.floor(s%60);
  const ms = Math.round((s - Math.floor(s))*1000).toString().padStart(3,'0');
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(sec_i).padStart(2,'0')},${ms}`;
}

const out = process.argv[2] || 'out-whisperx.json';
const epDir = process.argv[3] || 'episodes/1.tam-nhu-mat-ho';
const alias = process.argv[4] || path.basename(epDir);

if(!fs.existsSync(out)){
  console.error('Missing', out);
  process.exit(2);
}
const data = JSON.parse(fs.readFileSync(out,'utf8'));
const segs = data.segments || [];
const lines = [];
let idx=1;
for(const s of segs){
  lines.push(String(idx));
  lines.push(`${toSRT(s.start)} --> ${toSRT(s.end)}`);
  lines.push((s.text||'').replace(/\s+/g,' ').trim());
  lines.push('');
  idx++;
}
const srt = lines.join('\n').trim();
if(!fs.existsSync(epDir)) fs.mkdirSync(epDir,{recursive:true});
const outPath = path.join(epDir, `${alias}.srt`);
fs.writeFileSync(outPath,srt,'utf8');
console.log('Wrote SRT to', outPath, 'with', segs.length, 'segments');
