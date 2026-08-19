# 22 DLL ↔ openvmm 版本指纹比对结果（issue #65 完成）

> 日期：2026-08-19 ｜ 方法：DLL 字符串 WPP 行号集合 vs openvmm 候选 commit 的 tracing/tracelimit 宏命中率

## 一、结论

**wsldevicehost.dll（v1.2.14.0，文件时间 2026-04-20）内嵌的 net_consomme 与 openvmm commit 0bb5cf75（2026-04-19，"virtio_net/consomme: add USO support"）精确吻合**：

- tcp.rs：27/27 行号全中
- udp.rs：7/7 全中
- dns_tcp.rs：2/2 全中
- 时间线吻合：DLL 文件时间 04-20，0bb5cf75 提交 04-19，下一个 net_consomme 提交 4a73bb30（04-29）
- 对比：HEAD（eef8b22e，2026-08）tcp 0/27——行号漂移严重，证实"必须锚定版本"的必要性

**"你分析的不是 DLL 里那版"的质疑就此消除**：可精确声称分析对象即 DLL 内嵌版本（tcp/udp/dns_tcp 逐行号吻合）。

## 二、方法

1. strings 提取 DLL 全部 WPP 源路径行号：84 个（tcp 27、udp 7、dns_tcp 2、lib 48）
2. 对 7 个候选 commit（HEAD eef8b22e、0bb5cf75、4b326a12、201024c7、6005b8cd、624ab07e、3a46a484），逐个检查"行号对应行是否为 tracing/tracelimit 宏调用"
3. 命中率最高的 commit 即 DLL 版本（WPP 事件名带的行号 = 宏调用行）

## 三、结果表

| commit | 日期 | tcp | udp | dns_tcp | 判断 |
| --- | --- | --- | --- | --- | --- |
| eef8b22e (HEAD) | 2026-08 | 0/27 | 0/7 | 0/2 | ✗ |
| **0bb5cf75** | **2026-04-19** | **27/27** | **7/7** | **2/2** | **✓ 精确锚定** |
| 4b326a12 | 2026-03-24 | 27/27 | 0/7 | 2/2 | 部分（tcp.rs 未变，udp.rs 已变） |
| 201024c7 | 2026-03-20 | 23/27 | 0/7 | 2/2 | ✗ |
| 6005b8cd | 2026-03-10 | 6/27 | 0/7 | 2/2 | ✗ |
| 624ab07e | 2026-03-16 | 7/27 | 0/7 | 2/2 | ✗ |
| 3a46a484 | 2026-03-13 | 7/27 | 0/7 | 2/2 | ✗ |

- lib.rs 的 48 个行号为多 crate 混合（net_consomme/src/lib.rs + consomme/src/lib.rs + 其他依赖 crate 的 lib.rs 均可能），两个候选 lib.rs 合计命中 7/48，不用于定版；tcp/udp/dns_tcp 已覆盖核心结论（TimeWait、注册、黑洞机制均在 tcp.rs）
- udp.rs 是区分 0bb5cf75 与 4b326a12 的关键：0bb5cf75 为 USO 支持（改动 udp.rs），DLL 的 udp 行号匹配 0bb5cf75 而非 4b326a12

## 四、关键机制在锚定版本的确认（20 号文档结论适用性）

| 机制 | 0bb5cf75 存在 |
| --- | --- |
| TimeWait "TODO: start timer" / "TODO: restart timer" | ✓（tcp.rs） |
| disable_connection_retries（SIO_TCP_INITIAL_RTO / MaxSynRetransmissions） | ✓（windows.rs + tcp.rs） |
| connect 超时静默不发 RST（"Avoid resetting so that the guest"） | ✓（tcp.rs） |
| SO_REUSEADDR | ✗ 不存在（与 HEAD 一致，无此设置） |

结论：20 号文档基于 HEAD 的机制分析全部适用于 DLL 内嵌版本（tcp/udp/dns_tcp 部分）。

## 五、局限

- 0bb5cf75 与 DLL 之间可能还有微软内部未开源的净微调（无法排除）；开源可见最近匹配即 0bb5cf75
- lib.rs 无法定版（多 crate 混合），但核心机制不依赖 lib.rs 行号
- 后续若 openvmm 有新提交，可用同方法重新比对

## 六、材料

- 脚本：/root/research/full-fingerprint.sh（可复用，改 DLL 路径与候选 commit 即可）
- 数据：/tmp/dll_lines.txt（DLL 行号集合）
