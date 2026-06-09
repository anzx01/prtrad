# 贡献指南 (Contributing)

感谢你对本项目的关注！本项目接受外部 Pull Request，但所有贡献必须满足以下条款。

## 1. 许可证

- 本项目采用 **MIT 协议**（见 [LICENSE](LICENSE)）。
- **提交 PR 即视为你同意**：你的贡献将以同样的 MIT 协议被纳入本项目，且授予项目作者及全体使用者按 MIT 协议使用、修改、再分发的权利。
- 你不会因此放弃自己作为贡献者的著作权署名。

## 2. Developer Certificate of Origin (DCO)

所有提交（commit）必须签名。我们使用 **Developer Certificate of Origin 1.1**（见 https://developercertificate.org/）——签名意味着你声明你有权提交该贡献。

### 如何签名

使用 `git commit -s`（或 `--signoff`）：

```bash
git commit -s -m "feat: add new tagging rule"
```

这会自动在 commit message 末尾追加一行：

```
Signed-off-by: Your Name <your.email@example.com>
```

`Your Name` 和邮箱需与 `git config user.name` / `git config user.email` 一致。

### DCO 1.1 全文（节选）

> By making a contribution to this project, I certify that:
>
> (a) The contribution was created in whole or in part by me and I have the right to submit it under the open source license indicated in the file; or
>
> (b) The contribution is based upon previous work that ... is covered under an appropriate open source license and I have the right ... to submit that work with modifications ...; or
>
> (c) The contribution was provided directly to me by some other person who certified (a), (b) or (c) and I have not modified it.
>
> (d) I understand and agree that this project and the contribution are public and that a record of the contribution (including all personal information I submit with it, including my sign-off) is maintained indefinitely and may be redistributed consistent with this project or the open source license(s) involved.

未签名的 commit 不会被合并。

## 3. 贡献流程

1. 在 Issues 中先讨论你的想法，避免重复劳动或方向偏离
2. Fork 本仓库，从 `main` 拉新分支：`git checkout -b feat/your-feature`
3. 按本项目的代码规范开发（见 `CLAUDE.md` 与 `AGENTS.md`）
4. **每个 commit 都用 `git commit -s` 签名**
5. 确保 `python -m pytest -v` 与前端 `npm --workspace apps/web run typecheck` 通过
6. 提交 PR，描述清楚动机、改动范围与测试方式

## 4. 代码规范

- **语言**：文档、注释、commit message 默认使用中文（仓库根 `CLAUDE.md` 约定）
- **文件长度**：Python/TypeScript ≤ 300 行/文件；Java/Go/Rust ≤ 400 行/文件
- **目录扇出**：每个目录文件数 ≤ 8
- **强类型**：避免使用未结构化的 `dict` / `any` / `json`
- **commit 规范**：`feat:` / `fix:` / `docs:` / `test:` / `refactor:` / `style:` / `chore:`

## 5. 安全问题

**不要**通过 Issues 公开报告安全漏洞，请按 [SECURITY.md](SECURITY.md) 流程私下提交。

## 6. 行为准则

请尊重所有贡献者。我们不接受人身攻击、骚扰、歧视或任何使讨论变得敌对的言行。维护者保留关闭/删除不当 Issues、评论与 PR 的权利。

## 7. 免责声明

本项目按 [DISCLAIMER.md](DISCLAIMER.md) 提供。贡献者的代码同样按"原样"提供，不对使用者承担任何责任。
