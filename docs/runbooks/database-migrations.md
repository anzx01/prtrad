# 数据库迁移手册

## 命令

- `npm run db:upgrade`
- `npm run db:downgrade`
- `npm run db:current`

## Wave 1 说明

- 本地验证使用 `sqlite:///./var/data/ptr_dev.sqlite3`
- 生产目标数据库方言仍然是 PostgreSQL

## 操作规则

- 每次 schema 变更都必须同时提供 upgrade 和 downgrade
- migration 文件必须可重复、可审查
- 应用代码与 migration 版本必须同步发布

