"""Noninteractive Actions entry point; credentials and server payloads stay out of logs."""
import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone

BEIJING = timezone(timedelta(hours=8))
STAGES = {0: "登录", 1: "获取任务", 2: "微信配置", 3: "开启签到窗口", 4: "获取宿舍信息", 5: "提交签到"}


def report(outcome, message, exit_code):
    """Only locally defined status text is allowed into logs and the job summary."""
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    trigger = {"schedule": "定时触发", "workflow_dispatch": "手动触发"}.get(event, "本地或其他触发")
    timestamp = datetime.now(BEIJING).strftime("%Y-%m-%d %H:%M:%S UTC+8")
    print(f"[{outcome}] {message}")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        summary = f"## AHUT 运行结果\n\n- 触发：{trigger}\n- 北京时间：{timestamp}\n- 状态：`{outcome}`\n- 说明：{message}\n"
        try:
            with open(summary_path, "a", encoding="utf-8") as stream:
                stream.write(summary)
        except OSError:
            print("无法写入任务摘要，请查看上方状态；本次不会因此重新提交签到。")
    return exit_code


def run(check_only=False):
    student_id = os.environ.get("AHUT_STUDENT_ID", "").strip()
    password = os.environ.get("AHUT_PASSWORD", "")
    if not student_id or not password:
        return report("configuration_error", "缺少 AHUT_STUDENT_ID 或 AHUT_PASSWORD；未连接学校系统。", 2)
    if not student_id.isascii() or not student_id.isdigit():
        return report("configuration_error", "AHUT_STUDENT_ID 必须是数字学号；未连接学校系统。", 2)
    if check_only:
        return report("configuration_only", "仅检查配置：没有提交签到，也没有验证密码。", 0)
    now = datetime.now(BEIJING)
    if (now.hour, now.minute) < (21, 35):
        return report("outside_window", "当前未到北京时间 21:35，未提交签到。", 2)
    os.environ["TZ"] = "Asia/Shanghai"
    if hasattr(time, "tzset"):
        time.tzset()
    logging.disable(logging.CRITICAL)
    try:
        import signin_core
        user = signin_core.User(student_Id=int(student_id), password=password)
        result = signin_core.sign_in(user, debug=False)
    except Exception:
        return report("execution_error", "执行异常；未确认签到成功。原始异常和请求内容不写入日志。", 1)
    if not isinstance(result, dict):
        return report("invalid_result", "接口结果格式异常，未确认签到成功。", 1)
    if result.get("success") is True and result.get("outcome") == "api_confirmed":
        return report("api_confirmed", "学校提交接口明确返回成功；尚未独立查询当日签到记录，请在小程序核对。", 0)
    if result.get("success") is True and result.get("outcome") == "already_signed":
        return report("already_signed", "学校接口明确返回今天已完成签到；尚未独立查询当日签到记录，请在小程序核对。", 0)
    errors = result.get("data") or set()
    if "密码错误" in errors:
        return report("login_failed", "登录失败：请更新 AHUT_PASSWORD。", 1)
    stage = STAGES.get(result.get("step"), "结果确认")
    return report("sign_in_failed", f"签到未确认成功；失败阶段：{stage}。未输出学校原始响应。", 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-config", action="store_true")
    args = parser.parse_args()
    sys.exit(run(check_only=args.check_config))
