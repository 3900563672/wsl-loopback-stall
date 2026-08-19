# WSL2 Loopback Stall Case Study

WSL2（Consomme 网络模式）下 **IPv4 回环 + 临时端口 churn 引发的连接停滞（stall）**：完整复现、根因定位、证据链与上游互动记录。

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

- 2026-08-18：上游 issue #41286 试探评论（健康态瞬态 + 5/5 复现）。
- 2026-08-19：正式报告 #41383 发布（v5 正文，含直方图、Docker 排除、版本区间）；官方日志包已按模板补交（`wsl-netlogs-issue41383.zip`）；机器人诊断通过。
- 观察窗口：至 2026-09-01，见 `docs/35_时间线与观察窗口.md`。

## 仓库结构

```text
docs/      主文档链，编号全局唯一（01–39），按主题分段，无交叉
archive/   过程归档：源仓库 issue 全文、PR/commit 索引、正文草稿演进、早期文档形态
tools/     探针（Go）、观察脚本、直方图分析
evidence/  关键小证据（日志包、渲染截图）+ 大文件清单
Documents/ 面试专用材料（本地维护，gitignore，永不推送）
```

### docs 编号地图

| 分段 | 编号 | 内容 |
| --- | --- | --- |
| 总览与研究 | 01–05 | 行动指南、研究报告、现状与缺口、查重决策 |
| 实验与复现 | 06–15 | 实验记录、复现手册、参数验证、直方图、恢复/回滚、升级验证 |
| 源码与证据 | 16–26 | 机制分析、DLL 指纹/核验、openvmm 溯源、修复确认、日志包、port0 证据 |
| 投稿与互动 | 27–36 | 评论草稿与发送、issue 正文 v5、发布校验、时间线、弹药清单 |
| 预案 | 37–39 | 官方三种回应的处置预案 |

## 复现指引

环境：Windows 11 + WSL2（Ubuntu，Consomme 网络模式）。完整步骤见 `docs/07_复现手册.md`，恢复与回滚见 `docs/13_回滚与恢复指南.md`。

```bash
# 探针（Go）
cd tools/wsl-loopback-probe && go run . 
# 观察脚本
./tools/watch-41286.sh
```

## 说明与限制

- 本仓库为**研究记录与证据归档**，不包含业务代码。
- 大体积原始证据（ETL 抓包、WPR 日志）不入 git，清单见 `evidence/manifest.md`。
- 迁移自源仓库的完整 commit 历史见 `archive/prs/commit-index.md`。
