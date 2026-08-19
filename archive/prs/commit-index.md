# Commit 索引（迁移后）
> 源仓库 hello-k8s-ai 中 WSL 相关 commit 经 `git filter-repo` 按路径提取，作者/日期/消息完整保留，
> 哈希已重写。共 22 个 commit，按时间顺序（旧→新）：

01d2b92 docs: 文档体系内容迁移——根清理、journal/lessons 拆分与三层入口合并
fc8a8d4 docs: 沉淀 WSL 回环首连被拒排查结论（localhost 转发中继降级）
bd075c8 docs: 补充 journal front-matter 日期字段（通过 docs-check）
c829502 docs: WSL 回环中继降级完整排查案例 + 探针接入指引
0c00215 feat: WSL 回环中继探针接入 preflight 与 selfcheck（环境问题可复现化）
3e8c13d docs: 补充 WSL 回环探针参数说明与自动接入指引
59f4efd fix: WSL 回环探针 lint 修复（errcheck/SplitSeq）+ 接入说明同步
d601fdf fix: WSL 回环探针重写为单轮语义（健康对照推翻旧探针）
38b9dd4 docs: 沉淀 WSL 研究修正（fd11/健康对照/瞬态）+ Docker bind 失效恢复案例
c5e7733 fix: 探针 curl 命令行拆分（修复 CI lint lll 超长行）
570e28b docs: WSL 回环案例研究沉淀（阶段五至十） (#59)
0c1c93c docs: WSL 回环研究三 issue 闭环（查重/指纹/参数实验） (#67)
d5839fe docs: WSL 回环 follow-up 评论正文修订（#41286）
c710e2c docs: WSL 31/32 号沉淀（溯源勘误 + 重启后排除测试 + 探针工具缺陷修复） (#70)
fed7a65 research: WSL 缓存预热对照实验——瓶颈定位到 seccomp 通知链（Fixes #72） (#78)
25e7b36 docs: 沉淀 WSL 升级验证实验（2.9.4 仍复现 + 回滚 MSI 修正，#71/#63） (#79)
b596a97 feat: Agent 进化强制层——静态检查三件套 + make doctor 环境自检 (#84)
9ee607b docs: WSL 源码级验证——2.9.5+ 修复已确认存在（#71 最后证明项） (#85)
3269686 docs: WSL 回环案例独立仓库——文档归一重编号（01-39）+ 归档迁移 + README 名片
1acb58c chore: 仓库优化——指向修复 + lint/链接门禁 + LICENSE + README badge
288ebfb chore: 移除投稿内部材料并重编号 docs 01-24
e5f7f2a chore: 清洗公开内容——本地路径/IP/MAC 泛化、内部过程措辞中性化、移除观察脚本与子集日志包

> 迁移说明：源仓库 PR 为 GitHub 平台对象，无法迁移；本索引即迁移后的完整 commit 历史（哈希已重写）。
