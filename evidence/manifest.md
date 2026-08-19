# evidence —— 证据文件清单

> 大体积原始证据（ETL 抓包、WPR 日志、完整日志包）不入 git，保留在本地研究目录（logs/ 与 research/ 子目录），本清单为唯一索引。

## 入库文件（本目录）

| 文件 | 大小 | 说明 |
| --- | --- | --- |
| `wsl-netlogs-issue41383.zip` | 5.8 MB | 官方 issue 日志包（含 logs.etl 54MB 压缩），2026-08-19 采集，36 秒窗口内 3 轮探针第 3 轮复现 >30s STALL |
| `issue-page.jpg` | 84 KB | issue 渲染检查截图 |

## 本地保留的大文件（不入库）

| 相对路径（本地） | 大小 | 说明 |
| --- | --- | --- |
| `logs/WslLogs-2026-08-18_22-18-40-pktmon.etl` | ~GB 级 | pktmon 抓包（参数验证实验） |
| `logs/WslLogs-2026-08-18_22-27-23.tar.gz` | 102 MB | 官方模板日志包（早版本） |
| `logs/evidence/` | - | ETW / 探针证据 |
| `research/*.etl` | 903 MB 总量 | 直方图与探针抓包（2026-08-19） |
| `logs/2026-08-19-param-experiments/` | - | 参数实验日志 |
| `logs/cache-warm-072.txt` | - | 缓存预热实验数据 |
| `logs/reboot-exclusion/` | - | 重启后排除测试记录 |
| `logs/wsl-upgrade-2026-08-19/` | - | 2.9.4 升级验证日志 |

> 复现需要这些文件时，按 `docs/03_复现手册.md` 与 `docs/09_回滚与恢复指南.md` 操作。
