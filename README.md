# 🧘 Hỏi Thầy Một Câu - Video Content Generator

> Hệ thống tự động tạo video thiền học từ kịch bản JSON

## 🎯 Mục đích

Tạo chuỗi video thiền học chất lượng cao với:
- ✅ Kịch bản đã được format sẵn
- ✅ Hình ảnh AI được tạo theo mô tả cụ thể
- ✅ Video tự động ghép với hiệu ứng Ken Burns
- ✅ Quy trình production chuẩn hóa

## 🚀 Cách sử dụng

### Bước 1: Chuẩn bị dữ liệu kịch bản
- Đặt file `data.json` (hoặc các file JSON khác) vào thư mục `data/`
- Làm theo hướng dẫn chi tiết tại `docs/AI-Training-Prompt-Guide.md` để tạo đúng format

### Bước 2: Tạo cấu trúc episodes
```bash
npm run generate
```
→ Tạo folders và files cho tất cả episodes từ dữ liệu JSON trong `data/`

### Bước 3: Chuẩn bị assets
Cho mỗi episode, thêm:
- **Audio:** `episodes/X.tên-tập/audio/voiceover.mp3` 
- **Images:** `episodes/X.tên-tập/images/1.png` → `5.png`

### Bước 4: Tạo video
```bash
# Video test đơn giản
npm run video:test 1

# Video final với hiệu ứng
npm run video:final 1

# Tạo cả hai
npm run video:all 1

# Tạo nhiều episodes cùng lúc
npm run video:batch 1,2,3
```

## � Cấu trúc sau khi generate

```
episodes/
├── 1.tam-nhu-mat-ho/
│   ├── content.json             # Kịch bản và metadata
│   ├── content.txt              # Script dễ đọc
│   ├── timing.json              # Thời gian cho từng scene
│   ├── production-checklist.md  # Checklist sản xuất
│   ├── audio/                   # 📁 Thêm file voiceover.mp3
│   ├── images/                  # 📁 Thêm 5 hình ảnh (1.png → 5.png)
│   └── output/                  # 📁 Video được tạo ra
├── 2.chiec-bat-vo/
└── ... (10 episodes total)
```

## 📋 Production Checklist

Mỗi episode cần:

### 🎵 Audio
- **Format:** MP3, 22kHz, Mono
- **Tên file:** `voiceover.mp3` 
- **Thời lượng:** Khoảng 2 phút/episode

### 🖼️ Images  
- **Số lượng:** 5 hình ảnh
- **Format:** PNG, 1024x1024px
- **Tên file:** `1.png`, `2.png`, `3.png`, `4.png`, `5.png`
- **Nội dung:** Theo mô tả trong `content.json`

### 🎬 Video Output
- **Test video:** Đơn giản, 1 hình + audio
- **Final video:** 5 hình với Ken Burns effects
- **Format:** MP4, 1920x1080, H.264 + AAC

## 🎯 Workflow Production

1. **Setup** → `npm run generate` (1 lần)
2. **Chuẩn bị assets** → Thêm audio + images cho episodes
3. **Tạo video** → `npm run video:all [số tập]`
4. **Review** → Kiểm tra video trong folder `output/`

## 💡 Tips

- **Batch processing:** Dùng `video:batch 1,2,3` cho nhiều episodes
- **Test trước:** Luôn chạy `video:test` trước `video:final`
- **Checklist:** Xem `production-checklist.md` trong mỗi episode folder

## � Yêu cầu hệ thống

- **Node.js** 16+ 
- **npm** (đi kèm Node.js)
- **Hệ điều hành:** Windows, macOS, Linux

> FFmpeg được tự động cài qua npm, không cần cài thủ công

## � Tài liệu chi tiết

- `docs/` - Hướng dẫn kỹ thuật chi tiết
- `AI-Training-Prompt-Guide.md` - Training AI tạo nội dung mới  
- `AI-Image-Training-Guide.md` - Training AI tạo hình ảnh

---

**🎬 Ready to create professional meditation videos!**

### Tạo hình ảnh
Sử dụng `AI-Image-Training-Guide.md` để tạo prompts cho Midjourney/DALL-E với phong cách thiền Việt Nam.

## 🎯 Tính năng nổi bật

- ✅ **Auto-detect**: Tự động đọc tất cả file JSON
- ✅ **Smart parsing**: Lấy số tập từ title thay vì index
- ✅ **Text formatting**: Script được chia câu dễ đọc
- ✅ **Error handling**: Xử lý lỗi và logging chi tiết
- ✅ **Organized structure**: Tất cả episodes trong thư mục riêng

## 📝 Script formatting

Script text được tự động format với:
- Xuống dòng sau dấu chấm (`.`)
- Xuống dòng sau dấu hỏi (`?`)
- Xuống dòng sau dấu chấm than (`!`)
- Xuống dòng sau dấu hai chấm (`:`)
- Xuống dòng sau kết thúc đối thoại (`.'`)

## 🔧 Yêu cầu hệ thống

- Node.js 14+
- File system permissions để tạo thư mục

## 📄 License

MIT License - Tự do sử dụng và phát triển

---

*Được tạo ra để hỗ trợ việc sản xuất content cho chuỗi video thiền học "Hỏi Thầy Một Câu" 🧘‍♂️*