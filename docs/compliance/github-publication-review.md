# GitHub 发布合规审查

审查日期：2026-05-23（最后更新：2026-05-23 第二轮补齐）

本文是面向公开 GitHub 仓库发布前的工程合规清单，不构成法律意见。若后续要商业化分发、接入真实资金或发布二进制产物，应再做正式法律审查。

## 结论

- 当前跟踪文件未发现真实 API Key、钱包私钥、云密钥或 `.env` 泄露。
- `.env` 未被 Git 跟踪，历史中也未发现 `.env` 提交记录。
- `.claude/` 属于本地助手配置，已加入 `.gitignore`，已确认从 Git 跟踪中移除。历史提交中的 `.claude/settings*.json` 内容经核查仅含 Claude Code 允许命令列表，无密钥或私人路径，风险可接受。
- `SESSION_STATUS.json` 已从 Git 跟踪中移除，并加入 `.gitignore`。
- **已选择 MIT 开源许可证**，根目录 `LICENSE` 文件、`package.json` 与 `apps/web/package.json` 的 `license` 字段均同步为 `MIT`，版权归属署名 `anzx01`。
- 依赖中存在 LGPL 与 CC-BY-4.0 条目，已在第三方依赖授权清单中记录。
- `image/` 目录三张截图人工审查通过：仅含 UI、系统生成 UUID、内部时间戳，无钱包地址、无真实人名、无本机路径、无外部素材复用。
- **已补齐**：`DISCLAIMER.md`（实盘资金风险免责）、`CONTRIBUTING.md`（贡献流程 + DCO 签名要求）、`docs/compliance/data-usage-policy.md`（Polymarket API 数据使用边界）、`scripts/refresh-licenses.sh`（依赖授权清单刷新脚本）。

## 已执行检查

- Git 跟踪文件清单检查：确认 `.env`、`.venv/`、`node_modules/`、`var/`、`logs/` 未作为业务文件进入跟踪范围。
- Git 历史检查：`git log --all -- .env .env.local apps/web/.env apps/web/.env.local` 未返回提交记录。
- 密钥扫描：`detect-secrets` 对 Git 跟踪文件仅报告 Alembic `down_revision` 版本号误报。
- 依赖授权检查：从 `package-lock.json` 与 Python 包 metadata 汇总依赖许可证。
- 素材检查：人工查看 `image/` 下 PNG，内容为本项目 UI 截图。
- 编码检查：跟踪文本文件可按 UTF-8 读取；发现的 UTF-8 BOM 已列入自动清理项。

## 需要发布前确认

- 开源许可证已选定：MIT。`LICENSE` 文件 Copyright 行填写的是 `anzx01`；若版权应归属其他个人或机构，需在公开前修改。
- 远端历史已复核：`.claude/settings*.json` 历史内容经核查仅含 Claude Code 命令权限列表，无密钥或私人路径，风险可接受。未发现 `.env` 历史提交。若追求最干净的历史，可考虑压缩为新的初始提交。
- `py_clob_client_v2==1.0.0` 已在 `third-party-notices.md` 中补充说明：Polymarket 官方 SDK 采用 MIT 许可证，本项目测试中仅 mock 该包，不含其源代码，已记录为运行时依赖。
- 如果发布 Docker 镜像、桌面包、二进制包或托管服务，应补齐完整第三方许可证文本、归属声明和运行时依赖清单。
- 依赖授权清单建议定期刷新：运行 `bash scripts/refresh-licenses.sh`，输出落到 `var/license-reports/`，人工据此更新 `third-party-notices.md`。

## 参考

- GitHub 官方文档说明：没有许可证时，默认版权法仍适用，公开仓库不自动授予他人使用权。参考：https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository

