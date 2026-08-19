# Commit 索引（迁移后）

> 源仓库 hello-k8s-ai 中 WSL 相关 commit 经 `git filter-repo` 按路径提取，作者/日期/消息完整保留，
> 哈希已重写。共 18 个 commit，按时间顺序（旧→新）：

01d2b92 docs: 文档体系内容迁移——根清理、journal/lessons 拆分与三层入口合并
fc8a8d4 docs: 沉淀 WSL 回环首连被拒排查结论（localhost 转发中继降级）
bd075c8 docs: 补充 journal front-matter 日期字段（通过 docs-check）
10dd120 docs: WSL 回环中继降级完整排查案例 + 探针接入指引（面试案例沉淀）
7d31eb6 feat: WSL 回环中继探针接入 preflight 与 selfcheck（环境问题可复现化）
72266be docs: 补充 WSL 回环探针参数说明与自动接入指引
2eca95b fix: WSL 回环探针 lint 修复（errcheck/SplitSeq）+ 接入说明同步
19b6d94 fix: WSL 回环探针重写为单轮语义（健康对照推翻旧探针）
d4904af docs: 沉淀 WSL 研究修正（fd11/健康对照/瞬态）+ Docker bind 失效恢复案例
540f3e2 fix: 探针 curl 命令行拆分（修复 CI lint lll 超长行）
9853dfa docs: WSL 回环案例研究沉淀（阶段五至十） (#59)
cddacd3 docs: WSL 回环研究三 issue 闭环（查重/指纹/参数实验） (#67)
cbbc630 docs: WSL #41286 follow-up 评论 v4 正式发送（编辑 v3 不新增）
18cf9b1 docs: WSL 31/32 号沉淀（溯源勘误 + 重启后排除测试 + 探针工具缺陷修复） (#70)
6c38455 research: WSL 缓存预热对照实验——瓶颈定位到 seccomp 通知链（Fixes #72） (#78)
811cee2 docs: 沉淀 WSL 升级验证实验（2.9.4 仍复现 + 回滚 MSI 修正，#71/#63） (#79)
fb70603 feat: Agent 进化强制层——静态检查三件套 + make doctor 环境自检 (#84)
793e19a docs: WSL 源码级验证——2.9.5+ 修复已确认存在（#71 最后证明项） (#85)

> 对照：源 PR 合并信息见 `pr-index.md`；源 issue 全文见 `../issues/`。
