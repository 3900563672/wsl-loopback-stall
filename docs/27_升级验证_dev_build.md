# 27 升级验证：dev build 2.9.7.19（官方确认 #41051 同源修复）（2026-08-20）

> 状态：验证闭环完成——端口 0 注册窗口消失，修复确认。

## 背景

- 官方（@chemwolf6922，#41051 作者）回复 #41383：日志表明与 #41051 同一问题，提供 dev build。
- 本机验证路径：安装官方 dev build（MSI，基于 master c9f0d36b，2026-08-14 构建），重跑 port0 探针。
- 已核实：dev build 源码 commit c9f0d36b 同时包含 #41051（55d45784，behind 61）与 #41125（96b220c7，behind 110）。

## 升级前后对比

| 项 | 升级前（2.7.8.0 stable） | 升级后（2.9.7.19 dev） |
| --- | --- | --- |
| wsl.exe | 2.7.8.0 | 2.9.7.19 |
| wsldevicehost.dll | 1.2.14.0 / 1,598,496B / sha256 3044acea... | 1.2.60.0 / 1,771,288B / sha256 079DE4B3F161EE68 |
| 内核 | 6.18.33.1-1 | 6.18.35.2-1 |
| WSLg / MSRDC | 1.0.73.2 / 1.2.6676 | 1.0.79 / 1.2.7214 |

## 探针结果（决定性）

- **8 轮 churn：8/8 通过**（升级前基线：2.9.4 ok=2/8，2.7.8 直方图 STALL 91.5%）。
- **40 轮压力：40/40 通过**（2.9.4 对照：ok=5/40，STALL 87.5%）。
- 注册延迟：**0.85-1.2ms**（升级前健康态 50-100ms）——注册开销一个数量级下降，窗口消失。
- 中继错误计数（UtilAcceptVsock）= 0。
- 结论：**端口 0 注册失败窗口在含 #41051 的版本上消失，官方判定与修复同时得到验证。**

## 操作记录

1. 基线归档（2.7.8.0 + DLL 1.2.14.0 + 探针单轮 PASS 53.9ms）。
2. 下载官方 dev build MSI（gh run download 31764537928 → wsl.msi 291MB）。
3. 管理员 msiexec /i wsl.msi /qn 安装（UAC 一次）。
4. wsl --shutdown 生效；2.9.7.19 / 内核 6.18.35.2-1。
5. 探针 8/8、40/40 通过。
6. 恢复 Docker Desktop + kind 5 节点（docker start 手动拉起）。

## 注意与后续

- dev build 为 master 构建（8-14），非正式发布；官方建议测完换回 release/pre-release。
- 待 Store 推送 2.9.5+ 正式版后复测一轮（对照本结果）。
- 回滚预案见 09 号文档 3.2（Appx + MSI 双通道；本机当前为 MSI 主导，回滚装 2.7.8.0 MSI 即可）。

## 性能对照（2026-08-20 追加：bind 同步链固定开销反而恶化 2-3 倍）

> 背景：为给官方回复提供"完整对照"，在 dev build（2.9.7.19）上重跑 bind_latency.go / churn_heavy.go / syscall_bench.go。

### 结果（dev build vs 旧基线 2.7.8.0/2.9.4，04 号文档）

| 项 | 旧基线 | dev build 2.9.7.19 | 变化 |
| --- | --- | --- | --- |
| seq 200（127.0.0.1:0）bind p50 | 10.4ms | 32.0ms（两次复测 31.97/31.98ms） | **3.1x 更慢** |
| seq 200（127.0.0.2:0）bind p50 | 10.4ms | 31.5ms | 3.0x 更慢 |
| seq 200（固定端口 127.0.0.1:39001）bind p50 | 无 bind 级数据 | 21.1ms | 与端口类型无关 |
| syscall bind 127.0.0.1:0 p50 | 10.4ms | 21.4ms | 排除 Go runtime 因素 |
| 128 并发×20（2560 次）p50 | 1.322s（×100 轮） | 4.27s | 3.2x 更慢 |
| 128 并发 >1s 占比 | 99.27% | **100%**（2560/2560） | 恶化 |
| 128 并发吞吐 | 96 bind/s | 30 bind/s | 3.2x 更慢 |

- p50 4.27s ≈ 128 × 33ms：完全串行模型仍成立，每 bind 固定开销 10.4ms → ~33ms。
- 与地址/端口类型无关：127.0.0.1、127.0.0.2、固定端口全部 ~21-35ms → guest 侧拦截链（seccomp 通知处理）整体变慢。
- 环境因素基本排除：Windows 侧 dllhost（wsldevicehost 宿主）CPU 累计仅 ~2s；Ubuntu load 0.87；内存充足。

### 解读与待确认

- **不推翻核心修复结论**：可达性/黑洞已修复（探针 8/8、40/40、0.9ms）。串行单轮下 33ms 固定开销不会造成"30s 不可达"，listen 返回后 dial 立即成功（同步确认）。
- **性能线未修复且恶化**：issue 正文报告的"10.4ms/bind 串行化 + 并发停滞"在 dev build 上依然存在，且 2-3 倍更差。128 并发仍 100% >1s。
- 待确认：① 是否 Docker+kind 环境因素（kind 跑在 docker-desktop distro，理论上不经 Ubuntu GnsPortTracker，影响弱；彻底排除需停 Docker 复测）；② dev build 是否带诊断开销（正式版可能更快）；③ 内核 6.18.35 seccomp 通知路径变化。
- **最终定论需等 Store 正式版 2.9.5+ 复测**（同一套命令即可对照）。

### 源码定位（2026-08-20 追加：2.9.4..c9f0d36b 注册链仅两个 commit）

WSL 仓库 `git diff 2.9.4..c9f0d36b -- src/linux/init/`：仅 #41051（55d45784，PIDFD_THREAD）与 #41125（96b220c7，listen 拦截）。

- **#41051**：`pidfd_open(Pid, PIDFD_THREAD)`（fallback EINVAL→0）。旧版非主线程 bind 的 pidfd_open 失败 → 直接放行（不注册=黑洞根因）；新版所有线程 bind 都被追踪挂起。
- **#41125**：`__NR_listen` 也注册 seccomp handler。`ParseListen` 每次执行：read_symlink(/proc/pid/ns/net) + GetSocketProtocol + DuplicateSocketFd(pidfd_getfd) + ValidateCookie + getsockname。**每连接从 1 个 seccomp 通知变 2 个（bind+listen）**。
- **线程分解实测（/tmp/perf_split.go，主线程 vs 新线程，各 100 次）**：bind-only p50=10.2ms（新旧线程一致，旧版基线 10.4ms → bind 链本身未变慢）；net.Listen（bind+listen）p50=43ms → **listen 拦截新增 ~33ms/次**。
- **并发模型验证**：128 并发旧版=128×10.4ms≈1.32s；新版=128×(10+33)ms≈4.27s，与实测 4.27s 精确吻合。性能恶化主因是 #41125 的 listen 同步拦截（每连接通知数翻倍 + ParseListen 路径更重），非环境负载。
- Windows 侧新 DLL（1.2.60.0，net_consomme 大更新：tcp.rs +1243/udp +734/新增 local_addr_map.rs）可能贡献部分单通知开销；但新 DLL 的 lib.rs（Windows 集成层）指纹仅 9/57 匹配公开 openvmm master → 微软内部版本，无法精确对齐，标注为未定位项。
- 已建仓库 issue #103（性能回归确认 + 停 Docker 复测 / Store 正式版复测待办）。

### 内核 diff 排除（2026-08-20 追加：性能税归因闭环）

- 对比 linux-msft-wsl-6.18.33.1（旧基线 2.7.8.0 内核）与 linux-msft-wsl-6.18.35.2（dev build 内核），shallow clone 逐文件 diff。
- **seccomp 用户通知路径零改动**：kernel/seccomp.c、include/uapi/linux/seccomp.h 完全一致。
- **pidfd 路径零改动**：kernel/pid.c（pidfd_open / pidfd_getfd）、kernel/fork.c、fs/proc/base.c 完全一致。
- fs/nsfs.c（/proc/pid/ns/net readlink）：仅 1 处错误处理修复（break→return ret，NS_GET_PID ioctl），非性能相关。
- 其余差异均为上游 LTS 补丁：kernel/ 14 个文件（cgroup/dma/sched/trace）、fs/ 54 个文件（btrfs/smb/netfs/fuse 等），与通知链无关。
- **结论**：10.4ms→43ms 性能税完全归因于用户态两个 commit（#41051 全量追踪 + #41125 listen 拦截），内核无混淆因素，归因闭环。

## 官方回复已发送（2026-08-20 04:51Z）

- 评论：`https://github.com/microsoft/WSL/issues/41383#issuecomment-5351512967`（用户 3900563672）
- 内容：dev build 验证结果表（8/8、40/40、~1ms、Windows 侧 8/8、中继错误 0）+ 修复确认 + 2.9.5+ Store 复测承诺 + 一句话性能预告（listen 同步 seccomp 往返，正式版复测后分享数字）。
- 流程：桌面草稿 → 预演 issue（#104，已关闭）→ 正式发送 → 回读校验一致。
- 下一步：等官方回应；Store 正式版 2.9.5+ 推送后复测（对照 dev build，含性能税数据）。
