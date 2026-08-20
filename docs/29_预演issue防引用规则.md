# 29 预演 issue 防引用规则（2026-08-20）

> 规则等级：硬规则（已入自有仓库 FAILURE_REGISTRY FR-014）

## 问题

自有仓库的预演/rehearsal issue 标题或正文出现外部仓库编号（如 `#41383`）时，GitHub 自动在外部 issue 时间线生成 cross-reference（"mentioned this"），预演内容对外可见。2026-08-20 预演 issue #104（标题含 "WSL #41383"）再次触发，已删除。

## 规则

1. 预演 issue 标题**不得**包含任何外部仓库编号。用模糊标题，例如 `[Internal rehearsal] Render check (will be closed)`。
2. 预演正文中的外部编号（`#41383`、`#41051` 等）**必须用反引号包裹**（`` `#41383` ``，代码格式不触发自动引用），或直接省略编号。
3. 预演 issue 用后即删：`gh issue delete <n> --repo <owner/repo> --yes`。删除后外部时间线的 cross-reference 自动消失（已验证 2026-08-20 #104）。
4. 正式发送的内容（评论/issue）正常使用编号与 @mention——规则只约束预演产物。

## 验证记录

- 2026-08-20 04:5x 删除 #104 后，`microsoft/WSL#41383` timeline 仅剩 3 个正常 @mention 事件，无 cross-referenced 事件。