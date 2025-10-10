#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { spawnSync } from 'child_process';

function usage(){
  console.log('Usage: node scripts/whisperx-batch.mjs <audioFolder> [--pattern "*.mp3"] [--require-gpu] [--force] [--dry-run] [--parallel N]');
  process.exit(2);
}

const argv = process.argv.slice(2);
if (argv.length === 0) usage();

const audioFolder = argv[0];
const opts = {
  pattern: '*.mp3',
  requireGpu: false,
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
    const aud = path.join(episodesRoot, e, 'audio');
    if (fs.existsSync(aud) && fs.statSync(aud).isDirectory()) audioFolders.push(aud);
  }
  if (audioFolders.length === 0){ console.error('No episode audio folders found under episodes/*/audio'); process.exit(4); }
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
  const srt = path.join(folder, base + '.srt');
  if (!fs.existsSync(mp3)){
    console.error('Missing mp3 (unexpected):', mp3);
    process.exit(5);
  }
  if (fs.existsSync(srt) && !opts.force){
    console.log('Skipping (srt exists):', path.relative(repoRoot, mp3));
    continue;
  }
  work.push({ fname, mp3, base, srt });
}

if (work.length === 0){ console.log('Nothing to do.'); process.exit(0); }

console.log(`Will process ${work.length} file(s) with parallel=${opts.parallel}`);

if (opts.requireGpu && opts.parallel > 1){
  console.warn('Warning: --require-gpu with parallel>1 may overload a single GPU or cause conflicts. Proceed with caution.');
}

// Helper to run one job (returns a Promise)
function runJob(job){
  return new Promise((resolve, reject)=>{
    console.log('Processing', job.fname);
    if (opts.dryRun) return resolve({ ok: true, job });

    const userProfile = process.env.USERPROFILE || process.env.HOME || '';
    const hostCache = path.join(userProfile, '.cache');
    const containerAudio = '/workspace/' + path.relative(repoRoot, job.mp3).replace(/\\/g, '/');
    const tmpJson = '/workspace/.out-whisperx-' + job.base + '.json';

    const dockerArgs = ['run','--rm'];
    if (opts.requireGpu) dockerArgs.push('--gpus','all');
    dockerArgs.push('-v', `${repoRoot}:/workspace`);
    dockerArgs.push('-v', `${hostCache}:/root/.cache`);
    dockerArgs.push('-e','HF_HOME=/root/.cache/huggingface');
    dockerArgs.push('-e','TRANSFORMERS_CACHE=/root/.cache/huggingface');
    dockerArgs.push('-e','TORCH_HOME=/root/.cache/torch');
    dockerArgs.push('cc_bcal-whisperx');
    dockerArgs.push('--audio', containerAudio, '--output', tmpJson);
    if (opts.requireGpu) dockerArgs.push('--require-gpu');

    const spawn = require('child_process').spawn;
    const proc = spawn('docker', dockerArgs, { stdio: 'inherit' });
    proc.on('error', (err)=> reject({ ok:false, job, err }));
    proc.on('close', (code)=>{
      if (code !== 0) return reject({ ok:false, job, code });
      // convert json -> srt
      const hostTmpJson = path.join(repoRoot, '.out-whisperx-' + job.base + '.json');
      if (!fs.existsSync(hostTmpJson)) return reject({ ok:false, job, err: new Error('json missing') });
      const nodeProc = spawn(process.execPath, ['scripts/write-srt-from-outjson.mjs', hostTmpJson, path.dirname(job.mp3), job.base], { stdio: 'inherit' });
      nodeProc.on('error', (err)=> reject({ ok:false, job, err }));
      nodeProc.on('close', (c2)=>{
        // cleanup
        try { fs.unlinkSync(hostTmpJson); } catch(e){}
        if (c2 !== 0) return reject({ ok:false, job, code: c2 });
        resolve({ ok:true, job });
      });
    });
  });
}

async function runPool(){
  const concurrency = Math.max(1, opts.parallel);
  const queue = work.slice();
  const running = [];
  while (queue.length || running.length){
    while (running.length < concurrency && queue.length){
      const job = queue.shift();
      const p = runJob(job).then(r=>{ running.splice(running.indexOf(p),1); return r; }).catch(e=>{ running.splice(running.indexOf(p),1); return e; });
      running.push(p);
    }
    // wait any
    await Promise.race(running);
  }
  // gather results
  const results = await Promise.all(running.map(p => p.catch(e=>e)).concat([]));
  return results;
}

(async ()=>{
  try{
    const res = await runPool();
    console.log('All jobs finished');
    process.exit(0);
  }catch(e){
    console.error('Error during processing', e);
    process.exit(20);
  }
})();

