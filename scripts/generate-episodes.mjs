import fs from 'fs';
import path from 'path';
import { loadAllJsonFiles, formatScript, secToSRT } from './utils.mjs';

// Đọc tất cả file JSON từ thư mục data
const jsonData = loadAllJsonFiles('data');

// Kiểm tra có dữ liệu không
if (jsonData.length === 0) {
  console.log('❌ Không tìm thấy dữ liệu JSON nào để xử lý');
  process.exit(1);
}

console.log(`🎬 Tổng cộng có ${jsonData.length} tập để xử lý\n`);

// Tạo thư mục chung cho tất cả episodes
const episodesDir = 'episodes';
if (!fs.existsSync(episodesDir)) {
  fs.mkdirSync(episodesDir, { recursive: true });
  console.log(`📁 Đã tạo thư mục chung: ${episodesDir}`);
}

// Tạo thư mục và file content.json + content.txt cho mỗi item
jsonData.forEach((item, index) => {
  // Lấy số tập từ title thay vì dùng index
  const episodeMatch = item.title.match(/Tập (\d+)/);
  const episodeNumber = episodeMatch ? episodeMatch[1] : (index + 1);
  const folderName = path.join(episodesDir, `${episodeNumber}.${item.alias}`);
  
  // Tạo thư mục nếu chưa tồn tại
  if (!fs.existsSync(folderName)) {
    fs.mkdirSync(folderName, { recursive: true });
    console.log(`✅ Đã tạo thư mục: ${folderName}`);
  } else {
    console.log(`📁 Thư mục đã tồn tại: ${folderName}`);
  }

  // Tạo production subfolders
  const productionFolders = ['audio', 'images', 'output'];
  productionFolders.forEach(folder => {
    const subfolderPath = path.join(folderName, folder);
    if (!fs.existsSync(subfolderPath)) {
      fs.mkdirSync(subfolderPath, { recursive: true });
      console.log(`📁 Đã tạo: ${folder}/`);
    }
  });
  
  // Tạo file content.txt với script text được định dạng đẹp
  const contentTxtPath = path.join(folderName, 'content.txt');
  
  // formatScript is imported from ./utils.mjs
  
  const scriptTexts = item.visual_prompts.map(vp => vp.text || '').filter(Boolean);
  const txtContent = `${formatScript(scriptTexts.join(' '))}`;

  fs.writeFileSync(contentTxtPath, txtContent, 'utf8');
  console.log(`📝 Đã tạo file: ${contentTxtPath}`);
});

console.log('\n🎉 Hoàn thành tạo cấu trúc thư mục và file!');