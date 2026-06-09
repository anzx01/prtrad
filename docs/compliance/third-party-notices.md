# 第三方依赖授权清单

审查日期：2026-05-23

本文件记录当前仓库依赖层面的授权风险点，便于公开 GitHub 前审查。它不是完整的许可证文本集合；若后续分发二进制、镜像或部署包，应随包附带对应依赖的完整 LICENSE / NOTICE 文件。

## 项目自身授权

- 当前项目未选择开源许可证。
- `package.json` 与 `apps/web/package.json` 已标记为 `UNLICENSED`。
- 若项目要开放复用、派生或商用授权，需要项目所有者另行选择并添加 `LICENSE` 文件。

## JavaScript 依赖概况

来自 `package-lock.json` 的许可证计数：

| 许可证 | 数量 |
| --- | ---: |
| MIT | 69 |
| Apache-2.0 | 15 |
| LGPL-3.0-or-later | 10 |
| Apache-2.0 AND LGPL-3.0-or-later | 3 |
| Apache-2.0 AND LGPL-3.0-or-later AND MIT | 1 |
| ISC | 7 |
| MPL-2.0 | 12 |
| BSD-3-Clause | 1 |
| 0BSD | 1 |
| CC-BY-4.0 | 1 |

需要重点留意的条目：

| 包 | 许可证 | 说明 |
| --- | --- | --- |
| `@img/sharp-libvips-*` | `LGPL-3.0-or-later` | `sharp` 的平台相关图像处理依赖；公开源码通常风险较低，分发包含该依赖的产物时需要确认 LGPL 义务。 |
| `@img/sharp-*` | `Apache-2.0 AND LGPL-3.0-or-later` 或组合许可证 | 平台相关包；分发时保留对应许可证文本。 |
| `caniuse-lite` | `CC-BY-4.0` | 浏览器兼容数据；使用或再分发时保留归属声明。 |

直接 JavaScript 依赖摘要：

| 包 | 当前解析版本 | 许可证 |
| --- | --- | --- |
| `concurrently` | `9.2.1` | MIT |
| `next` | `15.5.14` | MIT |
| `react` | `19.2.4` | MIT |
| `react-dom` | `19.2.4` | MIT |
| `@tailwindcss/postcss` | `4.2.2` | MIT |
| `tailwindcss` | `4.2.2` | MIT |
| `typescript` | `5.9.3` | Apache-2.0 |
| `@types/node` | `22.19.15` | MIT |
| `@types/react` | `19.2.14` | MIT |

## Python 依赖概况

来自本地 `.venv` metadata 与 `requirements.txt` 的直接依赖摘要：

| 包 | 版本 | 许可证 |
| --- | --- | --- |
| `fastapi` | `0.116.1` | MIT |
| `uvicorn` | `0.35.0` | BSD-3-Clause |
| `pydantic-settings` | `2.10.1` | MIT |
| `SQLAlchemy` | `2.0.41` | MIT |
| `alembic` | `1.16.4` | MIT |
| `psycopg` / `psycopg-binary` | `3.2.13` | LGPL-3.0-only |
| `httpx` | `0.28.1` | BSD-3-Clause |
| `celery` | `5.5.3` | BSD-3-Clause |

Polymarket SDK 说明：

- `py_clob_client_v2==1.0.0`：Polymarket 官方 CLOB 交易客户端 SDK 的本地构建版本。Polymarket 的官方开源仓库（`py-clob-client`）采用 MIT 许可证；若使用的是该仓库的派生版本，请以实际 README / LICENSE 文件为准。本项目测试中仅对该包进行了 mock，不包含其源代码，仅通过 `requirements.txt` 声明运行时依赖。

