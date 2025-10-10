import fs from 'fs';
import path from 'path';
import { spawnSync } from 'child_process';
import { generateSRTFromData } from './generate-srt.mjs';

function runPythonAligner(audioPath) {
  const py = process.env.PYTHON || 'python';
  const script = path.join('scripts', 'whisperx_align.py');
  const args = [script, '--audio', audioPath];
  const res = spawnSync(py, args, { encoding: 'utf8' });
  if (res.error) return { ok: false, error: res.error.message };
  if (res.status !== 0) return { ok: false, error: res.stderr || res.stdout };
  try {
    const parsed = JSON.parse(res.stdout);
    return { ok: true, data: parsed };
  } catch (e) {
    return { ok: false, error: 'Invalid JSON from python aligner' };
  }
}

function writeSRTToEpisode(episodeDir, alias, srtContent) {
  if (!fs.existsSync(episodeDir)) fs.mkdirSync(episodeDir, { recursive: true });
  const outPath = path.join(episodeDir, `${alias}.srt`);
  fs.writeFileSync(outPath, srtContent, 'utf8');
  return outPath;
}

// CLI usage: node generate-srt-from-whisperx.mjs <episodeJsonPath> <episodeDir> [audioPath]
if (import.meta.url === `file://${process.argv[1]}`) {
  const argv = process.argv.slice(2);
  if (argv.length < 2) {
    console.error('Usage: node generate-srt-from-whisperx.mjs episode.json episodes/9.alias [audioPath]');
    process.exit(2);
  }
  const [episodeJson, episodeDir, audioPath] = argv;
  const data = JSON.parse(fs.readFileSync(episodeJson, 'utf8'));
  let srt = null;

  if (audioPath && fs.existsSync(audioPath)) {
    console.log('Attempting python whisperx aligner...');
    const r = runPythonAligner(audioPath);
    if (r.ok && r.data && Array.isArray(r.data.segments) && r.data.segments.length > 0) {
      // Map segments into SRT entries but also clamp to scene start/end
      let index = 1;
      const lines = [];
      for (const seg of r.data.segments) {
        lines.push(String(index));
        lines.push(`${toSRT(seg.start)} --> ${toSRT(seg.end)}`);
        lines.push(seg.text.replace(/\s+/g, ' ').trim());
        lines.push('');
        index++;
      }
      srt = lines.join('\n').trim();
      console.log('Used whisperx output for SRT');
    } else {
      console.log('whisperx aligner failed or returned no segments, falling back to JS algorithm');
    }
  }

  if (!srt) {
    console.log('Generating SRT from visual_prompts using JS fallback...');
    srt = generateSRTFromData(data);
  }

  const alias = data.alias || path.basename(episodeDir);
  const out = writeSRTToEpisode(episodeDir, alias, srt);
  console.log('Wrote srt to', out);
}

function toSRT(sec) {
  const s = Number(sec || 0);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec_i = Math.floor(s % 60);
  const ms = Math.round((s - Math.floor(s)) * 1000).toString().padStart(3, '0');
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(sec_i).padStart(2,'0')},${ms}`;
}
