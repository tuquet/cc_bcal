import fs from 'fs';
import path from 'path';

export function loadAllJsonFiles(dataDir = 'data') {
  let allData = [];
  if (!fs.existsSync(dataDir)) {
    console.log(`❌ Thư mục ${dataDir} không tồn tại`);
    return allData;
  }

  const files = fs.readdirSync(dataDir).filter(file => file.endsWith('.json'));
  console.log(`📖 Tìm thấy ${files.length} file JSON trong thư mục ${dataDir}`);

  files.forEach(file => {
    try {
      const filePath = path.join(dataDir, file);
      const jsonData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
      if (Array.isArray(jsonData)) {
        allData = allData.concat(jsonData);
        console.log(`✅ Đã đọc ${jsonData.length} tập từ ${file}`);
      } else {
        allData.push(jsonData);
        console.log(`✅ Đã đọc 1 tập từ ${file}`);
      }
    } catch (error) {
      console.log(`❌ Lỗi đọc file ${file}:`, error.message);
    }
  });

  return allData;
}

export function pad(n) {
  return n.toString().padStart(2, '0');
}

export function secToSRT(sec) {
  // Accept seconds as number (can be float)
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  const ms = Math.round((sec - Math.floor(sec)) * 1000);
  return `${pad(h)}:${pad(m)}:${pad(s)},${ms.toString().padStart(3, '0')}`;
}

export function getEpisodeDir(projectRoot, episodeNumber) {
  const episodesDir = path.join(projectRoot, 'episodes');
  if (!fs.existsSync(episodesDir)) return null;
  const dirs = fs.readdirSync(episodesDir).filter(dir => {
    try {
      return fs.statSync(path.join(episodesDir, dir)).isDirectory() && dir.startsWith(`${episodeNumber}.`);
    } catch (e) {
      return false;
    }
  });
  if (dirs.length === 0) return null;
  return path.join(episodesDir, dirs[0]);
}
