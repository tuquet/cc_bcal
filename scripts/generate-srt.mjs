import fs from 'fs';
import path from 'path';
import { pad, secToSRT } from './utils.mjs';

function splitIntoSentences(text) {
  return text
    .replace(/\r\n/g, '\n')
    .replace(/\s+/g, ' ')
    .trim()
    .split(/(?<=[.!?…])\s+/);
}

function splitByMaxChars(sentence, maxChars = 84) {
  if (sentence.length <= maxChars) return [sentence];
  const parts = [];
  let cur = sentence.trim();
  while (cur.length > maxChars) {
    let idx = cur.lastIndexOf(' ', maxChars);
    if (idx <= 0) idx = maxChars;
    parts.push(cur.slice(0, idx).trim());
    cur = cur.slice(idx).trim();
  }
  if (cur) parts.push(cur);
  return parts;
}

function segmentsFromText(scene, opts = {}) {
  const charsPerSec = opts.charsPerSec || 12;
  const minDur = opts.minDur || 1.0;
  const maxDur = opts.maxDur || 7.0;
  const sentences = splitIntoSentences(scene.text || '').flatMap(s => splitByMaxChars(s, opts.maxChars || 84));
  const parts = sentences.map(s => {
    const chars = s.replace(/\s+/g, ' ').trim().length;
    const need = Math.max(minDur, Math.min(maxDur, chars / charsPerSec));
    return { text: s, need };
  });

  const available = Math.max(0.001, (scene.end || 0) - (scene.start || 0));
  const needed = parts.reduce((a, b) => a + b.need, 0);
  let factor = 1;
  if (needed > available && needed > 0) factor = available / needed;

  const assigned = [];
  let t = (scene.start || 0) + (opts.lead || 0.15);
  for (const p of parts) {
    let dur = Math.max(minDur, p.need * factor);
    if (t + dur > (scene.end || 0) - (opts.tail || 0.05)) {
      dur = Math.max(0.5, (scene.end || 0) - t - (opts.tail || 0.05));
      if (dur <= 0) break;
    }
    assigned.push({ start: t, end: t + dur, text: p.text });
    t = t + dur + (opts.gap || 0.05);
  }
  return assigned;
}

export function generateSRTFromData(data, opts = {}) {
  // data: { visual_prompts: [ {scene,title,description,visual_style,text,start,end}, ... ] }
  const srtLines = [];
  let index = 1;
  const scenes = (data.visual_prompts || []).sort((a, b) => (a.scene || 0) - (b.scene || 0));
  for (const scene of scenes) {
    const segs = segmentsFromText(scene, opts);
    for (const s of segs) {
      srtLines.push(`${index}`);
      srtLines.push(`${secToSRT(s.start)} --> ${secToSRT(s.end)}`);
      srtLines.push(s.text);
      srtLines.push('');
      index++;
    }
  }
  return srtLines.join('\n').trim();
}

// CLI
if (import.meta.url === `file://${process.argv[1]}`) {
  const argv = process.argv.slice(2);
  if (argv.length < 2) {
    console.error('Usage: node generate-srt.mjs input.json output.srt');
    process.exit(2);
  }
  const [input, out] = argv;
  const data = JSON.parse(fs.readFileSync(input, 'utf8'));
  const srt = generateSRTFromData(data);
  fs.writeFileSync(out, srt, 'utf8');
  console.log(`Wrote ${out}`);
}
