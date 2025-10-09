# Dự án "Hỏi Thầy Một Câu" - Tự động tạo cấu trúc thư mục

## 📋 Mục tiêu
Từ file JSON `generate.json`, tự động tạo ra các thư mục theo thuộc tính `alias` thông qua Node.js.

## 📁 Cấu trúc thư mục được tạo
Mỗi thư mục sẽ có cấu trúc:
```
[số_thứ_tự].[alias]/
├── content.json    # Chứa toàn bộ dữ liệu JSON của item
├── 1.png          # Hình ảnh scene 1
├── 2.png          # Hình ảnh scene 2
├── 3.png          # Hình ảnh scene 3
├── 4.png          # Hình ảnh scene 4
├── 5.png          # Hình ảnh scene 5
└── content.txt    # Nội dung text script
```

## 🚀 Cách sử dụng

### Chạy script tạo episodes
```bash
node run.mjs
```

### Kết quả
Script sẽ tạo ra thư mục `episodes/` chứa các tập:
- `episodes/6.tieng-chuong-sang-som/`
- `episodes/7.dong-nuoc-va-tang-da/`
- `episodes/8.chiec-guong-mo/`
- `episodes/9.canh-cua-khong-khoa/`
- `episodes/10.hat-bui-tren-duong/`

### 4. Nội dung mỗi thư mục
- **content.json**: Chứa toàn bộ thông tin của tập phim (title, hook, script_text, visual_prompts, tags) dạng JSON
- **content.txt**: Nội dung tương tự content.json nhưng định dạng văn bản dễ đọc
- **Hình ảnh**: Các file PNG tương ứng với từng scene (cần thêm thủ công)

## 📋 Scripts có sẵn
- **run.mjs**: Script chính - tạo thư mục episodes với đầy đủ content.json và content.txt định dạng đẹp

## 🤖 Training AI
- **AI-Training-Prompt-Guide.md**: Hướng dẫn chi tiết để training AI tạo nội dung cho chuỗi video "Hỏi Thầy Một Câu" theo đúng format JSON yêu cầu
- **AI-Image-Training-Guide.md**: Hướng dẫn chi tiết để training AI tạo ảnh (Midjourney, DALL-E, Stable Diffusion) theo phong cách thiền Việt Nam

## 📝 Dữ liệu gốc
File `generate.json` chứa 5 tập phim với các thông tin:
- **title**: Tiêu đề tập phim
- **hook**: Câu hook thu hút
- **alias**: Tên rút gọn (dùng làm tên thư mục)
- **tag**: Các thẻ phân loại
- **script_text**: Nội dung kịch bản
- **visual_prompts**: Mô tả hình ảnh cho từng scene

## 🔧 Yêu cầu hệ thống
- Node.js phiên bản 14 trở lên
- File `generate.json` trong cùng thư mục

## 📋 Ghi chú
- Script sẽ tự động kiểm tra và không ghi đè thư mục đã tồn tại
- Mỗi lần chạy sẽ tạo lại file `content.json` với dữ liệu mới nhất