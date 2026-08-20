# 31 官方 issue 状态清单与源码审计（2026-08-20）

> 状态：内部清单，只读审计产物。目标：区分「已修复 / 仍存在 / 新发现」，为对外动作（确认评论或新 issue）提供源码级证据。
> 基线：WSL master = 2.9.7-32（1e14a49b）；dev build = c9f0d36b（2.9.7-19）；wsldevicehost.dll v1.2.14.0 锚定 net_consomme commit 0bb5cf75（2026-04-19，15 号文档指纹比对）。2.9.5 已含 `#41085` 修复（86b51fcf）。

## 一、已确认修复

### `#40984`（Docker mirrored EADDRINUSE）——已修复，随 2.9.5 发布
- 修复 commit：86b51fcf（PR `#41085`，2026-07-29 合入），`git merge-base --is-ancestor 86b51fcf 2.9.5` 确认在 2.9.5 内。
- 机制：`#40597` 引入的「guest 绑定 host ephemeral 端口一律拒绝」破坏 Docker app-compat；修复改为「计数制限额」：guest 可用 host ephemeral 端口数 <= host 范围一半（cap = (end-start+1)/2），seed 从保留范围重叠数初始化。
- 建议动作：已修复类 -> 不写新 issue。若官方在 `#40984` 下追问，可补确认评论（附 86b51fcf）。

## 二、仍存在（已有人报，非我们的目标）

| issue | 家族 | master 状态 | 源码证据 |
| --- | --- | --- | --- |
| `#41102` / `#41135` | mirrored localhost 连接永不完成（port 5004 特例） | 仍存在，无修复 | 近 200 commit 无 mirrored loopback 修复；官方归并同家族 |
| `#41137` | host->WSL loopback 连错端口 | 仍存在，无修复 | 同上 |
| `#41139` | VirtioProxy accept 未挂起即拒连 | 仍存在，无修复 | vsock/VirtioProxy 路径，未定位到修复 commit |
| `#41227` | ip_local_port_range 扩大导致 hang | 标 feature | 官方不视为 bug，排除 |
| `#41162` | mirrored UDP 泄漏 >16000 端口保留 | 无官方回复 | 泄漏量 > cap(8192)，走保留范围外路径，与 `#41085` 无关，独立 |

## 三、新发现（源码审计产物）

### 新发现 A：`#41085` 计数泄漏（release 失败 -> cap 永久缩小）
- 位置：WslCoreGuestNetworkService.cpp OnPortAllocationRequest Release 分支。
- 逻辑：`m_reservedPorts.erase(it)` 无条件执行；`portsInUse--` 仅当 `SUCCEEDED(result)`。release 失败时：端口从保留表消失但计数不减 -> 计数永久偏高 1 -> 后续 guest 绑定 host ephemeral 端口提前撞 cap（WSAEADDRINUSE），直到服务重启。
- 作者注释自认「undercounting would let the guest exceed the intended cap」选择保守方向，但代价是计数泄漏。
- 触发条件：HCN release 失败（低频）。复现难度高，不适合作为新 issue 主候选。
- 额外观察：Allocate 分支 `releasePortOnError.release()` 在 SUCCEEDED/FAILED 后无条件调用——FAILED 时 scope_exit 可能再调一次 m_releasePort（双释放疑点），需确认 HCN API 容忍度。

### 新发现 B：SO_REUSEADDR 同四元组重连差异（已证伪，2026-08-20 三环境对照）
- 现象：guest 内「客户端主动关闭后，SO_REUSEADDR + 固定源端口重连同一四元组」WSL 失败（errno 99），原生 Linux 成功。
- 三环境对照（同一语义脚本）：原生 Linux（docker-desktop 容器）OK 0.00s；WSL guest FAIL 0.00s；**Windows 原生（go 1.26.5，SO_REUSEADDR 设置确认成功）FAIL 0.00s（WSAEADDRINUSE）**。
- 结论：WSL 行为与 Windows 原生一致，根源是 Windows TCP 栈语义（SO_REUSEADDR 不用于四元组重用），非 Consomme 独有缺陷。即使 Consomme 向 host socket 传递 SO_REUSEADDR 也不会改变结果。
- 定性：WSL 与 Linux 的架构性语义差异（WSL 网络走 Windows 栈），官方大概率标 by design -> 不作为新 issue 候选，候选已删除（issue #8 已删）。
- 沉淀教训：对照实验必须三环境（原生 Linux / WSL / Windows 原生），单侧对照会误判「Consomme 缺陷」为「架构差异」。

### 新发现 C：性能税（`#41051` + `#41125` 引入）——评论素材，非新 issue
- 30 号文档已详述。官方可用「设计如此」回应，按沉淀规则七降级为评论素材。

## 四、结论与建议

1. 新 issue 主候选池目前只有「新发现 A」（源码级真实缺陷但难复现）与「新发现 B」（已公开未独立）。两者都不满足「正式版可复现 + 无人提过」双条件。
2. 新发现 B 已证伪（Windows 原生同行为，架构差异非缺陷）。当前无满足「老 + 未修 + 可复现 + 无人提过」的候选，新 issue 方向回到待办研究 issue #9（反向挖掘 + 修复边界扫描）。
3. 后续若想扩大新 bug 挖掘面：`#41085` 双释放疑点（低风险验证）、wslc 端口发布路径（`#41052` 家族）、保留 range 与 host range 重叠时的 seed 计算边界。
