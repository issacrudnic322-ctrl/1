"""Noninteractive Actions entry point; credentials and server payloads stay out of logs."""
import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone


def run(check_only=False):
    student_id = os.environ.get("AHUT_STUDENT_ID", "").strip()
    password = os.environ.get("AHUT_PASSWORD", "")
    if not student_id or not password:
        print("配置未完成：请在仓库 Settings → Secrets and variables → Actions 添加 AHUT_STUDENT_ID 和 AHUT_PASSWORD。")
        return 2
    if not student_id.isascii() or not student_id.isdigit():
        print("配置错误：AHUT_STUDENT_ID 必须是数字学号。")
        return 2
    if check_only:
        print("凭据配置已就绪；本次未连接学校系统，也未验证密码是否正确。")
        return 0
    now = datetime.now(timezone(timedelta(hours=8)))
    if (now.hour, now.minute) < (21, 35):
        print("当前未到北京时间 21:35，本次不提交签到。")
        return 2
    os.environ["TZ"] = "Asia/Shanghai"
    if hasattr(time, "tzset"):
        time.tzset()
    logging.disable(logging.CRITICAL)
    try:
        import signin_core
        user = signin_core.User(student_Id=int(student_id), password=password)
        result = signin_core.sign_in(user, debug=False)
    except Exception:
        print("执行异常；请检查学校服务可用性。为保护账号，日志不输出原始异常或请求内容。")
        return 1
    if result.get("success") is True:
        print("学校接口返回签到成功或今天已完成签到；请在小程序核对记录。")
        return 0
    errors = result.get("data", set())
    if "密码错误" in errors:
        print("登录失败：请更新 AHUT_PASSWORD。")
    else:
        print("签到未成功：可能是登录、任务时间、网络或接口变化，请在小程序核对。")
    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-config", action="store_true")
    args = parser.parse_args()
    sys.exit(run(check_only=args.check_config))
