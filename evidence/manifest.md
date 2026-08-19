# evidence —— 证据文件清单

> 大体积原始证据（ETL 抓包、WPR 日志、完整日志包）**不入 git**，保留在本地
> `C:\Users\hh\OneDrive\Desktop\WSL\`（logs/ 与 research/），本清单为唯一索引。

## 入库文件（本目录）

| 文件 | 大小 | 说明 |
| --- | --- | --- |
| `wsl-netlogs-issue41383.zip` | 5.8 MB | 官方 issue 日志包（含 logs.etl 54MB 压缩），2026-08-19 采集，36 秒窗口内 3 轮探针第 3 轮复现 >30s STALL |
| `wsl-netlogs-subset.zip` | 4.1 MB | 子集日志包（评论附件的早期版本） |
| `issue-page.png` | 84 KB | issue 渲染检查截图 |

## 本地保留的大文件（不入库）

| 路径 | 大小 | 说明 |
| --- | --- | --- |
| `Desktop\WSL\logs\WslLogs-2026-08-18_22-18-40-pktmon.etl` | ~GB 级 | pktmon 抓包（参数验证实验） |
| `Desktop\WSL\logs\WslLogs-2026-08-18_22-27-23.tar.gz` | 102 MB | 官方模板日志包（早版本） |
| `Desktop\WSL\logs\evidence/` | - | ETW / 探针证据 |
| `Desktop\WSL\research/*.etl` | 903 MB 总量 | 直方图与探针抓包（2026-08-19） |
| `Desktop\WSL\logs\2026-08-19-param-experiments/` | - | 参数实验日志 |
| `Desktop\WSL\logs\cache-warm-072.txt` | - | 缓存预热实验数据 |
| `Desktop\WSL\logs\reboot-exclusion/` | - | 重启后排除测试记录 |
| `Desktop\WSL\logs\wsl-upgrade-2026-08-19/` | - | 2.9.4 升级验证日志 |

> 复现要求这些文件时，按 `docs/07_复现手册.md` 与 `docs/13_回滚与恢复指南.md` 操作。
