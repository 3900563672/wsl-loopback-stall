# 16 openvmm/WSL “为什么这么写”溯源：git 历史实证 + 版本缺陷区间重大修正

> 日期：2026-08-19 ｜ 类型：只读研究（git 历史）｜ 状态：完成
> 材料：/root/research/openvmm（openvmm blobless clone，HEAD eef8b22e）、/root/research/WSL（microsoft/WSL clone，HEAD 1e14a49b）
> 背景：12 号文档已把“机制路径”钉到源码行号；本文回答“为什么这样写”，并对版本缺陷区间的两处错误归因做勘误（#40187 归属、#41125/#41051 首发版本）。

## 一、结论摘要

1. **openvmm net_consomme 的三个关键机制全部始于闭源时代，公开历史从未触碰**：TIME_WAIT 无 timer（tcp.rs:2006/2022 TODO）、禁 SYN 重传（windows.rs:28-50 SIO_TCP_INITIAL_RTO）、bind 无 SO_REUSEADDR + listen(10)，全部存在于初始开源提交 304657e9（2024-10-03）；2024-10 至今的公开提交中，TIME_WAIT / SO_REUSEADDR 相关修改 **0 条**（全史 grep 无命中）。不是“最近改坏了”，是“从未进入路线图”。
2. **net_consomme 的 TCP 状态机是自研实现**：Cargo.toml 只启用 smoltcp 的 wire/checksum/dhcpv4 能力（socket-tcp 未启用），tcp.rs 是微软自研栈；TimeWait 状态存在但 timer 是 TODO——嵌入式栈“先有状态机、后补 timer”的典型未完成项。
3. **WSL 侧 GnsPortTracker 是 2026 年补丁式演进**：5 个提交各对应一个真实报告场景（VSCode Remote、端口跟踪竞态、accept 隐式绑定、listen-only 应用、线程 bind），每个只修报告场景，缝隙仍漏——与我们的 churn/端口 0 观测一致。
4. **【重大勘误】2.7.8.0 的 guest 侧 tracker 已含 #40187**（inline 端口 0 解析）：#40187（3f00f988，04-22）修改的是 `src/linux/init/GnsPortTracker.cpp`（guest 侧，随 WSL 应用发布），2.7.8 tag（06-05）经 merge-base 验证包含。此前 20/21 号与本文前身“本机 wsldevicehost.dll（04-20 构建）不含 #40187”是**类别错误**——#40187 不在 DLL 里，DLL 构建日期只约束 host 侧 glue（ConsommeNetworking + net_consomme）。
5. **与 ETW 证据（22 号：host 侧 0 个 port request 事件）直接对应的缺失修复是 #41051（PIDFD_THREAD）**：2.7.8 的 DuplicateSocketFd 用 `pidfd_open(Pid, 0)`，非主线程（tid ≠ pid）bind(0) 时 pidfd_open 失败 → 注册请求从未发出 → host 0 事件。我们的 Go 探针 bind 跑在 Go runtime 非主线程上，机制链条完全自洽。
6. **发布线勘误**：#40287 首发 2.8.5+（05-13）；#41125（listen autobind）与 #41051（PIDFD_THREAD）首发 **2.9.5（2026-08-11）**；2.7.x 全系（至 2.7.12，08-17）与 2.8.x 均不含。本文前身“#41125 从 2.7.11 起”表述错误。

## 二、openvmm net_consomme：三个机制的来源与“为什么”

### 2.1 TIME_WAIT timer TODO（tcp.rs:2006 / 2022）

- 证据：`git log -L '/TODO: start timer/,+2:...tcp.rs'` 只返回初始提交 304657e9；`git log --all --grep='TIME_WAIT|SO_REUSE|reuseaddr' -i` 全史 0 命中。
- 行为：FinWait2 收 FIN → TimeWait（无 timer）；TimeWait 收包只回 ACK（TODO: restart timer）；唯一移除路径是合法 RST（RFC 5961 校验）→ 残留可长达实测 81~187s。
- 为什么：VM 场景端口固定、连接生命周期短、新 VM 即新内核命名空间，TIME_WAIT 复用压力从未出现；WSL loopback 把“高频端口生命周期”引入后成为瓶颈。

### 2.2 禁 SYN 重传（windows.rs:28-50）

- 证据：`disable_connection_retries`：TCP_INITIAL_RTO_PARAMETERS { Rtt=0xffff(UNSPECIFIED), MaxSynRetransmissions=0xfe(NO_SYN_RETRANSMISSIONS) }；git blame 显示随初始提交导入，后续仅 5ce7c6dc 改过空指针参数写法。
- 为什么：刻意语义设计——统一 Linux“立即失败”语义、防 guest 误判对端存在 TCP 栈；前提是“listener 必须先就绪”（同步注册链），任何一环延迟即暴露（半黑洞/全黑洞）。

### 2.3 bind 无 SO_REUSEADDR + listen(10)

- 0bb5cf75（本机 DLL 锚定点）核实：`TcpListener::new` = Socket::new → bind(src) → listen(10)，无 SO_REUSEADDR（tcp.rs:1385-1408）；本机 DLL 走 bind_tcp_port RPC 路径。
- `create_bound_socket`（net_consomme/src/lib.rs）是 4a73bb30（#3364，2026-04-29，openvmm CLI hostfwd）才引入，**晚于**本机 DLL 锚点 0bb5cf75（04-19）——本机 DLL 无此函数，16 号文档引用的 lib.rs 行号需注意版本。
- 5c773aaf（#3668，2026-06-05）只修“同端口不同族”冲突（IPv6 set_only_v6）——修复范围只到族冲突，未触及 TIME_WAIT 复用（0 条相关提交佐证）。
- 为什么：与 2.1 同源——VM 端口固定，bind 复用冲突从未成为问题。

### 2.4 Windows 侧排他锁（host glue）

- 证据：WSL 初始开源提交 697572d6（2025-05-15）中 `src/windows/service/exe/VirtioNetworking.cpp` 已有 3 处 `m_lock.lock_exclusive()`（89/222/269 行）；历次重构（#13760 / #13783 / #13788 / #40873 改名 Consomme）原样保留。
- 为什么：刻意一致性设计——“bind 返回 = localhost 转发一定可用”，正确性优先于性能；代价是 churn 时全串行（实测 ~96 bind/s 吞吐恒定）。

## 三、WSL GnsPortTracker：补丁式演进（每个补丁 = 一个真实场景）

| 提交 | PR | 日期 | 内容 | 触发场景 | 2.7.8.0 |
| --- | --- | --- | --- | --- | --- |
| ef8e1c8d | #14333 | 2026-03-13 | 端口 0 bind 跟踪（seccomp 拦截 + ResolvePortZeroBind） | VSCode Remote-SSH 连不上 | ✅ 含 |
| 3f00f988 | #40187 | 2026-04-22 | 端口 0 解析 inline（去 dup socket 异步竞态） | 端口跟踪与关闭竞态（#40109） | ✅ 含 |
| ee92475a | #40287 | 2026-05-12 | accept() 隐式绑定跟踪（mirrored） | accept 连接端口被误释放 | ❌（2.8.5+） |
| 96b220c7 | #41125 | 2026-07-23 | listen() 隐式 autobind 拦截（ParseListen） | listen-only 应用 127.0.0.1 不可达（#41117） | ❌（2.9.5+） |
| 55d45784 | #41051 | 2026-08-05 | pidfd_open 加 PIDFD_THREAD | 线程内 bind(0) 不被跟踪（#41039） | ❌（2.9.5+） |

特征：每个提交正文都点名具体报告场景与用户影响；修复只覆盖该场景，未覆盖的并发/退化路径仍出问题——与 07/20/21 号文档的 churn/窗口式观测一致。

## 四、版本缺陷区间重大修正

### 4.1 #40187 归属修正（guest 侧，2.7.8.0 已含）

- #40187 修改 `src/linux/init/GnsPortTracker.cpp`，编译进 guest 侧 init，随 WSL 应用（Store 包）发布；2.7.8 tag 包含（merge-base 验证）。
- 2.7.8.0 的端口 0 处理顺序（tag 2.7.8 代码实证）：`TrackPort`（显式端口）→ `CompleteRequest`（放行 bind，返回 0）→ `ResolvePortZeroBind` inline → `HandleRequest`（同步事务到 host）。bind 返回 0 与注册完成是两件事——与 20 号 E 实验（立即自连 0%）自洽。
- 因此本文前身表格“不含 #40187”、20 号“仍使用 dup socket 异步解析”、21 号“#40187 修复前实现的竞态”等表述**全部作废**，以本文为准。

### 4.2 #41051 是 ETW 证据的直接机制对应

- 2.7.8 的 DuplicateSocketFd（tag 2.7.8:504-507）：`syscall(SYS_pidfd_open, Pid, 0u)`——无 PIDFD_THREAD。
- #41051 提交正文：“The seccomp filter provides the tid instead of the pid. But the pidfd_open call by default requires the first parameter to be a pid. This causes bind calls in threads not tracked by the tracker. Which further causes the local host forwarding to not work for consomme.”
- 对应链条：Go 探针的 bind() 是阻塞 syscall，跑在 Go runtime 非主线程（tid ≠ pid）→ pidfd_open 失败 → ResolvePortZeroBind 无结果 → HandleRequest 从未调用 → host 侧 0 个 port request 事件（22 号 ETW）→ 自连被 RST（10061）。**机制与官方修复方向完全吻合**。
- 保留未解：“窗口式成块失败”（连续分钟级失败后自愈）仍未完全解释——可能与 seccomp 通知循环/线程调度时序相关，需 guest 侧 tracing 证明（超出本机可观测范围），如实标注为推断。

### 4.3 发布线修正

- #40287：2.8.5+（2026-05-13 起）。
- #41125 + #41051：**2.9.5+（2026-08-11 起）**；2.7.x 全系（至 2.7.12，08-17）与 2.8.x 均不含。
- 本文前身“#41125（2.7.11 起）”错误；2.7.11/2.7.12 不含这两个修复。

## 五、对既有文档的勘误清单

| 文档 | 需修正处 | 修正 |
| --- | --- | --- |
| 本文前身 | 第一节表格（#40187 归属）、“2.7.8.0 不含 #40187”、“#41125 从 2.7.11 起” | #40187 含；#41125/#41051 首发 2.9.5 |
| 20 号 | 结论 1/2、“与官方问题的对应”第 2 条 | 缺失修复 = #41051（非 #40187） |
| 21 号 | “机制推断”段（#40187 前提） | 同上 |
| 22 号 | 第五节结论 4 前提 | 不冲突；版本对应修正为 #41051 |

各文档已追加“勘误（16 号）”节，历史正文保留不改写（研究链可追溯）。

## 六、对结论表述的影响

- “2.7.8.0 处于官方已知缺陷区间”结论**不变**，锚点后移：缺 #41051（线程 bind 追踪）+ #41125（listen 隐式绑定），#40187 已在。
- 新增最强对应：**ETW“host 0 事件”= #41051 所修 bug 的直接实证签名**；#41051 由官方确认（#41039 场景）并于 2026-08-05 合并、2.9.5（08-11）发布——均早于本案例对外提交（08-18）。
- 对外表述建议：“健康态下非主线程 bind(0) 的注册请求从未到达 host（host 侧 0 事件），与后续版本对线程 bind 跟踪的修复（#41051 语义）一致；本机 2.7.8.0 处于该修复发布之前的缺陷区间。”（对外文本不提 PR 编号，只描述语义。）
- 升级验证是低成本闭环动作：本机装 2.9.5+ 后重跑 port0_*.go 探针，若成功率恢复 ~100% 即闭环（需用户拍板，见 10 号升级验证）。

## 七、边界与限制（如实记录）

- 本文所有“含/不含”结论基于 microsoft/WSL 与 openvmm 的 git 标签/merge-base，非运行态验证；2.7.8.0 实际行为由 tag 代码 + 本机实测推定。
- “#41051 机制对应”是强推断（ETW 证据 + 官方修复方向吻合），未在本机 guest 侧直接观测到 pidfd_open 失败日志（guest 日志不可读）；若 2.9.5 升级验证通过则升级为闭环。
- openvmm 2020-2024 内部历史不可见（初始提交声明“~5 years closed-source”），“从未进入路线图”仅指公开历史。

## 参考

- openvmm：304657e9（初始导入）、0bb5cf75（本机 DLL 锚点）、4a73bb30（#3364 create_bound_socket）、5c773aaf（#3668 族冲突）、dc6bfc6b（#3620 动态 host 端口）
- microsoft/WSL：ef8e1c8d（#14333）、3f00f988（#40187）、ee92475a（#40287）、96b220c7（#41125）、55d45784（#41051）、697572d6（初始开源）
- 15_DLL指纹比对.md（0bb5cf75 锚定）、20/21/22 号（端口 0 证据链）
- 探针：/root/research/exp2/port0_*.go

---

## 附录（2026-08-19 补）：本地 git 祖先验证——修复存在性从"API 推断"升级为"本地实证"

> 详细证据见 17 号文档；触发原因：2.9.5/2.9.6/2.9.7 无安装资产（GitHub release API 实证仅源码 zip/tar.gz），#71 运行时验证不可执行，转源码级验证（只读）。

- 本地 wsl-src-master-sparse（blob:none）拉取 tag 2.7.8/2.7.12/2.9.3/2.9.4/2.9.5/2.9.6/2.9.7，git merge-base --is-ancestor 验证：
  - 96b220c7（#41125）与 55d45784（#41051）：**2.9.5/2.9.6/2.9.7 全含；2.7.8/2.7.12/2.9.3/2.9.4 全不含**——与本节发布线勘误完全一致，且与运行时实测（2.7.8.0 STALL 91.5%、2.9.4.0 STALL 87.5%）逐版本对齐。
- 修复代码稳定性：git diff 2.9.5 2.9.7 修复文件（GnsPortTracker.cpp/localhost.cpp/main.cpp/seccomp_defs.h）为空；2.9.7..master 仅 1e14a49（VMP 警告，无关）。
- 意义：版本缺陷区间从"compare API + 推断"升级为**双向证据**（复现边界 = 源码缺失边界），#71 关闭条件仅剩"Store 推送 2.9.5+ 后的运行时探针复测"（watch-wsl295.sh 每日监控中）。
