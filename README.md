# Polymarket Tail Risk Web App

一个用于监控和管理 Polymarket 市场尾部风险的 Web 应用程序。系统通过数据采集、质量检查、标签分类、评分和审核流程来识别和管理高风险市场。

![1775309980461](image/README/1775309980461.png)

## 项目简介

Polymarket Tail Risk 是一个全栈 Web 应用，旨在帮助团队识别、评估和管理 Polymarket 平台上的高风险市场。系统包含以下核心功能：

- **数据采集**：自动从 Polymarket API 采集市场数据和快照
- **数据质量检查**：验证数据完整性和一致性
- **标签分类**：使用规则引擎和 AI 模型对市场进行分类
- **风险评分**：基于多维度指标计算市场风险分数
- **审核流程**：人工审核高风险市场，支持批准/拒绝操作
- **名单管理**：维护白名单、灰名单和黑名单
- **监控告警**：实时监控系统健康状态和任务执行情况
- **质量回归**：定期检测标签质量异常
- **报告生成**：自动生成周度和里程碑报告

### 技术栈

- **后端**：Python 3.14, FastAPI, SQLAlchemy, Alembic
- **前端**：Next.js 15, React 19, TypeScript, Tailwind CSS
- **Worker**：Celery, Redis/SQLite
- **数据库**：SQLite (开发), PostgreSQL (生产)

## 目录结构

```
prtrad/
├── apps/
│   ├── api/              # FastAPI 后端服务
│   │   ├── app/          # API 路由和主应用
│   │   ├── db/           # 数据库模型和迁移
│   │   ├── services/     # 业务逻辑服务
│   │   └── middleware/   # 中间件
│   └── web/              # Next.js 前端应用
│       └── app/          # 页面和组件
├── workers/              # Celery Worker
│   └── worker/
│       └── tasks/        # 后台任务
├── tests/                # 测试
│   ├── integration/      # 集成测试
│   └── *.py              # 单元测试
├── docs/                 # 文档
├── scripts/              # 启动和辅助脚本
└── infra/                # 基础设施配置
```

## 快速启动

### 一键启动（推荐）

**Windows 用户**：

```bash
start.bat
```

**Linux/Mac 用户**：

```bash
./start.sh
```

启动脚本会自动：

- 检查 Node.js 和 Python 环境
- 安装依赖（如果未安装）
- 创建 Python 虚拟环境（如果不存在）
- 运行数据库迁移（如果数据库不存在）
- 启动所有服务

### 手动启动

如果需要手动控制启动流程：

```bash
# 1. 安装依赖
npm install

# 2. 初始化环境（首次运行）
# Windows
powershell -ExecutionPolicy Bypass -File ./scripts/bootstrap.ps1
# Linux/Mac
bash ./scripts/bootstrap.sh

# 3. 运行数据库迁移
npm run db:upgrade

# 4. 启动所有服务
npm run dev
```

启动后可访问：

- Web 前端：http://localhost:3000
- API 后端：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 安装说明

### 前置要求

- Node.js 18+ 和 npm
- Python 3.14+
- Git

### 详细安装步骤

1. **克隆仓库**

```bash
git clone <repository-url>
cd prtrad
```

2. **使用一键启动脚本**

```bash
# Windows
start.bat

# Linux/Mac
./start.sh
```

或者按照上面的"手动启动"步骤操作。

## 使用方法

### 开发环境

#### 启动所有服务

```bash
npm run dev
```

#### 单独启动服务

```bash
# 仅启动 API
npm run dev:api

# 仅启动 Web
npm run dev:web

# 仅启动 Worker
npm run dev:worker

# 仅启动 Beat
npm run dev:beat
```

### 数据库管理

```bash
# 升级到最新版本
npm run db:upgrade

# 降级一个版本
npm run db:downgrade

# 查看当前版本
npm run db:current

# 创建新迁移
cd apps/api
alembic revision --autogenerate -m "description"
```

### 手动触发任务

```bash
# 同步市场数据
npm run task:market-sync

# 同步快照数据
npm run task:snapshot-sync

# 运行数据质量检查
npm run task:dq-run

# 运行标签分类
npm run task:tagging-run
```

### 运行测试

```bash
# M4 风控自动化测试
npm run test:risk

# 功能验证测试
bash test_m1_m2.sh

# Worker 任务测试
cd workers && python test_new_tasks.py

# 单元测试
python -m pytest tests/test_*.py -v

# 集成测试
python -m pytest tests/integration/ -v

# 所有测试
python -m pytest -v
```

### 访问应用

- **Web 控制台**：http://localhost:3000
- **API 文档**：http://localhost:8000/docs
- **API Redoc**：http://localhost:8000/redoc

### 主要功能页面

- `/` - 首页和系统概览
- `/markets` - 市场列表
- `/dq` - 数据质量检查
- `/tagging` - 标签分类
- `/review` - 审核队列
- `/lists` - 名单管理
- `/monitoring` - 系统监控
- `/tag-quality` - 标签质量
- `/reports` - 报告中心

## 贡献指南

我们欢迎所有形式的贡献！请遵循以下指南：

### 开发流程

1. **Fork 仓库**并克隆到本地
2. **创建功能分支**：`git checkout -b feature/your-feature-name`
3. **进行开发**并确保代码质量
4. **运行测试**确保所有测试通过
5. **提交更改**使用语义化提交信息
6. **推送分支**：`git push origin feature/your-feature-name`
7. **创建 Pull Request**

### 代码规范

#### Git 提交信息

使用语义化提交信息格式：

```
<type>: <description>

[optional body]

[optional footer]
```

类型（type）：

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `test`: 测试相关
- `refactor`: 代码重构
- `style`: 代码格式调整
- `chore`: 构建/工具链更新

示例：

```
feat: 添加拒绝原因码管理 API
fix: 修复数据库索引重复问题
test: 添加名单管理集成测试
docs: 更新 README 安装说明
```

#### Python 代码规范

- 遵循 PEP 8 风格指南
- 使用类型注解
- 编写文档字符串
- 保持函数简洁（单一职责）

#### TypeScript/React 代码规范

- 使用 TypeScript 严格模式
- 优先使用函数组件和 Hooks
- 遵循 React 最佳实践
- 使用 Tailwind CSS 进行样式设计

### 测试要求

- 所有新功能必须包含测试
- 单元测试覆盖核心业务逻辑
- 集成测试覆盖 API 端点
- 确保所有测试通过后再提交

### 文档要求

- 更新相关文档（如果适用）
- 在 Pull Request 中说明更改内容
- 复杂功能需要添加使用示例

### 代码审查

- 所有 Pull Request 需要经过代码审查
- 响应审查意见并进行必要的修改
- 保持代码简洁、可读、可维护

### 报告问题

如果发现 Bug 或有功能建议：

1. 检查是否已有相关 Issue
2. 创建新 Issue 并提供详细信息：
   - Bug：复现步骤、预期行为、实际行为、环境信息
   - 功能：使用场景、预期效果、可能的实现方案

### 开发资源

- **开发指南**：[CLAUDE.md](CLAUDE.md)
- **项目状态**：[PROJECT_COMPLETION_STATUS.md](PROJECT_COMPLETION_STATUS.md)
- **测试报告**：[TESTING_100_PERCENT_COMPLETE.md](TESTING_100_PERCENT_COMPLETE.md)
- **快速开始**：[QUICK_START.md](QUICK_START.md)

## 环境变量

开发环境使用默认配置，生产环境需要配置以下环境变量：

```env
# 应用环境
APP_ENV=production

# 数据库
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# API 密钥
POLYMARKET_API_KEY=your_api_key_here

# 日志
LOG_LEVEL=INFO
```

详细配置说明请参考 `docs/` 目录下的文档。

## 部署

### 生产部署步骤

1. 安装依赖
2. 配置环境变量
3. 运行数据库迁移
4. 构建前端：`cd apps/web && npm run build`
5. 启动服务（使用 PM2 或 systemd）

详细部署指南请参考 `infra/` 目录。

## 许可证

[待添加许可证信息]

## 联系方式

- **问题追踪**：GitHub Issues
- **文档**：项目根目录的 Markdown 文件
- **测试**：运行 `bash test_m1_m2.sh` 验证系统状态

---

**当前状态**：✅ M1-M2 阶段完成，所有测试通过
**最后更新**：2026-04-04
