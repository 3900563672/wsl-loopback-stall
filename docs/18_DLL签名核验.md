# 17_wsldevicehost.dll 与开源 net_consomme 对应关系核验（issue #61）

> 日期：2026-08-19 凌晨 ｜ 状态：**完成——结论"可能包含相同代码"升级为"已确认包含"** ｜ 全部操作只读，未动系统

## 一句话结论

本机 WSL 2.7.8.0 实际承载 localhost 转发的 `C:\Program Files\WSL\wsldevicehost.dll`（v1.2.14.0，Microsoft 签名，**当前正被 dllhost.exe 加载**）**已确认内联 openvmm 的 net_consomme Rust 用户态 TCP 栈**：

- 字符串证据：96 处 `oss\vm\devices\net\net_consomme\...` 源码路径、TCP 状态机字段串（FinWait2/TimeWait 等）、`Duplicate TCP bind for port` 翻译串、带源码行号的 WPP 事件名；
- 构建来源证据：Microsoft 内部 CI 路径（`C:\__w\_temp\msrustup_home\...`）与内部 Cargo 源（`microsoft.pkgs.visualstudio.com-8dd33d26ad55b096\...`）、rustc 版本串；
- 对照组：`C:\Program Files\WSL\wslrelay.exe` 无任何 Consomme 标记（旧架构残留文件，本机未运行）。

## 1. 文件本体证据

| 项 | 值 |
| --- | --- |
| 路径 | `C:\Program Files\WSL\wsldevicehost.dll`（**注意：不在 `C:\Windows\System32\lxss`**，早期判断路径有误，System32\lxss 只有 wslsupport.dll） |
| FileVersion | 1.2.14.0 |
| FileDescription | Microsoft WSL Device Host Library |
| CompanyName | Microsoft Corporation |
| Authenticode | **Valid**（Signature verified） |
| SHA256 | `3044ACEA9540A8A3AD4B3539F8B336CC5B5AA6C056B7A52F6FBE8DE141E1D66E` |
| 运行状态 | 正被 dllhost.exe 进程加载（模块路径 = 本文件，2026-08-19 01:2x 实测） |
| 文件时间 | 2026-04-20（同目录 wsl.exe 为 2026-06-06 / 2.7.8 发布日）→ DLL 更新节奏独立，未锁定与 WSL 版本号映射 |
| 字符串规模 | ASCII 12,728 条 + UTF-16 36 条（`strings -a -n 4`） |

## 2. 字符串签名（决定性证据）

### 2.1 net_consomme 源码路径（`net_consomme` 共命中 96 次）

```
oss\vm\devices\net\net_consomme\consomme\src\tcp.rs
oss\vm\devices\net\net_consomme\consomme\src\udp.rs
oss\vm\devices\net\net_consomme\consomme\src\lib.rs
oss\vm\devices\net\net_consomme\consomme\src\dhcp.rs
oss\vm\devices\net\net_consomme\consomme\src\dhcpv6.rs
oss\vm\devices\net\net_consomme\consomme\src\icmp.rs
oss\vm\devices\net\net_consomme\consomme\src\dns_resolver\dns_tcp.rs
oss\vm\devices\net\net_consomme\consomme\src\tcp\assembler.rs
oss\vm\devices\net\net_consomme\src\lib.rs
```

这些是 WPP/事件宏编译时嵌入的源路径（`file!()`），**只可能来自 net_consomme crate 本体**。

### 2.2 特征字符串（与 12 号文档源码机制互相印证）

| 字符串 | 命中 | 说明 |
| --- | --- | --- |
| `Duplicate TCP bind for port` | ✅（实际串 `recvDuplicate TCP bind for port`） | **开源仓库无此串** → 是闭源 glue 对 openvmm `tcp.rs:713` `BindError::PortAlreadyBound` 的翻译串（12 号文档断言成立） |
| `PortNotBound` | ✅（错误枚举名串，`...IoBadTcpStatePortNotBoundUnsupportedDhcpv6...`） | 对应 `tcp.rs:735` `BindError::PortNotBound` |
| `PortAlreadyBound` 字面串 | ❌ 未命中（只有其翻译串） | Rust 枚举变体名不会被 stringify；符合预期 |
| TCP 状态机 | ✅ `Connecting SynSent SynReceived Established FinWait1 FinWait2 CloseWait Closing LastAck TimeWait` + 小写变体 | 与 `tcp.rs` TCP 状态枚举逐名一致 |
| 连接结构字段 | ✅ `proxy_for_guest_port loopback_port` + `rx_buffer rx_window_cap rx_seq needs_ack ...` | `tcp.rs TcpConnection` 结构字段（loopback 代理模型） |
| 校验错误文案 | ✅ `unacceptable segment number / missing ack bit / ack newer than sequence / invalid window scale` | `tcp.rs` 报文校验错误文案 |
| `failed to initialize DNS resolver, falling back to using host DNS settings` | ✅ | openvmm `consomme/src/lib.rs:822` 原文存在（消息文本一致，行号漂移见第 4 节） |

### 2.3 WPP 事件名（带源码行号，微软可解码）

```
consomme::tcp::message_error（tcp.rs:354 等数十个行号）
consomme::udp::message_dropped_ratelimited_error（udp.rs:466/472/480 等）
net_consomme::message_err（net_consomme/src/lib.rs:288/363/372/530）
consomme::dns_resolver::dns_tcp（dns_tcp.rs:165/199）
consomme::dhcpv6::message_error / consomme::ndp::message_error / consomme::icmp ...
```

与 WPR trace 中 `wsl_devicehost（WPP）` provider 26,036 条事件互证：**本 DLL 就是 trace 里那个承载中继的组件**。

### 2.4 Rust 工具链与构建来源（额外收获，来源证据极强）

```
/rustc/13948834cf6ba6943cbddc752b86e5b9e3585c03/library/core/src/...
C:\__w\_temp\msrustup_home\packages\rust.tools.stable-llvm-x86_64-pc-windows-msvc.1.94.0-ms-20260303.10037\tools\lib/rustlib/src/rust\library\alloc\src\...
C:\__w\_temp\cargo_home\registry\src\microsoft.pkgs.visualstudio.com-8dd33d26ad55b096\anyhow-1.0.99\src\...
C:\__w\_temp\cargo_home\registry\src\microsoft.pkgs.visualstudio.com-8dd33d26ad55b096\slab-0.4.11\src\lib.rs
C:\__w\_temp\cargo_home\registry\src\microsoft.pkgs.visualstudio.com-8dd33d26ad55b096\async-task-4.7.1\src\utils.rs
```

- `C:\__w\_temp\` = Microsoft 内部 CI（Azure DevOps）构建机路径；
- `microsoft.pkgs.visualstudio.com-8dd33d26ad55b096` = Microsoft 内部 Artifacts Cargo 源；
- rustc 1.94.0-ms-20260303（内部版 2026-03-03）→ 与文件时间 2026-04-20 一致（构建窗口合理）。
- Rust panic 文案全套在库内（`internal error: entered unreachable code` / `called \`Option::unwrap()\` on a \`None\` value` / `index out of bounds` 等）。

### 2.5 宿主 glue 与 virtio（同库内还内嵌其他 openvmm crate）

```
hyper-v\wsldevicehost\src\virtio_net.rs、hyper-v\wsldevicehost\src\virtiofs.rs   ← 设备宿主 crate（wsldevicehost 本体）
oss\vm\devices\virtio\virtio_net\src\lib.rs、oss\vm\devices\virtio\virtio_net\src\buffers.rs  ← openvmm virtio_net 也内嵌
```

### 2.6 对照组：wslrelay.exe

- `C:\Program Files\WSL\wslrelay.exe`（3.4MB，28,345 条 ASCII 字符串）对 `consomme / net_consomme / Duplicate TCP bind / ModifyOpenPorts / PortAlreadyBound` 等标记 **0 命中**；
- 与既有判断一致：本机是 Consomme 模式，wslrelay 是旧架构残留文件（从未运行；WPR 中 PortTrackerServer_WPP 未录亦互证）。

## 3. 导出签名比对

- `wsldevicehost.dll` 导出表：**0 项**；`wslrelay.exe` 导出表：**0 项**（PE 解析脚本 `research/pe_export.py`，逐名字解析）。
- 两二进制均无命名导出 → DLL 经 COM/注册表（dllhost 承载）加载，不按名链接 → **"导出签名"维度不适用**，字符串签名是正确且充分的手段。此结论已写入 issue #61 正文口径。

## 4. 版本漂移与局限（诚实声明）

1. **行号不一致**：DLL 内 WPP 行号（如 `tcp.rs:354`）与 openvmm master 快照（2026-08-18 拉取）**逐行对不上**（快照中 354 行是 `tx_segment_size` 字段声明）。原因：DLL 构建于 2026-04（rustc 20260303），openvmm master 已前进 4 个多月 → 行号漂移属正常。**路径结构与事件名一致是决定性证据，行号不是**。
2. **无法定位精确 commit**：字符串只给出 crate 名与路径，不给出 git commit；DLL 内也没有版本号能直接映射到 openvmm tag。
3. **无法反编译对比实现差异**：只证明"包含 net_consomme"，不证明"与 master 行为逐字节一致"；glue 层（端口编排/翻译串所在）仍闭源。
4. **DLL 与 WSL 版本映射未锁定**：wsldevicehost.dll 文件时间（04-20）≠ wsl.exe（06-06）；不能据此断言"2.7.8 出厂带此 DLL"，只能说"本机当前加载的 DLL 包含 net_consomme"。

## 5. 复现方法（他人可复核，全部只读）

```powershell
# 文件本体
Get-Item 'C:\Program Files\WSL\wsldevicehost.dll' | Select -Expand VersionInfo
Get-AuthenticodeSignature 'C:\Program Files\WSL\wsldevicehost.dll'
Get-FileHash 'C:\Program Files\WSL\wsldevicehost.dll' -Algorithm SHA256
Get-Process -Name dllhost | Select -Expand Modules | Where FileName -match 'wsldevicehost'

# 字符串（WSL 内）
cd '/mnt/c/Program Files/WSL'
strings -a -n 4 wsldevicehost.dll > /tmp/dll_ascii.txt
strings -a -n 4 -e l wsldevicehost.dll > /tmp/dll_utf16.txt
grep -i -E 'net_consomme|Duplicate TCP bind|PortNotBound|proxy_for_guest_port|FinWait2|wsldevicehost' /tmp/dll_ascii.txt

# 导出表（research/pe_export.py）
python3 /mnt/c/Users/hh/OneDrive/research/pe_export.py '/mnt/c/Program Files/WSL/wsldevicehost.dll'
```

## 6. 对 issue 流程的意义

1. **12 号文档"剩余不确定①：wsldevicehost.dll 内联 net_consomme 与 openvmm master 的版本差异"** → 前半句（内联）已确认，只剩版本差异细节；
2. v3 评论中"Consomme 由 wsldevicehost.dll 承载"从推断升级为**已确认事实**（字符串 + 进程加载 + WPR provider 三证合一）；
3. 若官方追问"你凭什么说这个 DLL 包含开源栈"→ 直接引用本文证据表；
4. 边界不变：**这仍不构成根因证明**（issue #61 只回答"代码对应关系"，不回答"为什么卡"）。
