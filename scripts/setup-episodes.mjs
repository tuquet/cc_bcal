import fs from "fs";
import path from "path";
import { loadAllJsonFiles } from "../lib/utils.mjs";
import videoTemplate from "../video-template.json" with { type: "json" };
// Đọc tất cả file JSON từ thư mục data
const jsonData = loadAllJsonFiles("data");

// Kiểm tra có dữ liệu không
if (jsonData.length === 0) {
  console.log("❌ Không tìm thấy dữ liệu JSON nào để xử lý");
  process.exit(1);
}

console.log(`🎬 Tổng cộng có ${jsonData.length} tập để xử lý\n`);

// Tạo thư mục chung cho tất cả episodes
const episodesDir = "episodes";
if (!fs.existsSync(episodesDir)) {
  fs.mkdirSync(episodesDir, { recursive: true });
  console.log(`📁 Đã tạo thư mục chung: ${episodesDir}`);
}

// Tạo thư mục và file content.json + content.txt cho mỗi item
jsonData.forEach((item, index) => {
  // Lấy số tập từ title thay vì dùng index
  const folderName = path.join(episodesDir, `${item.id}.${item.meta.alias}`);

  // Tạo thư mục nếu chưa tồn tại
  if (!fs.existsSync(folderName)) {
    fs.mkdirSync(folderName, { recursive: true });
    console.log(`✅ Đã tạo thư mục: ${folderName}`);
  } else {
    console.log(`📁 Thư mục đã tồn tại: ${folderName}`);
  }

  // Tạo file content.txt
  const contentTxtPath = path.join(folderName, "content.txt");
  if (!fs.existsSync(contentTxtPath)) {
    const scriptTexts = item.scenes
      .map((vp) => vp.narration || "")
      .filter(Boolean);
    
    // Nối các đoạn văn bản bằng dấu chấm và xuống dòng để TTS đọc tự nhiên hơn
    const txtContent = scriptTexts.join("\n\n");
    fs.writeFileSync(contentTxtPath, txtContent, "utf8");
    console.log(`✍️  Đã tạo file: ${contentTxtPath}`);
  } else {
    console.log(`⏩ Bỏ qua, file đã tồn tại: ${contentTxtPath}`);
  }

  // Tạo file capcut-api.json nếu chưa tồn tại
  const scriptJsonPath = path.join(folderName, "capcut-api.json");
  if (!fs.existsSync(scriptJsonPath)) {
    // Chỉ thêm generation_params khi tạo file mới
    item.generation_params = videoTemplate;
    fs.writeFileSync(scriptJsonPath, JSON.stringify(item, null, 2), "utf8");
    console.log(`📝 Đã tạo file: ${scriptJsonPath}`);
  } else {
    console.log(`⏩ Bỏ qua, file đã tồn tại: ${scriptJsonPath}`);
  }
});

console.log("\n🎉 Hoàn thành tạo cấu trúc thư mục và file!");
