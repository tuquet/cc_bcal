import fs from 'fs';
import path from 'path';

// Hàm đọc tất cả file JSON từ thư mục scripts
function loadAllJsonFiles(scriptsDir = 'scrips') {
  let allData = [];
  
  if (!fs.existsSync(scriptsDir)) {
    console.log(`❌ Thư mục ${scriptsDir} không tồn tại`);
    return allData;
  }
  
  const files = fs.readdirSync(scriptsDir).filter(file => file.endsWith('.json'));
  console.log(`📖 Tìm thấy ${files.length} file JSON trong thư mục ${scriptsDir}`);
  
  files.forEach(file => {
    try {
      const filePath = path.join(scriptsDir, file);
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

// Đọc tất cả file JSON từ thư mục scripts
const jsonData = loadAllJsonFiles();

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
  
  // Tạo file content.json với toàn bộ thông tin của item
  const contentJsonPath = path.join(folderName, 'content.json');
  fs.writeFileSync(contentJsonPath, JSON.stringify(item, null, 2), 'utf8');
  console.log(`📄 Đã tạo file: ${contentJsonPath}`);
  
  // Tạo file content.txt với script text được định dạng đẹp
  const contentTxtPath = path.join(folderName, 'content.txt');
  
  // Hàm để chia đoạn văn thành các câu ngắn hơn
  function formatScript(text) {
    return text
      // Thay thế các pattern cụ thể trước
      .replace(/\?' /g, '?\n\n')  // Dấu hỏi + khoảng trắng
      .replace(/!' /g, '!\n\n')  // Dấu chấm than + khoảng trắng  
      .replace(/\.' /g, '.\'\n\n')  // Dấu chấm + nháy đơn + khoảng trắng
      .replace(/\. /g, '.\n\n')  // Dấu chấm + khoảng trắng
      .replace(/: /g, ':\n\n')   // Dấu hai chấm + khoảng trắng
      // Loại bỏ các dòng trống thừa
      .replace(/\n\n\n+/g, '\n\n')
      .trim();
  }
  
  const txtContent = `TIÊU ĐỀ: ${item.title}

HOOK: ${item.hook}

ALIAS: ${item.alias}

TAGS: ${item.tag.join(', ')}

SCRIPT:
${formatScript(item.script_text)}

VISUAL PROMPTS:
${item.visual_prompts.map((prompt, i) => 
  `Scene ${prompt.scene}: ${prompt.title}
  Mô tả: ${prompt.description}
  Style: ${prompt.visual_style}
`).join('\n')}`;
  
  fs.writeFileSync(contentTxtPath, txtContent, 'utf8');
  console.log(`📝 Đã tạo file: ${contentTxtPath}`);
});

console.log('\n🎉 Hoàn thành tạo cấu trúc thư mục và file!');