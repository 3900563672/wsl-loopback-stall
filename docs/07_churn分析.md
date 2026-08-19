# 07 churn 窗口 744/6400 差异分析（BindEndpoint 事件计数之谜，已定位）

> 日期：2026-08-19 ｜ 类型：只读源码分析 ｜ 状态：已定位（机制级）
> 数据来源：23_参数验证实验结果.md 实验 5c（WSL 侧 6400 次 bind vs Windows 侧 BindEndpoint(WFP) 事件仅 744 个）
> 源码：wsldevicehost 还原源码 GnsPortTracker.cpp / ConsommeNetworking.cpp

## 问题

128 并发 × 50 轮 = 6400 次 `net.Listen("tcp", "127.0.0.1:0")`（端口 0，内核自动分配）期间，Windows 侧 BindEndpoint(WFP) 事件仅约 744 个（11.6%）。此前疑点："部分 WSL bind 未创建新 TCPIP 端点（wsldevicehost 端点缓存/复用？）"，未定论。

## 根因（源码级确认）

**不是 Windows 侧缓存，而是 guest 侧端口跟踪缓存命中，跳过了 Windows 请求。**

`GnsPortTracker::HandleRequest`（GnsPortTracker.cpp:328）：

```cpp
int GnsPortTracker::HandleRequest(const PortAllocation& Port)
{
    // If the port is already allocated, let the call go through and the kernel will
    // decide if bind() should succeed or not
    if (m_allocatedPorts.contains(Port))
    {
        GNS_LOG_INFO("Request for a port that's already reserved ...");
        return 0;   // ← 不发 Windows 请求 → 不产生 BindEndpoint 事件
    }
    const auto error = RequestPort(Port, true);  // ← 只有新端口走 Windows BindPort
    ...
}
```

- `m_allocatedPorts` 由 `TrackPort` 维护，条目带 **60s 超时**（`c_bind_timeout_seconds=60`，TrackPort 在 GnsPortTracker.cpp:655）。
- 端口 0 的 bind 流程：seccomp 拦截 → dup fd（`ResolvePortZeroBind`，GnsPortTracker.cpp:667）→ bind 放行后 getsockname 解析实际端口 → `HandleRequest(port)` → 端口已在缓存则**直接返回 0**。
- churn 场景下内核 ephemeral 端口被快速复用（socket 秒级 close → TIME_WAIT），加上 60s 缓存窗口，绝大多数 bind 命中缓存。

## 量化验证

- 744 个不同端口 / 6400 次 bind = 每个端口平均被分配 8.6 次（67 秒窗口内）。
- 若端口均匀随机（64511 个可用端口），6400 次期望不同端口 ≈ 6093（95%），与实测 744（11.6%）相差一个数量级——证实端口复用高度集中，与"ephemeral 快速复用 + 60s 缓存"机制吻合。

## 顺带发现：延迟模型的串行点需要修正/补证

- 128 并发下 88.4% 的 bind **不经过** Windows `ConsommeNetworking::ModifyOpenPorts` 排他锁（`m_lock.lock_exclusive()`），但实测 p50=1.322s 仍精确等于 128×10.4ms（04 号文档实验 4）。
- 说明 128 并发下的积压串行点**不是（或不只是）Windows 排他锁**，而是更前端的 seccomp 通知单线程处理队列（GnsPortTracker::Run 的 for 循环：ReadNextRequest → GetCallInfo[读进程内存 + pidfd_getfd + ValidateCookie] → CompleteRequest）。
- 8 并发（实验 1）新端口占比高，Windows 锁排队占主导；128 并发（实验 4）新端口占比低，但每个通知处理仍串行 ~10.4ms——两者恰好都是"并发 × 10.4ms"，宏观结论（延迟=并发×10.4ms、吞吐恒定 ~96 bind/s）不变，但"全局排他锁"作为唯一瓶颈的解释需要修正。
- **建议对照实验（健康态可做，无管理员权限）**：✅ **已验证（2026-08-19，结果见下）** 先预热固定端口集合到缓存（如 100 个端口各 bind 一次），再用 128 并发重复 bind 这 100 个端口（100% 命中缓存）测延迟。若延迟仍 ≈ 并发×10.4ms → 瓶颈确认在 seccomp 通知处理链（guest 侧）；若延迟骤降 → Windows 锁仍是主瓶颈。

### 验证结果（2026-08-19，#72 缓存预热对照，日志 `logs/cache-warm-072.txt`）

- 环境：WSL 2.7.8.0 / 健康态（200 轮直方图归档后）；固定端口，不受 fresh-port 退化窗口影响；`go run research/exp/cache_warm.go`（128 并发，阶段 2/3 各 512 次 bind，全部成功）。
- phase2 缓存命中（预热 100 端口 → 100% 命中缓存）：p50=1.32s / p95=1.36s / p99=1.37s / 吞吐 95 bind/s。
- phase3 未缓存对照（全新端口）：p50=1.39s / p95=1.42s / p99=1.42s / 吞吐 91 bind/s。
- **结论**：缓存命中（不经 Windows 排他锁）与未缓存路径几乎无差，且均 ≈ 128×10.4ms 积压模型 → 瓶颈确认在 guest 侧 seccomp 通知处理链（`GnsPortTracker::Run` 单线程队列），**Windows ConsommeNetworking 排他锁不是主瓶颈**，本假设证实。

## 结论

- 744/6400 已定位：guest 侧端口缓存（m_allocatedPorts，60s 超时）命中跳过 Windows 请求，非 Windows 端点缓存。
- 该机制是**设计预期**（避免重复端口重复注册），不是 bug；对结论无负面影响。
- 对外表述中"全局排他锁 + 同步链积压"宏观成立；内部机制描述建议补充 seccomp 通知处理链这一串行点（12 号文档）。

## 参考

- GnsPortTracker.cpp:328 HandleRequest（缓存命中跳过）
- GnsPortTracker.cpp:655 TrackPort（60s 超时）
- GnsPortTracker.cpp:667 ResolvePortZeroBind（端口 0 延迟解析）
- ConsommeNetworking.cpp:279 ModifyOpenPorts（Windows 侧排他锁 + BindPort）
- 23_参数验证实验结果.md 实验 4/5c
---

## 版本声明与时间线修正（2026-08-19 补充，重要）

**引用版本**：本文引用的 `GnsPortTracker.cpp` 为 microsoft/WSL GitHub **master**（2026-08-19 拉取，还原源码），**不是本机 2.7.8.0 DLL 的反编译**。本机 wsldevicehost.dll 构建于 2026-04-20（14 号文档），WSL 版本 2.7.8.0（发布 2026-06-06）。

**GnsPortTracker 演进时间线（WSL 开源仓库）**：

| 提交 | 合并日期 | 内容 | 2.7.8.0（06-06）DLL（04-20 构建） |
| --- | --- | --- | --- |
| #14333 | 2026-03-14 | 端口 0 bind 跟踪（VSCode remote 场景） | ✅ 包含（ResolvePortZeroBind 来源） |
| #40187 | 2026-04-22 | socket race condition 修复 | ❌ 不含（DLL 04-20 构建） |
| #40287 | 2026-05-12 | accept() 隐式绑定跟踪（mirrored） | ❌ 不含 |
| #41125 | 2026-07-24 | listen() 隐式 autobind 拦截（#41117） | ❌ 不含 |
| #41051 | 2026-08-05 | 端口 0 跟踪在线程下失效（#41039，PIDFD_THREAD） | ❌ 不含 |

**对 744/6400 解读的影响（2026-08-19 二次修正，见 20 号文档）**：
- **主因不是缓存命中，而是注册竞态失败**：2.7.8.0（DLL 04-20 构建）不含 #40187（04-22 合并，端口 0 解析 dup socket 异步 → inline 修复）。实测：端口 0 注册成功率单线程 ~43%、128 并发 2.3%；显式端口 100%。
- 6400 次 bind 中大量从未发起 RequestPort（注册丢失）→ 不产生 BindEndpoint 事件；缓存命中机制（HandleRequest contains）存在但量级上次要。
- #41051（线程 bug，08-05）亦未含，叠加使并发场景塌缩到 2.3%。
- 744 个事件 ≈ churn 期间成功注册数；"每端口 8.6 次复用"的推断不再适用。

**对结论的意义**：
- 官方在 #41039/#41125 已承认并修复（7-24/8-05）"端口 0 线程跟踪失效"和"listen-only 不可达"，**2.7.8.0 同时缺这两个修复**——我们的实验环境正好踩中官方已知缺陷区间，可作为"版本行为差异"的补充证据（需在 2.7.8.0 上实测 listen-only 场景佐证，见 20 号文档）。
- 对外评论（#41286）未引用 GnsPortTracker 版本敏感代码（仅一句存在性描述），无证据误用；net_consomme 引用已锚定 0bb5cf75。
