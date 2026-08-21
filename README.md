<!-- markdownlint-disable MD033 -->
# WSL2 Loopback Stall Case Study

WSL2（Consomme 网络模式）下 **IPv4 回环 + 临时端口 churn 引发的连接停滞（stall）**：完整复现、根因定位、证据链与上游互动记录。

<div align="center">

[![Docs](https://github.com/3900563672/wsl-loopback-stall/actions/workflows/docs.yml/badge.svg)](https://github.com/3900563672/wsl-loopback-stall/actions/workflows/docs.yml)
[![License](https://img.shields.io/github/license/3900563672/wsl-loopback-stall)](https://github.com/3900563672/wsl-loopback-stall/blob/main/LICENSE)

</div>

## TL;DR

| 项 | 结论 |
| --- | --- |
| 现象 | WSL2 内 `127.0.0.1` 新监听端口创建后立即连接，间歇性 `connection refused` / `i/o timeout`；高 churn 下出现 >30s STALL |
| 复现 | 2.7.8.0 与 2.9.4.0 稳定复现（5/5）；固定端口免疫；Docker Desktop 排除 |
| 根因方向 | Consomme 网络栈端口注册链在 churn 下失效（全局排他锁 + TimeWait 状态残留，源码层指向一致） |
| 修复确认 | 2.9.5+ 已包含相关修复（autobind/retention 路径，上游 commit 已并入发布线） |
| 官方互动 | 上游 issue #41286 两条评论；正式报告 #41383 已发布，机器人诊断通过，作者反馈标签已解除 |

## 现象与影响

- **触发模式**：IPv4 回环（`127.0.0.1`）+ 新监听端口 + 创建后立即连接。Go 与 Python 一致（语言无关）。
- **健康对照**：`eth0`（192.168.x.x）与 IPv6 `::1` 新端口立即连接 10/10 成功；长存活监听稳定可达。
- **实际影响**：开发环境中 Grafana 反向代理测试偶发失败（httptest server 刚启动即被 proxy 拨号）；CI 全绿——问题在环境层，不在业务代码。
- **严重形态**：极端 churn（`wsl --shutdown` 恢复前的退化态）下连接停滞 >30s，`WSAEADDRINUSE` 窗口 60–75s 与 TCP TIME_WAIT 特征吻合。

## 证据链（怎么证明的）

1. **确定性复现**：探针驱动、分钟级触发健康态瞬态；churn 模式 30s/轮稳定触发 STALL（`tools/wsl-loopback-probe/`）。
2. **剂量响应**：约 10.4ms/bind 固定开销、延迟 ≈ 并发 × 10.4ms、128 并发 99.27% 超过 1s、吞吐恒定约 96 bind/s——把"偶发"升级为"机制"。
3. **固定端口免疫**：同一端口注册成功后重新 listen 再立即连接成功，churn 专属。
4. **Docker 排除**：不起 Docker Desktop 同样复现，排除第三方组件。
5. **DLL 指纹**：本机 `wsldevicehost.dll` 与开源 net_consomme 字符串/导出签名比对全中（tcp 27/27、udp 7/7、dns_tcp 2/2），确认运行时与开源代码同源。
6. **源码机制**：`ConsommeNetworking.cpp` 全局排他锁可能阻塞新注册；`tcp.rs` TimeWait 不启动 timer 导致状态残留——与所有观察一致。
7. **版本区间**：2.9.4 仍复现（87.5% STALL 率），2.9.5+ 发布线已确认包含修复 commit，定位缺陷引入/修复区间。

## 官方互动时间线

- 2026-08-18：上游 issue #41286 评论（健康态瞬态 + 5/5 复现）。
- 2026-08-19：正式报告 #41383 发布（正文含直方图、Docker 排除、版本区间）；官方日志包已按模板补交（`wsl-netlogs-issue41383.zip`）；机器人诊断通过。

## 研究历程（过程时间线）

| 阶段 | 时间 | 关键产出 | 文档 |
| --- | --- | --- | --- |
| 发现 | 2026-08-16 ~ 08-18 | 本地测试偶发失败 → 收敛为"IPv4 回环 + 新端口 + 立即连接"专属模式 | 01 / 02 |
| 复现 | 2026-08-18 | 探针驱动确定性复现（5/5）；四地址对照；语言无关 | 03 |
| 根因 | 2026-08-18 | kill 因果实验推翻 Relay 假设；定位"新端口注册链路失效" | 01 / 12 |
| 源码证据 | 2026-08-18 ~ 19 | 双仓库源码机制分析 + DLL 指纹锚定 openvmm commit 0bb5cf75 | 12 / 13 / 14 / 15 |
| 参数定量 | 2026-08-19 | 剂量响应（10.4ms/bind）、TIME_WAIT 窗口、128 并发 99.27% >1s | 04 / 05 |
| 环境排除 | 2026-08-19 | Docker ON/OFF 对照、整机重启复测 | 06 |
| 版本定位 | 2026-08-19 | 2.9.4 仍复现；2.9.5+ 确认包含修复 commit | 10 / 17 |
| 上游互动 | 2026-08-18 ~ 19 | 上游评论、正式报告、官方日志包 | 23 / 24 |
| 开发环境再实证 | 2026-08-20 | 端口被遮蔽后换新端口立即恢复（第 N 次）；半死进程假象与操作教训 | 25 |

## 仓库结构

```text
docs/      主文档链，编号全局唯一（01–24），按主题分段，无交叉
archive/   过程归档：迁移 commit 索引
tools/     探针（Go）、直方图分析
evidence/  关键小证据（日志包、渲染截图）+ 大文件清单
```

### docs 编号地图

| 分段 | 编号 | 内容 |
| --- | --- | --- |
| 研究结论 | 01–05 | 研究报告、实验记录、复现手册、参数验证、直方图 |
| 环境与实验 | 06–11 | 重启后排除、churn 分析、系统恢复、回滚指南、升级验证、缓存预热 |
| 源码与证据 | 12–19 | 源码机制/深入、DLL 签名核验/指纹比对、openvmm 溯源、修复确认、日志包、上游查重 |
| port0 证据链 | 20–22 | port0 跟踪失败、注册窗口、ETW 实证 |
| 对外交付物 | 23–24 | 正式报告正文（#41383）、日志包评论 |
| 开发环境影响 | 25 | 端口残留再实证与操作教训 |

> 投稿过程内部材料（评论草稿、预案、发送记录等）为本地内部资料，不入库。

## 快速开始

环境：Windows 11 + WSL2（Ubuntu，Consomme 网络模式）。

```bash
# 1. 探针：复现"新端口首连被拒 / churn STALL"（Go 1.21+）
cd tools/wsl-loopback-probe
go run .

# 2. 复现手册（含每项实验的预期与耗时）
#    docs/03_复现手册.md
```

> 环境恢复与回滚步骤见 `docs/08_系统恢复操作步骤.md`、`docs/09_回滚与恢复指南.md`；大体积原始证据（ETL/抓包）清单见 `evidence/manifest.md`。

## 说明与限制

- 本仓库为**研究记录与证据归档**：现象、实验、源码分析、官方互动全链路，可独立复现。
- 大体积原始证据（ETL 抓包、WPR 日志）不入 git，清单见 `evidence/manifest.md`。
- 迁移自早期研究工作区的完整 commit 历史见 `archive/prs/commit-index.md`。
- 文档编号全局唯一（`docs/` 01–32），主题分段见上文；`archive/` 为过程归档不参与主编号。
## 🤖 AI 协作说明

本研究全程在 AI 辅助下推进——复现设计、源码分析与证据整理均有 AI 参与。所有结论均经过**人工复核与可复现实验验证**（本仓库即完整证据链）：AI 是协作者，人对结论负责。

AI×Human 协作研究与实践见 [我的主页](https://github.com/3900563672)。

