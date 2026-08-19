# 22 端口 0 注册丢失的 Windows 侧 ETW 实证：请求从未到达 wsl_devicehost（21 号待办① 闭环）

> 日期：2026-08-19 ｜ 类型：健康态抓包（需管理员权限，已完成）｜ 状态：完成
> 对应：25_port0注册窗口.md 待办①（GNS/wsldevicehost ETW 抓包定位注册丢失点）
> 证据目录：logs/evidence/port0-etw-2026-08-19/

## 一、目标与方法

21 号文档待办①：用 Windows 侧 ETW 定位端口 0 注册失败的确切原因（getsockname 超时 vs pidfd 失败 vs 消息丢失）。

方法：`logman -ets` 启用 wsl_devicehost WPP → 探针循环跑 mix（交替 bind(0)/显式）直到故障窗口 → `tracerpt -of XML` 解码（03 号文档 156 行确认该命令在本机可解出 wsl_devicehost 的 EventData 字段）。

## 二、重要修正：抓 PortTrackerServer_WPP（090bf343）是死路

- `090bf343-4490-42d3-b273-8af174d314fb`（官方 wsl.wprp 的 PortTrackerServer_WPP）在 WSL-Networking 官方日志包（08-18 22:27）中 0 条事件，本机 logman 直启也 0 条 → 该组件（wslrelay 旧架构）在 Consomme 模式下不运行（12 号文档判断成立）。
- 正确目标：wsl_devicehost WPP = `9d6c7b9e-2581-4d8a-b8c5-b90b4a17094a`（官方 wsl.wprp 第 270 行 EventProvider Id="wsl_devicehost"）。官方日志 26,036 条，tracerpt -of XML 可解码为 Microsoft.WSL.DeviceHost（PID 4140 = dllhost.exe 承载），核心事件：
  - virtio-net port request：target=wsldevicehost::virtio_net + port_info_string=tag=loopback0;port_number=NNNN;listen_addr=::1（host 收到 guest 端口注册请求的唯一事件）
  - consomme::tcp error 事件（os error 10061 等）

## 三、抓包参数（可复现）

```powershell
logman create trace pt2 -p "{9d6c7b9e-2581-4d8a-b8c5-b90b4a17094a}" 0xffffffffffffffff 5 -o pt2.etl -max 1024 -bs 256 -nb 32 128 -ets
# 跑探针（循环直到 FAIL，见下）
logman stop pt2 -ets
tracerpt pt2.etl -of XML -o pt2.xml -summary pt2-summary.txt -lr
```

探针（WSL guest 侧）：local/port0/port0_mix.go 预编译为 port0_mix_bin，循环最多 8 轮，每轮 40 次交替 bind(0)/bind(显式)（sleep 1.5s 后自连），出现 FAIL 即停：

```bash
for i in 1 2 3 4 5 6 7 8; do port0_mix_bin >> mix.log 2>&1; if grep -q FAIL mix.log; then break; fi; done
```

## 四、抓包结果（2026-08-19 11:05:12–11:06:12，62 秒）

- mix round 1 命中故障窗口：idx 10→38 连续 15 个 zero 端口全 FAIL，显式端口全 OK，34/36/38 为 OK 恢复段（窗口自愈）。
- ETL 645 事件（643 个 wsl_devicehost，0 丢失）。

### 决定性对照：Windows 侧 port request 事件 vs 探针结果

| 探针结果 | 数量 | host 侧 virtio-net port request 事件 |
| --- | --- | --- |
| explicit OK | 20 | 20/20 全部有（注册时间与 bind 对齐） |
| zero OK | 5 | 5/5 全部有 |
| zero FAIL | 15 | 0/15 全部没有（NONE） |

### 配套信号（consomme::tcp）

- rst xmit 事件 15 次、os error 10061（WSAECONNREFUSED）15 次，时间与 15 个 FAIL 端口的自连一一对应（每 ~3s 一个）。
- 含义：探针自连 SYN 到达 host 后，因目标端口从未注册（无监听 socket 可转发），host 直接 RST 拒绝 → guest 侧 connect 立即失败（connection refused，非 2s 超时；这也解释了 mix 单轮恒为 60s）。

## 五、结论（修正 20/21 号文档）

1. FAIL 端口的注册请求从未到达 wsl_devicehost（host 侧 0 个 port request 事件）→ 丢失点位于 guest→host 消息路径（guest 未发出，或消息在 vsock/HvSocket 传输中丢失），不是 host 侧 ResolvePortZeroBind 解析失败（getsockname/pidfd）——host 根本没收到请求，谈不上解析。
2. 20 号文档结论 1"注册是异步的：bind 放行后 wsldevicehost 才异步 getsockname + RequestPort"需要修正：故障窗口内连 RequestPort 这一步都未发生（host 无事件）；异步竞态描述只适用于"host 收到但解析慢/失败"的假设，本轮证据将该假设排除。
3. 21 号文档"机制推断"段（ResolvePortZeroBind 取不到端口）同理修正：注册丢失在更上游；每进程独立（pair 实验）与"消息路径 per-socket 处理"自洽。
4. 与 07 号文档（churn 时 Windows 侧 BindEndpoint 事件连续）不冲突：那是另一个 provider（网络栈层）的另一实验；本轮是 wsl_devicehost 应用层的注册事件，两者层级不同，不混用。

## 六、边界与限制（如实记录）

- 本轮只能证明"host 未收到"，无法区分：guest 侧 stub 未发送 vs 消息在通道中丢失。要区分需 guest 侧 tracing（vsock/9p 通道层），超出本机可观测范围。
- 窗口内 0 事件也可能包含 host 侧丢弃（ETW 0 丢失 = 我们捕获端无丢失；host 应用层若主动丢弃不记事件则不可见——但显式端口同窗口全记，说明 host 记日志逻辑正常）。
- 明确不主张为新 bug：继续沿用 21 号文档立场（官方 #40187 已承认同类问题并修复；本证据作为 2.7.8.0 版本缺陷区间的实证）。
- 对结论的意义：健康态下"注册请求未达 host"是可一键复现、host 侧证据闭环的版本缺陷实证；与 #40187 修复方向（去掉异步 dup fd 路径）不矛盾——若 guest 侧发送依赖该竞态路径，修复后此现象应消失（本机无修复版可对照，如实标注为推断）。

## 七、证据文件（已归档 logs/evidence/port0-etw-2026-08-19/）

- pt2.etl（2.3MB 原始 ETW，62s）
- pt2.xml（tracerpt 解码 XML，578KB，含全部 643 个 wsl_devicehost 事件）
- pt2-summary.txt（事件统计）
- port0_mix_pt2.log（探针输出：15 个 FAIL 端口列表）
- analyze_pt2.py / analyze_pt2b.py（对照分析脚本，可重跑）

## 参考

- 25_port0注册窗口.md（待办① 已完成）
- 24_port0跟踪失败.md（机制修正见第五节）
- 18_实验复现手册.md（tracerpt -of XML 命令出处）
- 官方 wsl.wprp（wsl_devicehost provider 定义第 270 行）
