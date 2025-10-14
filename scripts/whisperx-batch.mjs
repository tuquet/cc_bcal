#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';

function usage(){
  console.log('Usage: node scripts/whisperx-batch.mjs <audioFolder> [--pattern "*.mp3"] [--require-gpu] [--force] [--dry-run] [--parallel N]');
  process.exit(2);
}

const argv = process.argv.slice(2);
if (argv.length === 0) usage();

const audioFolder = argv[0];

const opts = {
  pattern: '*.mp3',
  requireGpu: true,
  force: false,
  dryRun: false,
  parallel: 1,
  scanEpisodes: false,
};

for (let i=1;i<argv.length;i++){
  const a = argv[i];
  if (a==='--pattern' && argv[i+1]) { opts.pattern = argv[i+1]; i++; }
  else if (a==='--require-gpu') opts.requireGpu = true;
  else if (a==='--force') opts.force = true;
  else if (a==='--dry-run') opts.dryRun = true;
  else if (a==='--parallel' && argv[i+1]) { opts.parallel = Math.max(1, parseInt(argv[i+1],10)||1); i++; }
  else if (a==='--scan-episodes') opts.scanEpisodes = true;
  else { console.error('Unknown arg', a); usage(); }
}
const repoRoot = process.cwd();

let audioFolders = [];
if (opts.scanEpisodes) {
  const episodesRoot = path.join(repoRoot, 'episodes');
  if (!fs.existsSync(episodesRoot)) {
    console.error('episodes folder not found:', episodesRoot);
    process.exit(3);
  }
  const eps = fs.readdirSync(episodesRoot).filter(d=> fs.statSync(path.join(episodesRoot,d)).isDirectory());
  for (const e of eps){
    const epFolder = path.join(episodesRoot, e);
    audioFolders.push(epFolder);
  }
  if (audioFolders.length === 0){ console.error('No episode folders found under episodes'); process.exit(4); }
} else {
  const absAudioFolder = path.resolve(repoRoot, audioFolder);
  if (!fs.existsSync(absAudioFolder) || !fs.statSync(absAudioFolder).isDirectory()){
    console.error('Audio folder not found:', absAudioFolder);
    process.exit(3);
  }
  audioFolders.push(absAudioFolder);
}

// collect mp3 files from selected folders
let all = [];
for (const af of audioFolders){
  const files = fs.readdirSync(af).filter(f=> f.toLowerCase().endsWith('.mp3'));
  for (const f of files) all.push({ folder: af, name: f });
}

if (all.length === 0){
  console.error('No mp3 files found in selected folders');
  process.exit(4);
}

console.log(`Found ${all.length} mp3(s) across ${audioFolders.length} folder(s)`);

// Build work list
const work = [];
for (const item of all){
  const fname = item.name;
  const folder = item.folder;
  const mp3 = path.join(folder, fname);
  const base = path.basename(fname, '.mp3');
  const whisperxJson = path.join(folder, base + '.whisperx.json');
  const srt = path.join(folder, base + '.srt'); // Keep for job object
  if (!fs.existsSync(mp3)){
    console.error('Missing mp3 (unexpected):', mp3);
    process.exit(5);
  }
  if (fs.existsSync(whisperxJson) && !opts.force){
    console.log('Skipping (whisperx.json exists):', path.relative(repoRoot, mp3));
    continue;
  }
  work.push({ fname, mp3, base, srt });
}

if (work.length === 0){ console.log('Nothing to do.'); process.exit(0); }

console.log(`Will process ${work.length} file(s) with parallel=${opts.parallel}`);

if (opts.requireGpu && opts.parallel > 1){
  console.warn('Warning: --require-gpu with parallel>1 may overload a single GPU or cause conflicts. Proceed with caution.');
}

// Helper to run one job (returns a Promise that always resolves to a result object)
function runJob(job){
  return new Promise((resolve)=>{
    console.log('Processing', path.relative(repoRoot, job.mp3));
    if (opts.dryRun) return resolve({ ok: true, job, note: 'dry-run' });

  const userProfile = process.env.USERPROFILE || process.env.HOME || '';
  const hostCache = path.join(userProfile, '.cache');
  const containerAudio = '/workspace/' + path.relative(repoRoot, job.mp3).replace(/\\/g, '/');
  // Write whisperx JSON next to the audio file so it's easy to debug and trace.
  const hostTmpJson = path.join(path.dirname(job.mp3), job.base + '.whisperx.json');
  const containerTmpJson = '/workspace/' + path.relative(repoRoot, hostTmpJson).replace(/\\/g, '/');

    const dockerArgs = ['run','--rm'];
    if (opts.requireGpu) dockerArgs.push('--gpus','all');
    dockerArgs.push('-v', `${repoRoot}:/workspace`);
    dockerArgs.push('-v', `${hostCache}:/root/.cache`);
    dockerArgs.push('-e','HF_HOME=/root/.cache/huggingface');
    dockerArgs.push('-e','TRANSFORMERS_CACHE=/root/.cache/huggingface');
    dockerArgs.push('-e','TORCH_HOME=/root/.cache/torch');
    dockerArgs.push('cc_bcal-whisperx');
    dockerArgs.push('--audio', containerAudio, '--output', containerTmpJson);
    if (opts.requireGpu) dockerArgs.push('--require-gpu');

  console.log('DEBUG: docker', dockerArgs.join(' '));
  const proc = spawn('docker', dockerArgs, { stdio: 'inherit' });

    proc.on('error', (err)=> {
      console.error('Docker spawn error for', job.mp3, err && err.message ? err.message : err);
      return resolve({ ok:false, job, err: err && err.message ? err.message : err });
    });
    proc.on('close', (code)=>{
      if (code !== 0) {
        console.error(`Docker exited with code ${code} for ${job.mp3}`);
        return resolve({ ok:false, job, code });
      }
      // convert json -> srt
      if (!fs.existsSync(hostTmpJson)) {
        console.error('Expected json not found for', job.mp3, hostTmpJson);
        return resolve({ ok:false, job, err: 'json missing', expected: hostTmpJson });
      }
      console.log('DEBUG: Converting json -> srt for', hostTmpJson);
      const nodeProc = spawn(process.execPath, ['scripts/write-srt-from-outjson.mjs', hostTmpJson, path.dirname(job.mp3), job.base], { stdio: 'inherit' });
      nodeProc.on('error', (err)=> {
        console.error('Error running write-srt for', hostTmpJson, err && err.message ? err.message : err);
        return resolve({ ok:false, job, err: err && err.message ? err.message : err });
      });
      nodeProc.on('close', (c2)=>{
        if (c2 !== 0) {
          console.error('write-srt exited with code', c2, 'for', hostTmpJson);
          return resolve({ ok:false, job, code: c2 });
        }
        console.log('Completed job for', path.relative(repoRoot, job.mp3));
        // Keep the .whisperx.json next to the audio for debugging/inspection.
        return resolve({ ok:true, job, json: hostTmpJson });
      });
    });
  });
}

async function runPool(){
  const concurrency = Math.max(1, opts.parallel);
  const queue = work.slice();
  const running = [];
  const allPromises = [];

  while (queue.length || running.length){
    while (running.length < concurrency && queue.length){
      const job = queue.shift();
      const p = runJob(job)
        .then(r=>{ running.splice(running.indexOf(p),1); return r; })
        .catch(e=>{ running.splice(running.indexOf(p),1); return { ok:false, job, err: e && e.message ? e.message : e }; });
      running.push(p);
      allPromises.push(p);
    }
    if (running.length) await Promise.race(running);
  }

  // gather results from all started promises and normalize using allSettled to avoid surprises
  const settled = await Promise.allSettled(allPromises);
  const results = settled.map(s => {
    if (s.status === 'fulfilled') return s.value;
    // s.reason may be an object with job info or an Error
    const reason = s.reason;
    if (reason && reason.job) return { ok:false, job: reason.job, err: reason.err || reason.message || String(reason) };
    return { ok:false, job: null, err: reason && (reason.message || reason) ? (reason.message||String(reason)) : 'unknown' };
  });
  return results;
}

function runAlignment(processedEpisodes) {
  return new Promise((resolve, reject) => {
    console.log('\n--- Starting scene alignment step ---');
    const args = ['scripts/align-scenes.mjs'];
    // If we only processed specific episodes, pass them to the alignment script
    if (processedEpisodes.length > 0) {
      args.push(...processedEpisodes);
    }

    const alignProc = spawn('node', args, { stdio: 'inherit' });

    alignProc.on('error', (err) => {
      console.error('Failed to start alignment script:', err);
      reject(err);
    });

    alignProc.on('close', (code) => {
      code === 0 ? resolve() : reject(new Error(`Alignment script exited with code ${code}`));
    });
  });
}
(async ()=>{
  try{
    const res = await runPool();
    // summarize results
    const total = res.length;
    const successes = res.filter(r => r && r.ok === true).length;
    const failures = res.filter(r => !r || r.ok === false).length;
    console.log('\nBatch summary:');
    console.log(`  total: ${total}`);
    console.log(`  success: ${successes}`);
    console.log(`  failed: ${failures}`);
    if (failures > 0) {
      console.log('\nFailed jobs details:');
      for (const r of res){
        if (!r || r.ok === false){
          const name = r && r.job && r.job.mp3 ? path.relative(repoRoot, r.job.mp3) : (r && r.job && r.job.fname ? r.job.fname : '<unknown>');
          const err = r && (r.err || r.error) ? (r.err || r.error) : (r && r.code ? `exit ${r.code}` : JSON.stringify(r));
          console.log(` - ${name}: ${err}`);
        }
      }
      process.exit(1);
    }
    console.log('\nAll transcription jobs finished successfully.');

    // Determine which episodes were processed to pass to the alignment script
    const processedEpisodeNames = opts.scanEpisodes
      ? [...new Set(res.map(r => r.job && path.basename(path.dirname(r.job.mp3))))].filter(Boolean)
      : [];

    await runAlignment(processedEpisodeNames);

    console.log('\n--- Pipeline finished successfully ---');
    process.exit(0);
  }catch(e){
    console.error('\nError during pipeline execution:', e.message || e);
    process.exit(20);
  }
})();
