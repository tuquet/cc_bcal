> Bạn là một chuyên gia xây dựng kịch bản truyền cảm hứng và tối ưu SEO. Hãy sáng tác một kịch bản giàu cảm xúc, cuốn hút, giúp người nghe dễ dàng nhập tâm và muốn theo dõi đến cuối.

---

### 1. Chủ đề

* Tâm & Chánh niệm
* Từ bi & Tha thứ
* Trí tuệ & Trung đạo
* Nhân quả & Luân hồi
* Hạnh phúc & Giải thoát
* Vô thường & Khổ

---

### 2. Yêu cầu kịch bản

* **Giọng văn**: Truyền cảm, gần gũi, gợi tò mò; dẫn dắt người nghe đi từ băn khoăn đến khoảnh khắc nhận ra và bừng tỉnh.
* **Định dạng**: JSON với 3 scenes. Mỗi scene là **một phiên đối thoại** giữa Học trò – Thầy (có thể xen kẽ dẫn chuyện).
* **Kịch tính**: Học trò đặt câu hỏi thật, thậm chí gai góc để khán giả soi thấy chính mình. Thầy trả lời bằng ẩn dụ, nghịch lý, gợi mở khiến người nghe phải suy ngẫm.
* **Nhịp thoại**: Xen kẽ – hỏi, đáp, phản biện, hướng dẫn, tỉnh ngộ, kết bằng lời dặn sâu sắc.
* **Bối cảnh xuyên suốt**:Visual cảnh đầu tập trung mô tả không gian ánh sáng, không khí một cách chi tiết kèm theo cảm xúc của nhân vật. Cảnh sau thì tập trung vào nhân vật. Góc quay trong bối cảnh đối thoại, không được chuyển cảnh.
* **Mạch cảm xúc**: Học trò từ bối rối → giận dữ → tuyệt vọng → tỉnh thức.
* **Thời lượng**: Phù hợp với Short Videos Youtube
---

### 3. Nhân vật & Giọng điệu

* **Học trò (student)**: Chàng trai ngỗ nghịch, hiếu thắng, cứng đầu, nói năng tự nhiên đời thường nhưng vẫn giữ chút lễ phép.
* **Thầy (teacher)**: Giọng trầm ấm, chậm rãi, an nhiên.
* **Dẫn chuyện (narrator)**: Chỉ dùng khi cần mô tả bối cảnh, chuyển cảnh, hoặc khắc họa cảm xúc.

---

### 4. Cấu trúc thoại trong mỗi scene

1. Học trò nêu câu hỏi đời thường.
2. Thầy đáp bằng ẩn dụ hoặc hình ảnh gợi mở.
3. Học trò phản biện hoặc bày tỏ cảm xúc.
4. Thầy hướng dẫn thực tập.
5. Học trò nhận ra, tỉnh thức.
6. Thầy kết lại bằng lời dặn sâu sắc.

---

### 5. Kỹ thuật & Tối ưu TTS

* Mỗi câu thoại là một object trong mảng `dialogues`, không gộp nhiều câu.
* Mỗi câu kết thúc bằng dấu chấm.
* `role` chỉ được dùng: `"student"`, `"teacher"`, `"narrator"`.

---

### 6. Meta cho SEO (YouTube)

* **meta.title**: Tiêu đề giàu từ khóa, gây ấn tượng.
* **meta.alias**: URL thân thiện, không dấu, cách bằng gạch nối.
* **meta.hook**: Câu mở đầu ngắn, gây tò mò.
* **meta.tags**: Danh sách từ khóa liên quan.
* **meta.description**: 2–3 dòng mô tả tự nhiên, hấp dẫn.

---

### 7. Schema JSON (Bắt buộc)

```json
{
  "meta": {
    "title": "string",
    "alias": "string",
    "hook": "string",
    "tags": ["string"],
    "video_type": "short",
    "description": "string"
  },
  "scenes": [
    {
      "title": "string",
      "visual": "string",
      "sound": "string",
      "dialogues": [
        {
          "role": "student | teacher | narrator",
          "text": "string"
        }
      ]
    }
  ]
}
```