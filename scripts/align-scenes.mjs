import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';

const episodesDir = 'episodes';

/**
 * Normalizes and splits text into words.
 * @param {string} text - The text to process.
 * @returns {string[]} An array of words.
 */
const getWords = (text) => {
  if (!text) return [];
  return text
    .toLowerCase()
    .replace(/[.,':?"“'”]/g, '') // Expanded punctuation removal
    .trim()
    .split(/\s+/);
};

/**
 * Calculates the similarity between two arrays of words.
 * @param {string[]} arr1
 * @param {string[]} arr2
 * @returns {number} A similarity score between 0 and 1.
 */
function calculateSimilarity(arr1, arr2) {
  const set1 = new Set(arr1);
  const intersection = arr2.filter(word => set1.has(word));
  const union = new Set([...arr1, ...arr2]);
  return intersection.length / union.size; // Jaccard similarity for better accuracy
}

/**
 * Finds the best matching block of segments for a given narration.
 * @param {string} narration - The full narration text for a scene.
 * @param {Array<object>} segments - The array of transcribed segments.
 * @returns {{start: number|null, end: number|null}}
 */
function findSceneTimes(narration, segments) {
  const narrationWords = getWords(narration);
  if (narrationWords.length === 0) return { start: null, end: null };

  let bestMatch = { start: null, end: null, score: 0 };

  for (let i = 0; i < segments.length; i++) {
    for (let j = i; j < segments.length; j++) {
      const candidateSegments = segments.slice(i, j + 1);
      const candidateWords = candidateSegments.flatMap(s => getWords(s.text));

      if (candidateWords.length === 0) continue;

      const score = calculateSimilarity(narrationWords, candidateWords);
      const lengthRatio = Math.min(narrationWords.length, candidateWords.length) / Math.max(narrationWords.length, candidateWords.length);
      const finalScore = score * lengthRatio;

      if (finalScore > bestMatch.score) {
        bestMatch = {
          start: candidateSegments[0].start,
          end: candidateSegments[candidateSegments.length - 1].end,
          score: finalScore,
        };
      }
    }
  }

  return bestMatch.score > 0.5 ? { start: bestMatch.start, end: bestMatch.end } : { start: null, end: null };
}

/**
 * Processes a single episode directory.
 * @param {string} episodeDirName - The name of the episode directory (e.g., "11.la-rung-vo-thuong").
 */
function processEpisode(episodeDirName) {
  try {
    console.log(`\nAligning scenes for episode: ${episodeDirName}`);
    const episodePath = path.join(episodesDir, episodeDirName);
    const audioPath = path.join(episodePath, 'audio.mp3');
    const scriptJsonPath = path.join(episodePath, 'capcut-api.json');

    // The whisperx file is in the same directory as script.json
    if (!fs.existsSync(scriptJsonPath)) {
      console.error(`  -> Error: Missing script.json in ${episodePath}`);
      return;
    }

    if (!fs.existsSync(audioPath)) {
      console.error(`  -> Error: Missing audio.mp3 in ${episodePath}`);
      return;
    }

    // Find the whisperx file in the episode's main directory
    const whisperFile = fs.readdirSync(episodePath).find(f => f.endsWith('.whisperx.json'));
    if (!whisperFile) {
      console.error(`  -> Error: No .whisperx.json file found in ${episodePath}`);
      return;
    }

    const whisperPath = path.join(episodePath, whisperFile);
    const scriptData = JSON.parse(fs.readFileSync(scriptJsonPath, 'utf8'));
    const segments = JSON.parse(fs.readFileSync(whisperPath, 'utf8')).segments;

    // KIỂM TRA: Nếu các scene đã có timing, bỏ qua file này
    const hasExistingTimings = scriptData.scenes?.every(
      (scene) =>
        typeof scene.start === "number" && typeof scene.end === "number"
    );

    if (hasExistingTimings) {
      console.log(
        `-> Skipping: File already has timing information for all scenes.`
      );
      return;
    }

    let nullCount = 0;
    scriptData.scenes.forEach((scene, index) => {
      const times = findSceneTimes(scene.narration, segments);
      scene.start = times.start;
      scene.end = times.end;

      if (times.start === null || times.end === null) {
        nullCount++;
      }
      // Add absolute image path for each scene
      const imageFileName = `${index + 1}.png`;
      scene.image = path.resolve(episodePath, imageFileName);
    });

    // Also update the total duration
    // const endTimes = scriptData.scenes.map(s => s.end).filter(t => typeof t === 'number');
    // const totalDuration = endTimes.length > 0 ? Math.max(...endTimes) : 0;
    // scriptData.duration = totalDuration;

    // Get actual audio duration using ffprobe
    try {
      const command = `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${audioPath}"`;
      const duration = parseFloat(execSync(command).toString().trim());
      scriptData.duration = duration;
    } catch (ffprobeError) {
      console.warn(`-> Warning: Could not get audio duration with ffprobe. Is FFmpeg installed and in PATH? Error: ${ffprobeError.message}`);
    }

    fs.writeFileSync(scriptJsonPath, JSON.stringify(scriptData, null, 2), 'utf8');
    console.log(`-> Successfully aligned and updated: ${path.relative(process.cwd(), scriptJsonPath)}`);
    const folderUrl = `file://${path.resolve(path.dirname(scriptJsonPath)).replace(/\\/g, '/')}`;
    console.log(`📂 Open folder: ${folderUrl}`);
    if (nullCount > 0) {
      console.warn(`-> Warning: ${nullCount} scene(s) could not be aligned and were set to null.`);
    }
  } catch (error) {
    console.error(`-> Failed to process ${episodeDirName}:`, error.message);
  }
}

// Main execution logic
const targetEpisode = process.argv[2];

if (targetEpisode) {
  // Process a single specified episode
  processEpisode(targetEpisode);
} else {
  // Process all episodes
  console.log('--- Starting alignment for all episodes ---');
  const allEpisodes = fs.readdirSync(episodesDir, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory())
    .map(dirent => dirent.name);
  allEpisodes.forEach(processEpisode);
  console.log('\n--- Alignment complete ---');
}