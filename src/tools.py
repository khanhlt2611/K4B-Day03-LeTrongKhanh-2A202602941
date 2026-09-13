"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ cho MCP Server.
"""

import json
import re
from typing import Dict, Any

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA (TASK 1.2)
# ==============================================================================

TOOLS_SCHEMA = [
    # Tool 1: Đã được định nghĩa mẫu sẵn cho Học viên tham khảo
    {
        "name": "academic_query",
        "description": "Tra cứu hồ sơ và thông tin học vụ của sinh viên VinUni bằng mã sinh viên.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã sinh viên cần tra cứu. Phải sao chép chính xác mã xuất hiện trong yêu cầu của người dùng."
                }
            },
            "required": ["student_id"]
        }
    },
    
    # --------------------------------------------------------------------------
    # TODO 1.2: HỌC VIÊN HOÀN THIỆN TOOL SCHEMA CHO 'schedule_appointment'
    # 🎯 YÊU CẦU THIẾT KẾ SCHEMA (JSON SCHEMA STANDARD):
    # 1. Tool dùng để đặt lịch hẹn tư vấn học vụ với Cố vấn học tập VinUni.
    # 2. Thiết kế các tham số (properties) để LLM trích xuất:
    #    - student_id (string): Mã sinh viên cần đặt lịch (ví dụ: 'SV2026001')
    #    - datetime_str (string): Thời gian hẹn (ví dụ: '14:00 15/09/2026')
    #    - advisor_name (string): Tên cố vấn học tập
    # 3. Khai báo danh sách các trường bắt buộc (required).
    # --------------------------------------------------------------------------
    {
        "name": "schedule_appointment",
        "description": "Đặt lịch hẹn tư vấn học vụ với Cố vấn học tập VinUni.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã sinh viên cần đặt lịch, sao chép chính xác từ yêu cầu hoặc kết quả academic_query."
                },
                "datetime_str": {
                    "type": "string",
                    "description": "Thời gian hẹn (ví dụ: '14:00 15/09/2026')"
                },
                "advisor_name": {
                    "type": "string",
                    "description": "Tên cố vấn học tập, lấy chính xác từ yêu cầu hoặc kết quả academic_query/get_schedule."
                }
            },
            "required": ["student_id", "datetime_str", "advisor_name"]
        }
    },

    {
        "name": "get_schedule",
        "description": "Lấy lịch tư vấn và trạng thái các khung giờ của giảng viên. Dùng advisor_id do academic_query trả về trước khi chọn giờ đặt lịch.",
        "parameters": {
            "type": "object",
            "properties": {
                "advisor_id": {
                    "type": "string",
                    "description": "Mã giảng viên cần tra cứu, sao chép chính xác từ yêu cầu hoặc trường advisor_id của academic_query."
                }
            },
            "required": ["advisor_id"]
        }
    }
]

# ==============================================================================
# 2. MÔ PHỎNG DỮ LIỆU & HÀM THỰC THI TOOL (EXECUTION LAYER)
# ==============================================================================

MOCK_DATABASE = {
    "SV2026001": {
        "full_name": "Nguyễn Văn An",
        "class": "AI-K4",
        "gpa": 3.85,
        "email": "an.nv@vinuni.edu.vn",
        "status": "Đang học",
        "advisor": "PGS.TS Nguyễn Văn A",
        "advisor_id": "GV2026001"
    },
    "SV2026002": {
        "full_name": "Trần Thị Bình",
        "class": "AI-K4",
        "gpa": 3.60,
        "email": "binh.tt@vinuni.edu.vn",
        "status": "Đang học",
        "advisor": "TS. Lê Thị B",
        "advisor_id": "GV2026002"
    }
}


# Lịch tư vấn mẫu. Mỗi khung giờ được cập nhật ngay sau khi đặt thành công.
MOCK_SCHEDULES = {
    "GV2026001": {
        "advisor_name": "PGS.TS Nguyễn Văn A",
        "slots": {
            "14:00 15/09/2026": {"is_available": True, "booked_by": None},
            "09:00 16/09/2026": {"is_available": False, "booked_by": "SV2026002"},
            "15:30 16/09/2026": {"is_available": True, "booked_by": None}
        }
    },
    "GV2026002": {
        "advisor_name": "TS. Lê Thị B",
        "slots": {
            "10:00 15/09/2026": {"is_available": True, "booked_by": None},
            "13:30 17/09/2026": {"is_available": True, "booked_by": None}
        }
    }
}

MOCK_APPOINTMENTS = []


def execute_academic_query(student_id: str) -> str:
    """Thực thi tra cứu học vụ theo mã sinh viên"""
    student = MOCK_DATABASE.get(student_id.strip().upper())
    if student:
        return json.dumps({
            "status": "SUCCESS",
            "student_id": student_id,
            "data": student
        }, ensure_ascii=False)
    else:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy dữ liệu sinh viên có mã '{student_id}'"
        }, ensure_ascii=False)


def execute_get_schedule(advisor_id: str) -> str:
    """Lấy toàn bộ khung giờ tư vấn và trạng thái trống/bận của giảng viên."""
    normalized_advisor_id = advisor_id.strip().upper()
    schedule = MOCK_SCHEDULES.get(normalized_advisor_id)

    if not schedule:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy lịch của giảng viên có mã '{advisor_id}'."
        }, ensure_ascii=False)

    slots = [
        {
            "datetime": datetime_str,
            "status": "AVAILABLE" if slot["is_available"] else "BOOKED"
        }
        for datetime_str, slot in schedule["slots"].items()
    ]
    return json.dumps({
        "status": "SUCCESS",
        "advisor_id": normalized_advisor_id,
        "advisor_name": schedule["advisor_name"],
        "slots": slots
    }, ensure_ascii=False)


def _normalize_datetime(datetime_str: str) -> str:
    """Chuẩn hóa các cách viết phổ biến về dạng HH:MM DD/MM/YYYY."""
    match = re.search(
        r"(\d{1,2}):(\d{2}).*?(\d{1,2})/(\d{1,2})/(\d{4})",
        datetime_str.strip()
    )
    if not match:
        return " ".join(datetime_str.strip().split())

    hour, minute, day, month, year = (int(value) for value in match.groups())
    return f"{hour:02d}:{minute:02d} {day:02d}/{month:02d}/{year:04d}"


def execute_schedule_appointment(student_id: str, datetime_str: str, advisor_name: str = "PGS.TS Nguyễn Văn A") -> str:
    """Đặt lịch hẹn nếu sinh viên hợp lệ và khung giờ của cố vấn còn trống."""
    normalized_student_id = student_id.strip().upper()
    normalized_datetime = _normalize_datetime(datetime_str)

    if normalized_student_id not in MOCK_DATABASE:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy dữ liệu sinh viên có mã '{student_id}'."
        }, ensure_ascii=False)

    advisor_id, schedule = next(
        (
            (current_advisor_id, current_schedule)
            for current_advisor_id, current_schedule in MOCK_SCHEDULES.items()
            if current_schedule["advisor_name"].casefold() == advisor_name.strip().casefold()
        ),
        (None, None)
    )
    if not schedule:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy lịch của cố vấn '{advisor_name}'."
        }, ensure_ascii=False)

    slot = schedule["slots"].get(normalized_datetime)
    if not slot or not slot["is_available"]:
        return json.dumps({
            "status": "SLOT_UNAVAILABLE",
            "student_id": normalized_student_id,
            "advisor_id": advisor_id,
            "advisor": schedule["advisor_name"],
            "datetime": normalized_datetime,
            "message": (
                f"Không thể đặt lịch với {schedule['advisor_name']} vào lúc "
                f"{normalized_datetime} vì khung giờ không tồn tại hoặc đã được đặt."
            )
        }, ensure_ascii=False)

    booking_id = f"BK-{normalized_student_id}-{len(MOCK_APPOINTMENTS) + 1:03d}"
    slot["is_available"] = False
    slot["booked_by"] = normalized_student_id
    MOCK_APPOINTMENTS.append({
        "booking_id": booking_id,
        "student_id": normalized_student_id,
        "advisor_id": advisor_id,
        "advisor_name": schedule["advisor_name"],
        "datetime": normalized_datetime
    })

    return json.dumps({
        "status": "SUCCESS",
        "booking_id": booking_id,
        "student_id": normalized_student_id,
        "advisor_id": advisor_id,
        "datetime": normalized_datetime,
        "advisor": schedule["advisor_name"],
        "message": (
            f"Đặt lịch thành công cho sinh viên {normalized_student_id} với "
            f"{schedule['advisor_name']} vào lúc {normalized_datetime}."
        )
    }, ensure_ascii=False)


# Router gọi tool thực tế
TOOL_ROUTER = {
    "academic_query": execute_academic_query,
    "get_schedule": execute_get_schedule,
    "schedule_appointment": execute_schedule_appointment
}

def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool"""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as e:
            return json.dumps({"status": "EXECUTION_ERROR", "error": str(e)}, ensure_ascii=False)
    return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại!"}, ensure_ascii=False)
