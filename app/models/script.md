interface Scripts {
  // THÔNG TIN CỐT TRUYỆN CƠ BẢN
  title: string;
  alias: string;
  logline: string;
  
  // TÍNH CHẤT CÂU CHUYỆN
  genre: string[]; // Đổi thành mảng để chứa nhiều thể loại (ví dụ: ["Hài", "Đời thường"])
  themes: string[];
  tone: string;
  notes: string; // Ghi chú chung về kịch bản

  // CẤU TRÚC KỊCH BẢN
  setting: Setting;
  characters: Character[];
  acts: Act[];

  // QUẢN LÝ TRẠNG THÁI (WORKFLOW STATUS)
  // Các cờ Boolean để kiểm tra tiến độ
  is_video_generated: boolean;
  is_audio_generated: boolean;
  is_image_generated: boolean;
  is_transcript_generated: boolean;
  
  // TRẠNG THÁI GHÉP NỐI/RENDER
  is_video_compiled: boolean;
  compilation_path: string | null; // Đường dẫn file video cuối cùng (nếu đã compile)

  // THÔNG SỐ KỸ THUẬT CỦA VIDEO ĐẦU RA
  builder_configs: BuilderParams;
  
  // THÔNG TIN HỆ THỐNG
  created_at: string; // Timestamp
  updated_at: string; // Timestamp
}


interface BuilderParams {
  frame_rate: number;
  duration_seconds: number; // Đã chuẩn hóa đơn vị thành giây
  format: string;
  aspect_ratio: string;
  quality: string;
  resolution: string;
}

interface Act {
  act_number: number;
  summary: string;
  scenes: Scene[];
}

interface Scene {
  scene_number: number;
  location: string;
  time: string;
  action: string; // Mô tả hành động/bối cảnh
  dialogues: Dialogue[];
  
  // (Tùy chọn) Đường dẫn nội dung trực tiếp của Cảnh (nếu cả Cảnh dùng chung 1 ảnh/video nền)
  scene_media_path: string | null; 
}

interface Character {
  name: string;
  role: string;
  description: string;
  // (Tùy chọn) Thêm thông tin nếu cần cho AI tạo sinh:
  voice_type: string; // Ví dụ: 'male_deep', 'female_child'
}

interface Setting {
  time: string;
  location: string;
}

interface Dialogue {
  character: string; // PHẢI match với name trong Characters[]
  line: string;
  
  // PHÂN LOẠI LỜI THOẠI (giúp xử lý âm thanh/phụ đề)
  dialogue_type: "speech" | "thought" | "narration" | "sound_effect"; 
  
  // DỮ LIỆU ĐẦU VÀO ĐỂ GHÉP NỐI
  audio_file_path: string | null; // Đường dẫn tới file âm thanh lời thoại cụ thể
  image_file_path: string | null; // Đường dẫn tới file hình ảnh đại diện cho lời thoại này
}

interface BackgroundAudio {
  title: string;
  source: string; // Tên nguồn, ví dụ: 'Bản quyền A', 'Miễn phí B', 'Tự tạo'
  file_path: string; // Đường dẫn đến file nhạc nền (MP3, WAV, v.v.)
  volume_level: number; // Mức âm lượng (ví dụ: 0.1 đến 1.0, hoặc 10% đến 100%)
  
  // (Tùy chọn) Nếu nhạc nền không chạy liên tục
  start_time_seconds: number; // Bắt đầu ở giây thứ mấy của video
  end_time_seconds: number;   // Kết thúc ở giây thứ mấy của video
}