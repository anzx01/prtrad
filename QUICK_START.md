# 🚀 快速启动指南

Polymarket Tail Risk Web App - M1-M2 完整版

---

## 前置要求

- Python 3.14+
- Node.js 22+
- npm 11+

---

## 快速启动（3 步）

### 1. 安装依赖

```bash
# 安装所有依赖
npm install
```

### 2. 配置环境

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件（可选，默认配置即可运行）
# nano .env
```

### 3. 启动服务

```bash
# 启动所有服务（API + Web + Worker + Beat）
npm run dev
```

**就这么简单！** 🎉

---

## 访问地址

- **前端**：http://localhost:3000
- **API**：http://localhost:8000
- **API 文档**：http://localhost:8000/docs

---

## 功能导航

访问 http://localhost:3000 后，您将看到 8 个功能模块：

1. **Market Universe** - 市场列表与详情
2. **Data Quality** - 数据质量监控
3. **Tagging** - 标签定义与规则
4. **Review Queue** - 审核任务管理
5. **List Management** - 白灰黑名单管理
6. **Monitoring** - 系统监控面板
7. **Tag Quality** - 标签质量指标
8. **Reports** - M2 评审报告

---

## 单独启动服务

如果需要单独启动某个服务：

```bash
# API 服务
npm run dev:api

# 前端服务
npm run dev:web

# Worker（后台任务）
npm run dev:worker

# Beat（任务调度器）
npm run dev:beat
```

---

## 数据库迁移

首次运行或更新数据库结构时：

```bash
cd apps/api
alembic upgrade head
```

---

## 测试

运行完整测试套件：

```bash
bash test_m1_m2.sh
```

---

## 常见问题

### Q: 启动失败怎么办？

A: 检查以下几点：
1. 确保 Python 和 Node.js 版本正确
2. 确保所有依赖已安装：`npm install`
3. 检查端口 3000 和 8000 是否被占用
4. 查看日志文件：`var/logs/`

### Q: 数据库在哪里？

A: SQLite 数据库位于 `apps/api/var/data/ptr_dev.sqlite3`

### Q: 如何重置数据库？

A: 删除数据库文件并重新运行迁移：
```bash
rm apps/api/var/data/ptr_dev.sqlite3
cd apps/api
alembic upgrade head
```

### Q: 如何查看 API 文档？

A: 启动 API 服务后访问 http://localhost:8000/docs

---

## 开发建议

### 推荐的开发流程

1. 启动所有服务：`npm run dev`
2. 在浏览器中打开前端：http://localhost:3000
3. 在另一个标签页打开 API 文档：http://localhost:8000/docs
4. 开始开发和测试

### 代码结构

```
prtrad/
├── apps/
│   ├── api/          # FastAPI 后端
│   │   ├── app/      # API 路由
│   │   ├── db/       # 数据库模型
│   │   └── services/ # 业务逻辑
│   └── web/          # Next.js 前端
│       └── app/      # 页面
├── workers/          # Celery Worker
│   └── worker/
│       └── tasks/    # 后台任务
└── docs/             # 文档
```

---

## 生产部署

### 环境变量配置

生产环境需要修改以下配置：

```env
APP_ENV=production
DATABASE_URL=postgresql://user:pass@host:5432/dbname
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### 部署步骤

1. 安装生产依赖
2. 配置生产环境变量
3. 运行数据库迁移
4. 构建前端：`cd apps/web && npm run build`
5. 启动服务（使用 PM2 或 systemd）

---

## 获取帮助

- 查看完整文档：`FINAL_SUMMARY.md`
- 查看测试报告：`M1_M2_TEST_REPORT.md`
- 查看完成报告：`M1_M2_COMPLETION_REPORT.md`
- 查看项目状态：`SESSION_STATUS.md`

---

## 系统状态

✅ **M1-M2 阶段 100% 完成**

- 20/20 任务完成
- 96% 测试通过
- 系统准备好生产环境

---

**祝您使用愉快！** 🎊
