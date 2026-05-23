# GitHub 发布合规审查

审查日期：2026-05-23（最后更新：2026-05-23）

本文是面向公开 GitHub 仓库发布前的工程合规清单，不构成法律意见。若后续要商业化分发、接入真实资金或发布二进制产物，应再做正式法律审查。

## 结论

- 当前跟踪文件未发现真实 API Key、钱包私钥、云密钥或 `.env` 泄露。
- `.env` 未被 Git 跟踪，历史中也未发现 `.env` 提交记录。
- `.claude/` 属于本地助手配置，已加入 `.gitignore`，已确认从 Git 跟踪中移除。历史提交中的 `.claude/settings*.json` 内容经核查仅含 Claude Code 允许命令列表，无密钥或私人路径，风险可接受。
- `SESSION_STATUS.json` 已从 Git 跟踪中移除，并加入 `.gitignore`。
- 项目尚未选择开源许可证，当前按 `UNLICENSED` 处理：源码可见不等于授予使用权。
- 依赖中存在 LGPL 与 CC-BY-4.0 条目，已在第三方依赖授权清单中记录。
- `image/` 目录当前为本项目界面截图，未发现外部素材复用；仍建议保留素材来源说明。

## 已执行检查

- Git 跟踪文件清单检查：确认 `.env`、`.venv/`、`node_modules/`、`var/`、`logs/` 未作为业务文件进入跟踪范围。
- Git 历史检查：`git log --all -- .env .env.local apps/web/.env apps/web/.env.local` 未返回提交记录。
- 密钥扫描：`detect-secrets` 对 Git 跟踪文件仅报告 Alembic `down_revision` 版本号误报。
- 依赖授权检查：从 `package-lock.json` 与 Python 包 metadata 汇总依赖许可证。
- 素材检查：人工查看 `image/` 下 PNG，内容为本项目 UI 截图。
- 编码检查：跟踪文本文件可按 UTF-8 读取；发现的 UTF-8 BOM 已列入自动清理项。

## 需要发布前确认

- 是否要真正开源：若要允许他人使用或贡献，应由项目所有者选择并添加明确许可证；若不授权他人使用，保持 `UNLICENSED`。
- 远端历史已复核：`.claude/settings*.json` 历史内容经核查仅含 Claude Code 命令权限列表，无密钥或私人路径，风险可接受。未发现 `.env` 历史提交。若追求最干净的历史，可考虑压缩为新的初始提交。
- `py_clob_client_v2==1.0.0` 已在 `third-party-notices.md` 中补充说明：Polymarket 官方 SDK 采用 MIT 许可证，本项目测试中仅 mock 该包，不含其源代码，已记录为运行时依赖。
- 如果发布 Docker 镜像、桌面包、二进制包或托管服务，应补齐完整第三方许可证文本、归属声明和运行时依赖清单。

## 参考

- GitHub 官方文档说明：没有许可证时，默认版权法仍适用，公开仓库不自动授予他人使用权。参考：https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository

