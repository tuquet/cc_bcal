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

// Settings for splitting (tuned)
const PAUSE_THRESHOLD = 0.6; // seconds between words to consider a pause (was 0.8)
const MAX_SEGMENT_DURATION = 6.0; // max seconds per subtitle
const MAX_WORDS = 10; // max words per subtitle if no timing info (was 12)

function flattenWords(segment){
  // whisperx/whisper outputs may include words timing in different shapes
  // common: segment.words = [{start, end, word}, ...]
  if (segment.words && Array.isArray(segment.words) && segment.words.length>0) return segment.words.map(w=>({start: w.start, end: w.end, word: w.word||w.text||''}));
  // another common pattern: segment.tokens or word_timestamps
  if (segment.alignments && Array.isArray(segment.alignments) && segment.alignments.length>0) return segment.alignments.map(w=>({start: w.start, end: w.end, word: w.text||''}));
  // fallback: no word timings
  return null;
}

function splitSegmentByWords(words){
  const groups = [];
  let current = [];
  for (let i=0;i<words.length;i++){
    const w = words[i];
    if (current.length===0){ current.push(w); continue; }
    const prev = current[current.length-1];
    const gap = w.start - prev.end;
    const curStart = current[0].start;
    const curEnd = w.end;
    const curDur = curEnd - curStart;
    if (gap >= PAUSE_THRESHOLD || current.length >= MAX_WORDS || curDur >= MAX_SEGMENT_DURATION){
      // close current and start new
      groups.push(current);
      current = [w];
    } else {
      current.push(w);
    }
  }
  if (current.length) groups.push(current);
  return groups;
}

function splitSegmentByHeuristics(text, start, end){
  // fallback: split by punctuation or by word count
  const words = (text||'').replace(/\s+/g,' ').trim().split(' ').filter(Boolean);
  if (words.length <= MAX_WORDS) return [{start, end, text: words.join(' ')}];
  const groups = [];
  let i=0;
  while (i<words.length){
    const slice = words.slice(i, i+MAX_WORDS);
    const fracStart = start + (i/words.length) * (end-start);
    const fracEnd = start + ((i+slice.length)/words.length) * (end-start);
    groups.push({start: fracStart, end: fracEnd, text: slice.join(' ')});
    i += MAX_WORDS;
  }
  return groups;
}

const lines = [];
let idx=1;
for(const s of segs){
  const words = flattenWords(s);
  if (words){
    const groups = splitSegmentByWords(words);
    for(const g of groups){
      const tstart = g[0].start;
      const tend = g[g.length-1].end;
      const text = g.map(w=>w.word).join(' ').replace(/\s+/g,' ').trim();
      lines.push(String(idx));
      lines.push(`${toSRT(tstart)} --> ${toSRT(tend)}`);
      lines.push(text);
      lines.push('');
      idx++;
    }
  } else {
    // no word timings; attempt to split by heuristics if segment long
    const dur = (s.end||0) - (s.start||0);
    if (dur>MAX_SEGMENT_DURATION){
      const parts = splitSegmentByHeuristics(s.text||'', s.start||0, s.end||0);
      for(const p of parts){
        lines.push(String(idx));
        lines.push(`${toSRT(p.start)} --> ${toSRT(p.end)}`);
        lines.push((p.text||'').replace(/\s+/g,' ').trim());
        lines.push('');
        idx++;
      }
    } else {
      lines.push(String(idx));
      lines.push(`${toSRT(s.start)} --> ${toSRT(s.end)}`);
      lines.push((s.text||'').replace(/\s+/g,' ').trim());
      lines.push('');
      idx++;
    }
  }
}
const srt = lines.join('\n').trim();
if(!fs.existsSync(epDir)) fs.mkdirSync(epDir,{recursive:true});
const outPath = path.join(epDir, `${alias}.srt`);
fs.writeFileSync(outPath,srt,'utf8');
console.log('Wrote SRT to', outPath, 'with', idx-1, 'segments');
