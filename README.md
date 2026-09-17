# AHUT 晚寝定时运行

每天北京时间 **21:35** 由 GitHub Actions 启动，UTC cron 为 `35 13 * * *`。电脑和手机无需保持开机。

## 完成账号配置

仓库 Settings → Secrets and variables → Actions → New repository secret，分别保存：

| Name | Secret |
| --- | --- |
| `AHUT_STUDENT_ID` | 你的学号 |
| `AHUT_PASSWORD` | 考勤系统实际使用的密码；未修改时填写初始密码 |

公开仓库中不要把学号、密码、令牌和原始接口日志写进代码或 Issues。缺少任何一项 Secret，程序会明确报配置未完成，并在连接学校前退出。

然后打开 Actions → AHUT nightly 21:35 → Run workflow，mode 选择 `check`。检查通过只表示两项配置已提供，不代表密码正确或签到成功。

需要实际运行时，在北京时间 21:35 后选择 `sign-in`。定时任务自动使用签到模式。学校接口返回成功后仍应在小程序核对记录。

## 运行说明

- `.github/workflows/nightly.yml`：默认分支上的每日调度、手动检查与手动运行。
- `runner.py`：读取 Secrets、设置北京时间、屏蔽账号及接口详情日志、返回明确退出状态。
- `signin_core.py`：基于 [UnthinkingBrain/-_ahut_wqqd 的 main_sync.py](https://github.com/UnthinkingBrain/-_ahut_wqqd/blob/master/main_sync.py)，保留原作者署名，移除交互输入、硬编码初始密码及空错误响应被视为成功的分支。
- Python 3.13，标准库运行，无额外 pip 依赖；没有上传或运行 Windows EXE。

## 实际限制

GitHub Actions 的定时任务可能延迟，不能保证 21:35 准点。公开仓库连续 60 天没有仓库活动时，GitHub 可能自动停用定时工作流；届时在 Actions 中重新启用。请留意任务是否仍在运行。

此版本的账号配置与运行结果处理经过离线检查，尚未验证学校真实登录与签到。学校网络、接口更新、账号状态和签到窗口都可能导致失败。此程序沿用上游提交位置数据的逻辑，不读取手机实时位置；不能据此证明实际在寝。

参考：[GitHub 定时工作流](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)、[GitHub Secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)。
