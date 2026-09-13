# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Lê Trọng Khánh  
> **Mã Sinh Viên / Mã Học viên:** 2A202602941  
> **Chủ đề Lựa chọn:** Trợ lý Học vụ & Đặt lịch tư vấn VinUni  

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | 5 / 5 | Agent phải phân tích yêu cầu, tra cứu hồ sơ để xác định sinh viên và cố vấn phụ trách, kiểm tra thông tin lịch hẹn, sau đó mới đặt lịch và trả kết quả xác nhận cho sinh viên. |
| **2. Tool Interaction** | 5 / 5 | Bài toán cần tương tác với MCP Server qua ba công cụ: `academic_query` để tra cứu hồ sơ và cố vấn, `get_schedule` để kiểm tra khung giờ, và `schedule_appointment` để tạo lịch tư vấn học vụ. |
| **3. Dynamic Decision** | 4 / 5 | Agent phải tự quyết định trả lời trực tiếp hay gọi công cụ, chọn công cụ phù hợp theo ý định người dùng, đồng thời xử lý linh hoạt các trường hợp thiếu dữ liệu, không tìm thấy sinh viên hoặc đặt lịch không hợp lệ. |
| **4. Long Horizon Goal** | 2 / 5 | Mục tiêu đặt lịch được hoàn thành qua nhiều bước phụ thuộc nhau từ tra cứu đến xác nhận, nhưng quy trình tương đối ngắn và chưa yêu cầu theo dõi, nhắc lịch hoặc điều chỉnh lịch trong thời gian dài. |
| **TỔNG ĐIỂM AGENTIC FIT** | **16 / 20** | *Tổng điểm > 12/20: Bài toán rất phù hợp triển khai Agentic System.* |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

Test suite được thực thi bằng Gemini API thật với provider `gemini` và model `gemini-3.1-flash-lite`. File `docs/trace_waterfall.json` ghi nhận 14 sự kiện, gồm 9 lần thực thi Tool và 5 câu trả lời cuối cùng.

### 2.1. Kết quả từng Test Case

| Test Case | Kết quả | Đánh giá |
| :---: | :---: | :--- |
| **TC01** | Đạt | Gemini trả lời trực tiếp câu hỏi chung và không gọi Tool. |
| **TC02** | Đạt, có lưu ý | Agent gọi đúng `academic_query` và trả đúng hồ sơ SV2026001, nhưng gọi thêm `get_schedule` dù người dùng chỉ yêu cầu tra cứu học vụ. |
| **TC03** | Đạt | Agent xác minh sinh viên, kiểm tra lịch và đặt thành công lịch lúc 14:00 ngày 15/09/2026 cho SV2026001. |
| **TC04** | Đạt | Agent hoàn thành đúng chuỗi đa bước `academic_query → get_schedule → schedule_appointment` cho SV2026002 và chọn khung giờ trống đầu tiên. |
| **TC05** | Đạt | Agent giữ đúng mã SV9999999, nhận `NOT_FOUND` và phản hồi lịch sự, không bịa dữ liệu. |

### 2.2. Trace tiêu biểu cho TC04 — ReAct đa bước

Đoạn trích rút gọn từ `docs/trace_waterfall.json`:

```json
[
  {
    "step": 1,
    "action_type": "TOOL_EXECUTION",
    "tool_name": "academic_query",
    "arguments": {
      "student_id": "SV2026002"
    },
    "observation": {
      "status": "SUCCESS",
      "student_id": "SV2026002",
      "data": {
        "full_name": "Trần Thị Bình",
        "advisor": "TS. Lê Thị B",
        "advisor_id": "GV2026002"
      }
    },
    "latency_ms": 1486.24
  },
  {
    "step": 2,
    "action_type": "TOOL_EXECUTION",
    "tool_name": "get_schedule",
    "arguments": {
      "advisor_id": "GV2026002"
    },
    "observation": {
      "status": "SUCCESS",
      "advisor_name": "TS. Lê Thị B",
      "slots": [
        {
          "datetime": "10:00 15/09/2026",
          "status": "AVAILABLE"
        },
        {
          "datetime": "13:30 17/09/2026",
          "status": "AVAILABLE"
        }
      ]
    },
    "latency_ms": 1410.94
  },
  {
    "step": 3,
    "action_type": "TOOL_EXECUTION",
    "tool_name": "schedule_appointment",
    "arguments": {
      "student_id": "SV2026002",
      "datetime_str": "10:00 15/09/2026",
      "advisor_name": "TS. Lê Thị B"
    },
    "observation": {
      "status": "SUCCESS",
      "booking_id": "BK-SV2026002-002",
      "message": "Đặt lịch thành công cho sinh viên SV2026002 với TS. Lê Thị B vào lúc 10:00 15/09/2026."
    },
    "latency_ms": 1587.18
  },
  {
    "step": 4,
    "action_type": "FINAL_ANSWER",
    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ).",
    "output": "Yêu cầu của bạn đã được hoàn tất thành công.\n\nDưới đây là thông tin chi tiết:\n- **Sinh viên:** Trần Thị Bình (SV2026002)\n- **Cố vấn học tập:** TS. Lê Thị B\n- **Trạng thái:** Đã đặt lịch hẹn thành công vào lúc **10:00 ngày 15/09/2026**.\n- **Mã đặt lịch:** BK-SV2026002-002",
    "latency_ms": 1656.19
  }
]
```

Trace cho thấy Observation của mỗi Tool đã được đưa vào bước suy luận tiếp theo. Agent lấy `advisor_id` từ hồ sơ sinh viên, dùng mã này để kiểm tra lịch, chọn đúng slot `AVAILABLE`, sau đó truyền chính xác thời gian và tên cố vấn vào công cụ đặt lịch.

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã cấu hình API Key thật trong `.env` và xác nhận Agent chạy bằng Gemini API.
- **Tổng số Test Cases hoàn thành đúng chức năng:** **5 / 5 test cases**; TC02 còn một Tool Call dư thừa cần tối ưu.
- **Số lượt gọi Tool qua MCP Server:** **9 lượt** (`academic_query`: 4, `get_schedule`: 3, `schedule_appointment`: 2).
- **Độ chính xác Tool Call:** **9/9 lượt thực thi với tham số hợp lệ và nhận đúng trạng thái nghiệp vụ**; trong đó **8/9 lượt phù hợp hoàn toàn với phạm vi yêu cầu**, một lượt `get_schedule` trong TC02 là không cần thiết.
- **Tổng thời gian ghi nhận trong trace:** **25,398.74 ms** cho 14 sự kiện.
- **Kết quả nổi bật:** TC04 chứng minh Agent có khả năng duy trì trạng thái và hoàn thành quy trình ReAct đa bước; TC05 chứng minh cơ chế giữ nguyên định danh người dùng và xử lý `NOT_FOUND` an toàn.
- **Điểm cần cải thiện:** Bổ sung quy tắc dừng rõ hơn để Agent không gọi `get_schedule` khi người dùng chỉ yêu cầu xem hồ sơ học vụ như TC02.
- **Kết quả đẩy Repo nộp bài:** [ ] Chưa xác nhận Commit và Push lên GitHub cá nhân.

### Kết luận nghiệm thu

Hệ thống đạt mục tiêu của bài Lab: phân biệt được câu hỏi trả lời trực tiếp và yêu cầu cần Tool, kết nối MCP Server theo JSON-RPC 2.0, thực hiện được chuỗi ReAct đa bước, ghi Waterfall Trace có độ trễ, và xử lý trường hợp biên mà không bịa đặt dữ liệu. Với tổng điểm Agentic Fit **16/20**, chủ đề phù hợp để triển khai dưới dạng Agentic System.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
