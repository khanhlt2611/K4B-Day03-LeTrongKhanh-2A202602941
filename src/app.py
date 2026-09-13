"""
🚀 CORE AGENT APPLICATION (DAY 03: CHATBOT VS REACT AGENT)
Thực thi so sánh giữa Chatbot Baseline (Cấp 2) và ReAct Agent kết nối MCP Server (Cấp 3).
"""

import json
import os
import re
import sys
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from mcp_server import MCPAcademicServer
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_AGENT_SYSTEM_PROMPT,
    MAX_ITERATIONS
)
from providers import get_llm_provider

load_dotenv()

def load_test_cases():
    """Tải danh sách 5 test cases từ config/test_cases.json hoặc config/test_cases.example.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    if not os.path.exists(config_path):
        example_path = os.path.join(base_dir, "config", "test_cases.example.json")
        if os.path.exists(example_path):
            print("⚠️ [CONFIG NOTICE]: Chưa thấy file 'config/test_cases.json'. Đang dùng mẫu 'config/test_cases.example.json'.")
            print("👉 Hãy chạy: copy config/test_cases.example.json config/test_cases.json và viết test cases theo đề tài của bạn!\n")
            config_path = example_path
        else:
            config_path = "test_cases.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_waterfall_trace(trace_data: list):
    """Ghi vết log Waterfall Trace Log ra file docs/trace_waterfall.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, "trace_waterfall.json")
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    print(f"📊 [OBSERVABILITY]: Đã lưu {len(trace_data)} sự kiện Waterfall Trace tại '{trace_path}'!")


def run_baseline_chatbot(user_query: str, provider):
    """Chạy Chatbot gốc (Cấp 2) không có công cụ gọi Tool"""
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot phản hồi:\n{response}")


def run_react_agent(user_query: str, provider, mcp_server: MCPAcademicServer) -> list:
    """
    [REACT AGENT LOOP] Thực thi vòng lặp Thought -> Action -> Observation với MCP Server
    Trả về danh sách trace log của phiên thực thi.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    
    def format_observation(tool_name: str, observation: dict) -> str:
        """Tạo câu trả lời dự phòng từ dữ liệu thật, không để Agent tự bịa dữ liệu."""
        status = observation.get("status")
        if status == "SUCCESS" and tool_name == "academic_query":
            student = observation.get("data", {})
            return (
                f"Kết quả tra cứu cho sinh viên {observation.get('student_id', '')} "
                f"({student.get('full_name', '')}): Lớp {student.get('class', '')}, "
                f"GPA: {student.get('gpa', '')}, Email: {student.get('email', '')}, "
                f"Trạng thái: {student.get('status', '')}, "
                f"Cố vấn: {student.get('advisor', '')} ({student.get('advisor_id', '')})."
            )
        if status == "SUCCESS" and tool_name == "get_schedule":
            slots = observation.get("slots", [])
            slot_summary = ", ".join(
                f"{slot.get('datetime', '')} "
                f"({'còn trống' if slot.get('status') == 'AVAILABLE' else 'đã được đặt'})"
                for slot in slots
            ) or "không có khung giờ nào"
            return (
                f"Lịch tư vấn của {observation.get('advisor_name', '')} "
                f"({observation.get('advisor_id', '')}): {slot_summary}."
            )
        if status == "SUCCESS" and tool_name == "schedule_appointment":
            return observation.get(
                "message",
                f"Đặt lịch thành công. Mã lịch hẹn: {observation.get('booking_id', '')}."
            )
        if status in {"NOT_FOUND", "SLOT_UNAVAILABLE"}:
            return observation.get("message", "Không tìm thấy dữ liệu phù hợp.")
        if status in {"EXECUTION_ERROR", "UNKNOWN_TOOL"}:
            return observation.get("error", "Không thể thực thi công cụ.")
        return observation.get(
            "message",
            f"Phản hồi từ công cụ: {json.dumps(observation, ensure_ascii=False)}"
        )

    step = 0
    trace_logs = []
    tools_list = mcp_server.list_tools()
    react_history = []
    executed_calls = set()
    last_answer = ""
    known_student = {}
    known_schedule = {}
    student_ids = list(dict.fromkeys(re.findall(r"\bSV\d+\b", user_query.upper())))
    advisor_ids = list(dict.fromkeys(re.findall(r"\bGV\d+\b", user_query.upper())))

    while step < MAX_ITERATIONS:
        step += 1
        step_start_time = time.time()
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")

        agent_input = user_query
        if react_history:
            agent_input = (
                f"YÊU CẦU BAN ĐẦU:\n{user_query}\n\n"
                "LỊCH SỬ ACTION/OBSERVATION ĐÃ THỰC HIỆN:\n"
                f"{json.dumps(react_history, ensure_ascii=False, indent=2)}\n\n"
                "Hãy tiếp tục xử lý yêu cầu ban đầu. Không gọi lại một Action đã có cùng "
                "tham số. Nếu còn bước chưa hoàn thành thì gọi Tool kế tiếp; chỉ trả lời bằng "
                "văn bản khi toàn bộ yêu cầu đã hoàn tất hoặc Observation báo lỗi kết thúc."
            )

        llm_response = provider.generate_with_tools(
            agent_input,
            tools_list,
            system_prompt=REACT_AGENT_SYSTEM_PROMPT
        )
        latency_ms = round((time.time() - step_start_time) * 1000, 2)

        thought = llm_response.get("thought", "Đang suy luận...")
        print(f"🧠 [Thought]: {thought}")

        # Trường hợp 1: LLM quyết định trả lời bằng văn bản trực tiếp
        if llm_response.get("type") == "text":
            final_content = llm_response.get("content", "").strip() or last_answer
            print(f"🏁 [Final Answer]: {final_content}")
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": thought,
                "output": final_content,
                "latency_ms": latency_ms
            })
            break

        # Trường hợp 2: LLM đề xuất gọi Tool (Action)
        elif llm_response.get("type") == "tool_call":
            tool_name = llm_response.get("tool_name")
            arguments = llm_response.get("arguments", {})
            if not isinstance(arguments, dict):
                arguments = {}

            # Các mã được người dùng ghi rõ luôn có độ ưu tiên cao hơn ví dụ do LLM tự điền.
            if tool_name in {"academic_query", "schedule_appointment"} and len(student_ids) == 1:
                arguments["student_id"] = student_ids[0]
            if tool_name == "get_schedule":
                if len(advisor_ids) == 1:
                    arguments["advisor_id"] = advisor_ids[0]
                elif known_student.get("advisor_id"):
                    arguments["advisor_id"] = known_student["advisor_id"]
            if tool_name == "schedule_appointment":
                if known_student.get("advisor"):
                    arguments["advisor_name"] = known_student["advisor"]
                if known_schedule:
                    first_available = next(
                        (
                            slot.get("datetime")
                            for slot in known_schedule.get("slots", [])
                            if slot.get("status") == "AVAILABLE"
                        ),
                        None
                    )
                    if first_available and "khung giờ còn trống đầu tiên" in user_query.lower():
                        arguments["datetime_str"] = first_available

            call_signature = (
                tool_name,
                json.dumps(arguments, ensure_ascii=False, sort_keys=True)
            )
            if call_signature in executed_calls:
                final_content = last_answer or "Không thể tiếp tục vì Agent lặp lại cùng một Tool Call."
                print("⚠️ [ReAct Guard]: Bỏ qua Tool Call trùng lặp.")
                print(f"🏁 [Final Answer]: {final_content}")
                trace_logs.append({
                    "step": step,
                    "query": user_query,
                    "action_type": "FINAL_ANSWER",
                    "thought": "Dừng vòng lặp vì Tool Call bị lặp.",
                    "output": final_content,
                    "latency_ms": latency_ms
                })
                break

            print(f"🛠️ [Action Proposed]: {tool_name}({arguments})")

            # Thực thi Tool qua MCP Server
            mcp_result = mcp_server.call_tool(tool_name, arguments)
            obs_data = mcp_result.get("result", {})
            latency_ms = round((time.time() - step_start_time) * 1000, 2)

            if not obs_data:
                obs_data = {
                    "status": "EMPTY_RESULT",
                    "message": "MCP Server không trả về dữ liệu."
                }
                print("👁️ [Observation từ MCP Server]: {}")
            else:
                obs_str = json.dumps(obs_data, ensure_ascii=False)
                print(f"👁️ [Observation từ MCP Server]: {obs_str}")

            executed_calls.add(call_signature)
            last_answer = format_observation(tool_name, obs_data)
            if tool_name == "academic_query" and obs_data.get("status") == "SUCCESS":
                known_student = obs_data.get("data", {})
            elif tool_name == "get_schedule" and obs_data.get("status") == "SUCCESS":
                known_schedule = obs_data

            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "TOOL_EXECUTION",
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": obs_data,
                "latency_ms": latency_ms
            })

            react_history.append({
                "step": step,
                "action": {"tool_name": tool_name, "arguments": arguments},
                "observation": obs_data
            })

        else:
            final_content = last_answer or "LLM trả về định dạng phản hồi không hợp lệ."
            print(f"🏁 [Final Answer]: {final_content}")
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": "Không nhận diện được kiểu phản hồi của LLM.",
                "output": final_content,
                "latency_ms": latency_ms
            })
            break

    if trace_logs and trace_logs[-1].get("action_type") != "FINAL_ANSWER":
        final_content = last_answer or "Agent đã đạt giới hạn số vòng lặp mà chưa hoàn tất yêu cầu."
        print(f"🏁 [Final Answer]: {final_content}")
        trace_logs.append({
            "step": step + 1,
            "query": user_query,
            "action_type": "FINAL_ANSWER",
            "thought": "Đã đạt giới hạn vòng lặp ReAct.",
            "output": final_content,
            "latency_ms": 0.0
        })

    return trace_logs


if __name__ == "__main__":
    print("==========================================================")
    print("🏫 VINUNI AI COURSE - DAY 03 LAB: CHATBOT VS REACT AGENT")
    print("==========================================================")
    
    provider = get_llm_provider()
    mcp_server = MCPAcademicServer()
    
    print(f"🔌 LLM Provider: {provider.__class__.__name__}")
    print(f"🌐 MCP Server: {mcp_server.server_name}\n")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases thử nghiệm.\n")
    
    if "--interactive" in sys.argv:
        print("🎮 [INTERACTIVE MODE] Trò chuyện trực tiếp với ReAct Agent:")
        print("💡 Gợi ý câu hỏi thử nghiệm:")
        print("   - Câu hỏi chung: 'Quy chế học vụ VinUni yêu cầu bao nhiêu tín chỉ?'")
        print("   - Tra cứu học vụ: 'Hãy tra cứu thông tin học vụ của sinh viên SV2026001'")
        print("   - Đặt lịch hẹn: 'Đặt lịch hẹn tư vấn cho SV2026001 vào 14:00 ngày 15/09/2026'")
        print("   - Gõ 'exit' hoặc 'quit' để kết thúc phiên trò chuyện.\n")
        while True:
            try:
                user_input = input("👤 Sinh viên hỏi: ").strip()
                if not user_input or user_input.lower() in ["exit", "quit"]:
                    print("👋 Tạm biệt! Kết thúc phiên trò chuyện.")
                    break
                logs = run_react_agent(user_input, provider, mcp_server)
                save_waterfall_trace(logs)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Đã thoát phiên tương tác.")
                break
    elif "--all" in sys.argv:
        print("🚀 [TEST SUITE MODE] Kiểm tra 5 Test Cases:")
        completed_count = 0
        todo_count = 0
        all_traces = []
        
        for tc in tests:
            print(f"\n==================================================")
            print(f"🧪 [{tc['id']}] Loại test: {tc['type']} (Độ phức tạp: {tc['complexity']})")
            print(f"📌 Kỳ vọng: {tc['expected_behavior']}")
            
            if tc["question"].strip().startswith("TODO"):
                print(f"⏸️ [CHƯA KÍCH HOẠT - ĐANG LÀ TODO]:")
                print(f"   {tc['question']}")
                print(f"   👉 Hãy mở file 'config/test_cases.json' để viết câu hỏi thực tế cho Test Case này!")
                todo_count += 1
            else:
                logs = run_react_agent(tc["question"], provider, mcp_server)
                all_traces.extend(logs)
                completed_count += 1
                
        print(f"\n==================================================")
        print(f"📊 [KẾT QUẢ TEST SUITE]: Đã thực thi {completed_count}/{len(tests)} Test Cases | {todo_count} Test Cases đang chờ điền câu hỏi (TODO)")
        if all_traces:
            save_waterfall_trace(all_traces)
        print(f"💡 Để trò chuyện trực tiếp từng câu: Chạy 'python src/app.py --interactive'")
    else:
        # Chế độ mặc định khi chỉ gõ 'python src/app.py'
        print("ℹ️ HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH:")
        print("  1. Chat trực tiếp liên tục:   python src/app.py --interactive")
        print("  2. Chạy toàn bộ Test Cases:    python src/app.py --all\n")
        
        sample_query = tests[1]["question"]
        print(f"--- 🏁 DEMO CHẠY THỬ 1 TEST CASE MẪU (TC02: Tra cứu học vụ) ---")
        logs = run_react_agent(sample_query, provider, mcp_server)
        save_waterfall_trace(logs)
        print("\n💡 Hãy thử ngay lệnh: python src/app.py --interactive để chat trực tiếp!")
