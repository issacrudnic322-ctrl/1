# AHUT 晚寝定时运行

计划每天北京时间 **21:35** 由 GitHub Actions 调度，UTC cron 为 `35 13 * * *`。GitHub 可能延迟执行，不能保证准点。电脑和手机无需保持开机。

## 完成账号配置

仓库 Settings → Secrets and variables → Actions → New repository secret，分别保存：

| Name | Secret |
| --- | --- |
| `AHUT_STUDENT_ID` | 你的学号 |
| `AHUT_PASSWORD` | 考勤系统实际使用的密码；未修改时填写初始密码 |

公开仓库中不要把学号、密码、令牌和原始接口日志写进代码或 Issues。缺少任何一项 Secret，程序会明确报配置未完成，并在连接学校前退出。

打开 Actions → AHUT nightly 21:35 → Run workflow，默认模式现在是 `sign-in`，会在北京时间 21:35 后提交签到。运行标题会明确标记手动签到或定时签到。

若只想检查配置，主动选择 `check`，运行标题将显示“仅检查配置（不签到）”。检查通过只表示两项配置已提供，不代表密码正确或签到成功。

## 如何判断结果

运行详情中的摘要会显示触发方式、北京时间和以下状态，不包含凭据或学校原始响应：

| 状态 | 含义 |
| --- | --- |
| `configuration_only` | 只检查配置，没有连接学校或提交签到 |
| `api_confirmed` | 学校提交接口明确返回成功，尚未独立查询当日记录 |
| `already_signed` | 学校接口明确返回今天已完成签到，尚未独立查询当日记录 |
| `sign_in_failed` / `login_failed` | 未确认成功，任务返回失败；摘要标记失败阶段 |
| `configuration_error` / `outside_window` | 配置不完整或未到北京时间 21:35，没有提交 |
| `execution_error` / `invalid_result` | 异常或未知格式，不按成功处理 |

请在学校小程序核对当日记录。Actions 绿勾本身不能证明签到成功。

## 验证与发布

执行 `python -m unittest discover -s tests -v` 进行离线回归测试，不使用真实账号、不发起学校请求。`Offline regression tests` 工作流同样只测试代码，不进行签到。

把修复提交合并到默认分支后，先在允许的时间手动执行 `sign-in`，检查摘要并核对小程序记录。下一天单独检查是否出现事件类型为 `schedule` 的运行；手动运行成功不能验证定时触发。当前 cron 的时区换算正确，此补丁没有证明或修复此前未触发的服务端原因。

## 运行说明

- `.github/workflows/nightly.yml`：默认分支上的每日调度、手动检查与手动运行。
- `runner.py`：读取 Secrets、设置北京时间、屏蔽账号及接口详情日志、返回明确退出状态。
- `signin_core.py`：基于 [UnthinkingBrain/-_ahut_wqqd 的 main_sync.py](https://github.com/UnthinkingBrain/-_ahut_wqqd/blob/master/main_sync.py)，保留原作者署名，移除交互输入、硬编码初始密码及空错误响应被视为成功的分支。
- Python 3.13，标准库运行，无额外 pip 依赖；没有上传或运行 Windows EXE。

## 实际限制

GitHub Actions 的定时任务可能延迟，不能保证 21:35 准点。公开仓库连续 60 天没有仓库活动时，GitHub 可能自动停用定时工作流；届时在 Actions 中重新启用。请留意任务是否仍在运行。

此版本的账号配置与运行结果处理经过离线检查，尚未验证学校真实登录与签到。学校网络、接口更新、账号状态和签到窗口都可能导致失败。此程序沿用上游提交位置数据的逻辑，不读取手机实时位置；不能据此证明实际在寝。

参考：[GitHub 定时工作流](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)、[GitHub Secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)。
