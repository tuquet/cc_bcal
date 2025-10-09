#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';
import ffmpegStatic from 'ffmpeg-static';

class VideoGenerator {
  constructor() {
    this.ffmpegPath = ffmpegStatic;
    this.projectRoot = process.cwd();
  }

  // Tạo video test đơn giản
  async generateTestVideo(episodeNumber) {
    const episodeDir = this.getEpisodeDir(episodeNumber);
    if (!episodeDir) return;

    console.log(`🧪 Tạo video test cho ${path.basename(episodeDir)}...`);
    
    const audioPath = path.join(episodeDir, 'audio', 'voiceover.mp3');
    const imagePath = path.join(episodeDir, 'images', '1.png');
    const outputPath = path.join(episodeDir, 'output', 'test.mp4');

    if (!fs.existsSync(audioPath)) {
      console.log(`❌ Không tìm thấy: ${audioPath}`);
      return;
    }

    if (!fs.existsSync(imagePath)) {
      console.log(`❌ Không tìm thấy: ${imagePath}`);
      return;
    }

    const command = `"${this.ffmpegPath}" -y -i "${audioPath}" -i "${imagePath}" -c:v libx264 -c:a aac -shortest "${outputPath}"`;
    
    try {
      execSync(command, { stdio: 'inherit' });
      console.log(`✅ Video test đã tạo: ${outputPath}`);
    } catch (error) {
      console.log(`❌ Lỗi tạo video test: ${error.message}`);
    }
  }

  // Tạo video final với Ken Burns effects
  async generateFinalVideo(episodeNumber) {
    const episodeDir = this.getEpisodeDir(episodeNumber);
    if (!episodeDir) return;

    const timingPath = path.join(episodeDir, 'timing.json');
    if (!fs.existsSync(timingPath)) {
      console.log(`❌ Không tìm thấy timing.json trong ${episodeDir}`);
      console.log(`💡 Chạy: node prepare-episode.mjs ${episodeNumber} trước`);
      return;
    }

    const timing = JSON.parse(fs.readFileSync(timingPath, 'utf8'));
    console.log(`🎬 Tạo video final cho ${path.basename(episodeDir)}...`);

    // Build FFmpeg command
    const { inputs, filterComplex } = this.buildFFmpegCommand(episodeDir, timing);
    const outputPath = path.join(episodeDir, 'output', 'final.mp4');

    const command = `"${this.ffmpegPath}" -y ${inputs}-filter_complex "${filterComplex}" -map "[outv]" -map 0:a -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 128k -shortest "${outputPath}"`;

    try {
      execSync(command, { stdio: 'inherit' });
      console.log(`✅ Video final đã tạo: ${outputPath}`);
    } catch (error) {
      console.log(`❌ Lỗi tạo video final: ${error.message}`);
    }
  }

  // Build FFmpeg command components
  buildFFmpegCommand(episodeDir, timing) {
    let inputs = '';
    let filterComplex = '';

    // Input audio
    const audioPath = path.join(episodeDir, 'audio', 'voiceover.mp3');
    inputs += `-i "${audioPath}" `;

    // Input images
    for (let i = 1; i <= 5; i++) {
      const imagePath = path.join(episodeDir, 'images', `${i}.png`);
      inputs += `-i "${imagePath}" `;
    }

    // Tạo video segments cho mỗi scene
    timing.scenes.forEach((scene, index) => {
      const duration = scene.duration;
      const imageIndex = index + 1; // Images bắt đầu từ input [1]
      
      filterComplex += `[${imageIndex}]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,`;
      filterComplex += `zoompan=z='min(zoom+0.0015,1.5)':d=${duration * 30}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080[v${index}]; `;
    });

    // Concat video segments
    let concatInputs = '';
    timing.scenes.forEach((scene, index) => {
      concatInputs += `[v${index}]`;
    });
    filterComplex += `${concatInputs}concat=n=${timing.scenes.length}:v=1:a=0[outv]`;

    return { inputs, filterComplex };
  }

  // Utility: Get episode directory
  getEpisodeDir(episodeNumber) {
    const episodesDir = path.join(this.projectRoot, 'episodes');
    const dirs = fs.readdirSync(episodesDir).filter(dir => 
      fs.statSync(path.join(episodesDir, dir)).isDirectory() &&
      dir.startsWith(`${episodeNumber}.`)
    );

    if (dirs.length === 0) {
      console.log(`❌ Không tìm thấy episode ${episodeNumber}`);
      return null;
    }

    return path.join(episodesDir, dirs[0]);
  }

  // Tạo tất cả videos của 1 episode
  async generateAll(episodeNumber) {
    console.log(`📺 Tạo tất cả video cho episode ${episodeNumber}`);
    await this.generateTestVideo(episodeNumber);
    await this.generateFinalVideo(episodeNumber);
  }

  // Batch processing cho nhiều episodes
  async generateBatch(episodeNumbers) {
    for (const num of episodeNumbers) {
      await this.generateAll(num);
      console.log('---');
    }
  }

  // Show help
  showHelp() {
    console.log(`
🎬 Video Generator - Centralized video production tool

Usage:
  node video-generator.mjs <command> <episode-number>

Commands:
  test <num>     - Tạo video test đơn giản
  final <num>    - Tạo video final với Ken Burns
  all <num>      - Tạo cả test và final
  batch <nums>   - Tạo cho nhiều episodes (vd: batch 1,2,3)
  help           - Hiển thị help này

Examples:
  node video-generator.mjs test 1
  node video-generator.mjs final 1  
  node video-generator.mjs all 1
  node video-generator.mjs batch 1,2,3
`);
  }
}

// CLI Interface
const [,, command, ...args] = process.argv;
const generator = new VideoGenerator();

switch (command) {
  case 'test':
    if (args[0]) {
      generator.generateTestVideo(parseInt(args[0]));
    } else {
      console.log('❌ Cần episode number. VD: node video-generator.mjs test 1');
    }
    break;

  case 'final':
    if (args[0]) {
      generator.generateFinalVideo(parseInt(args[0]));
    } else {
      console.log('❌ Cần episode number. VD: node video-generator.mjs final 1');
    }
    break;

  case 'all':
    if (args[0]) {
      generator.generateAll(parseInt(args[0]));
    } else {
      console.log('❌ Cần episode number. VD: node video-generator.mjs all 1');
    }
    break;

  case 'batch':
    if (args[0]) {
      const numbers = args[0].split(',').map(n => parseInt(n.trim()));
      generator.generateBatch(numbers);
    } else {
      console.log('❌ Cần danh sách episodes. VD: node video-generator.mjs batch 1,2,3');
    }
    break;

  case 'help':
  default:
    generator.showHelp();
    break;
}