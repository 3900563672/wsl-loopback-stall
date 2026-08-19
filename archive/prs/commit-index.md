# Commit 索引（迁移后）

> 迁移自早期研究工作区，经  按路径提取，作者/日期/消息完整保留，哈希已重写。共 24 个 commit，按时间顺序（旧→新）：

a660d98 docs: 文档体系内容迁移——根清理与分层入口合并
8edcb37 docs: 沉淀 WSL 回环首连被拒排查结论（localhost 转发中继降级）
0c68d27 docs: 补充文档 front-matter 日期字段（通过 docs-check）
2781557 docs: WSL 回环中继降级完整排查案例 + 探针接入指引
e322501 feat: WSL 回环中继探针接入 preflight 与 selfcheck（环境问题可复现化）
40d3a53 docs: 补充 WSL 回环探针参数说明与自动接入指引
f50da96 fix: WSL 回环探针 lint 修复（errcheck/SplitSeq）+ 接入说明同步
7ece3b2 fix: WSL 回环探针重写为单轮语义（健康对照推翻旧探针）
b4d393d docs: 沉淀 WSL 研究修正（fd11/健康对照/瞬态）+ Docker bind 失效恢复案例
d400fe9 fix: 探针 curl 命令行拆分（修复 CI lint lll 超长行）
1a76fba docs: WSL 回环案例研究沉淀（阶段五至十）
dff0033 docs: WSL 回环研究三 issue 闭环（查重/指纹/参数实验）
fb4113e docs: WSL 研究沉淀（溯源勘误 + 重启后排除测试 + 探针工具缺陷修复）
38ddaa0 research: WSL 缓存预热对照实验——瓶颈定位到 seccomp 通知链
128438f docs: 沉淀 WSL 升级验证实验（2.9.4 仍复现 + 回滚 MSI 修正）
919d0dd chore: 静态检查三件套与 make doctor 环境自检接入
c5c9978 docs: WSL 源码级验证——2.9.5+ 修复已确认存在
1a7202b docs: WSL 回环案例独立仓库——文档归一重编号（01-39）+ 归档迁移 + README 名片
78f5b36 chore: 仓库优化——指向修复 + lint/链接门禁 + LICENSE + README badge
70d8aa5 chore: 移除投稿内部材料并重编号 docs 01-24
26db24e chore: 清理公开内容，隐藏本地路径，删除内部材料
104e550 docs: 重生成 commit 索引（对齐重写后历史）
77237d0 docs: 重生成 commit 索引（对齐重写后历史）
315aeb6 docs: 清理仓库，删除内部材料，重写环境操作文档

> 迁移说明：早期工作区的 PR 为平台对象，无法迁移；本索引即迁移后的完整 commit 历史（哈希已重写）。
