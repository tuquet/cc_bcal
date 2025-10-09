# 🎬 Video Production Workflow - "Hỏi Thầy Một Câu"

## 📋 Tổng quan quy trình sản xuất

### 🎯 Mục tiêu
Tạo video hoàn chỉnh từ:
- ✅ **Audio**: File MP3 có sẵn
- 🖼️ **Images**: AI-generated từ visual prompts  
- 📝 **Script**: Content.txt với timing
- 🎨 **Effects**: Transition, subtitle, branding

## 🗂️ Cấu trúc Assets

```
episodes/
├── [episode]/
│   ├── content.json          # Metadata đầy đủ
│   ├── content.txt          # Script with timing
│   ├── audio/
│   │   └── voiceover.mp3    # File audio chính
│   ├── images/
│   │   ├── scene1.png       # Hình ảnh scene 1
│   │   ├── scene2.png       # Hình ảnh scene 2
│   │   ├── scene3.png       # Hình ảnh scene 3
│   │   ├── scene4.png       # Hình ảnh scene 4
│   │   └── scene5.png       # Hình ảnh scene 5
│   ├── output/
│   │   ├── draft.mp4        # Video draft
│   │   └── final.mp4        # Video cuối cùng
│   └── timing.json          # Timing cho từng scene
```

## 🎵 Audio Analysis & Timing

### Phân tích file MP3
1. **Duration**: Tổng thời lượng audio
2. **Scene timing**: Chia audio theo 5 scenes
3. **Pause detection**: Tìm điểm ngắt tự nhiên
4. **Sync points**: Đánh dấu thời điểm chuyển scene

### Template timing.json
```json
{
  "total_duration": 120,
  "scenes": [
    {
      "scene": 1,
      "start_time": 0,
      "end_time": 24,
      "duration": 24,
      "description": "Scene mở đầu"
    },
    {
      "scene": 2, 
      "start_time": 24,
      "end_time": 48,
      "duration": 24,
      "description": "Vấn đề được đặt ra"
    }
  ]
}
```

## 🖼️ Image Production Pipeline

### Tạo hình ảnh từ AI
1. **Input**: Sử dụng visual_prompts từ content.json
2. **Tool**: Midjourney/DALL-E với prompts đã tối ưu
3. **Resolution**: 1920x1080 (16:9) cho video
4. **Style**: Consistent theo hướng dẫn trong AI-Image-Training-Guide.md
5. **Naming**: scene1.png, scene2.png, etc.

### Quality checklist
- ✅ Độ phân giải 1920x1080
- ✅ Format PNG hoặc JPG chất lượng cao
- ✅ Phong cách nhất quán
- ✅ Phù hợp với nội dung script
- ✅ Không có text trong ảnh

## 🎞️ Video Assembly

### Tools cần thiết
**Option 1: FFmpeg (Command line)**
- Pros: Automation, batch processing, precise control
- Cons: Learning curve

**Option 2: DaVinci Resolve (Professional)**
- Pros: Professional features, color grading, effects
- Cons: More complex

**Option 3: Adobe Premiere Pro**
- Pros: Industry standard, templates
- Cons: Subscription cost

### Video specifications
```
Resolution: 1920x1080 (Full HD)
Frame Rate: 30fps
Audio: 48kHz, stereo
Format: MP4 (H.264)
Bitrate: 8-12 Mbps
```

## 🔧 Automation Scripts

### Script 1: Asset preparation
```bash
# Tạo cấu trúc thư mục cho episode
node prepare-episode.mjs [episode-number]
```

### Script 2: Timing analysis  
```bash
# Phân tích audio và tạo timing.json
node analyze-audio.mjs [episode-number]
```

### Script 3: Video generation
```bash
# Ghép video tự động từ assets
node generate-video.mjs [episode-number]
```

## 📝 Production Checklist

### Pre-production
- [ ] Content.json đã có đầy đủ
- [ ] File MP3 chất lượng tốt
- [ ] Visual prompts đã review

### Production  
- [ ] Tạo 5 hình ảnh chất lượng cao
- [ ] Phân tích timing audio
- [ ] Setup project trong video editor
- [ ] Import all assets

### Assembly
- [ ] Sync audio với images
- [ ] Add transitions giữa scenes
- [ ] Color grading nhất quán
- [ ] Add subtitle nếu cần
- [ ] Add intro/outro branding

### Post-production
- [ ] Export video chất lượng cao
- [ ] Quality check trên nhiều devices
- [ ] Tạo thumbnail
- [ ] Prepare metadata cho upload

## 🎨 Visual Guidelines

### Transitions
- **Ken Burns Effect**: Zoom in/out nhẹ trên static images
- **Fade**: Fade in/out giữa scenes
- **Duration**: 0.5-1 giây transition time

### Typography (nếu có subtitle)
- **Font**: Simple, readable (Roboto, Open Sans)
- **Size**: 48-56pt
- **Color**: White với black outline
- **Position**: Bottom third

### Branding
- **Logo**: Góc dưới phải, 10% opacity
- **Color palette**: Theo style guide thiền học
- **Music**: Background music nhẹ nếu cần

## 📊 Quality Control

### Technical QC
- Audio levels: -12dB to -6dB
- No audio clipping
- Consistent image quality
- Smooth transitions
- No rendering artifacts

### Content QC  
- Hình ảnh match với script
- Timing phù hợp với audio
- Phong cách nhất quán
- Message clear và impactful

## 📤 Export & Distribution

### Export settings
```
Format: MP4
Codec: H.264
Resolution: 1920x1080
Frame Rate: 30fps
Bitrate: Variable (8-12 Mbps)
Audio: AAC, 48kHz, 320kbps
```

### Platform optimization
- **YouTube**: Upload original quality
- **Facebook**: Compress to <1GB
- **Instagram**: 1:1 crop version
- **TikTok**: 9:16 vertical version

## 🚀 Next Steps

1. **Tạo scripts automation** cho workflow
2. **Setup template** cho video editor
3. **Tạo style guide** chi tiết
4. **Test pipeline** với 1 episode
5. **Scale up** cho tất cả episodes

---

*Professional video production workflow cho "Hỏi Thầy Một Câu" series* 🎬✨