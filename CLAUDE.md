# Polymarket Tail Risk Web App - Claude 开发指南

**项目**：Polymarket Tail Risk Web App
**当前阶段**：M1-M2 完成
**最后更新**：2026-04-04

---

## 项目概述

这是一个用于监控和管理 Polymarket 市场尾部风险的 Web 应用程序。系统通过数据采集、质量检查、标签分类、评分和审核流程来识别和管理高风险市场。

### 技术栈

- **后端**：Python 3.14, FastAPI, SQLAlchemy, Alembic
- **前端**：Next.js 15, React 19, TypeScript, Tailwind CSS
- **Worker**：Celery, Redis/SQLite
- **数据库**：SQLite (开发), PostgreSQL (生产)

---

## 项目结构

```
prtrad/
├── apps/
│   ├── api/              # FastAPI 后端
│   │   ├── app/          # API 路由和主应用
│   │   ├── db/           # 数据库模型和迁移
│   │   ├── services/     # 业务逻辑服务
│   │   └── middleware/   # 中间件
│   └── web/              # Next.js 前端
│       └── app/          # 页面和组件
├── workers/              # Celery Worker
│   └── worker/
│       └── tasks/        # 后台任务
├── tests/                # 测试
│   ├── integration/      # 集成测试
│   └── *.py              # 单元测试
└── docs/                 # 文档
```

---

## 重要约定

### 1. 数据库相关

#### 索引定义

⚠️ **重要**：避免重复定义索引

```python
# ❌ 错误：重复定义索引
class MyModel(Base):
    __table_args__ = (
        Index("ix_my_field", "my_field"),  # 在这里定义
    )
    my_field: Mapped[str] = mapped_column(String(64), index=True)  # ❌ 不要再加 index=True

# ✅ 正确：只在一处定义索引
class MyModel(Base):
    __table_args__ = (
        Index("ix_my_field", "my_field"),  # 只在这里定义
    )
    my_field: Mapped[str] = mapped_column(String(64))  # ✅ 不加 index=True
```

#### 迁移

- 使用 Alembic 管理数据库迁移
- 迁移文件位于 `apps/api/db/migrations/versions/`
- 运行迁移：`cd apps/api && alembic upgrade head`

### 2. 测试相关

#### 单元测试

- 位置：`tests/test_*.py`
- 使用 `test_db` fixture 获取测试数据库
- 运行：`python -m pytest tests/test_*.py -v`

#### 集成测试

- 位置：`tests/integration/test_api_*.py`
- 使用文件数据库（`test.db`）而非内存数据库
- 审计服务已被 mock，避免数据库依赖
- 运行：`python -m pytest tests/integration/ -v`

#### 测试数据库配置

```python
# tests/integration/conftest.py 的关键配置
# 1. 使用文件数据库（重要！）
test_db_path = Path(__file__).parent / "test.db"
test_engine = create_engine(f"sqlite:///{test_db_path}", echo=False)

# 2. Mock 审计服务（重要！）
class MockAuditLogService:
    def write_event(self, event, session=None):
        return "mock-audit-id"
```

### 3. API 开发

#### 路由结构

- 所有路由位于 `apps/api/app/routes/`
- 使用 `Depends(get_db)` 获取数据库会话
- 返回 Pydantic 模型作为响应

#### 服务层

- 所有业务逻辑在 `apps/api/services/` 中
- 服务接受 `db: Session` 参数
- 使用审计服务记录重要操作（可选）

```python
# 示例服务
class MyService:
    def __init__(self, db: Session, audit_service: AuditLogService | None = None):
        self.db = db
        self.audit_service = audit_service
```

### 4. Worker 任务

#### 任务定义

- 位置：`workers/worker/tasks/`
- 使用 `@celery_app.task` 装饰器
- 任务名称格式：`module.function_name`

```python
@celery_app.task(name="my_module.my_task", bind=True)
def my_task(self: Task) -> dict:
    logger.info("Starting task")
    # 任务逻辑
    return {"status": "success"}
```

#### 任务注册

- 在 `workers/worker/celery_app.py` 的 `imports` 中注册
- 在 `beat_schedule` 中配置定时任务

### 5. 前端开发

#### 页面结构

- 所有页面位于 `apps/web/app/`
- 使用 Server Components（默认）
- 需要交互时使用 `'use client'`

#### API 调用

```typescript
// 从后端 API 获取数据
const response = await fetch('http://localhost:8000/api/endpoint');
const data = await response.json();
```

---

## 已知问题和注意事项

### 1. 数据库索引重复

✅ **已修复**：`ListVersion` 和 `MarketScoringResult` 模型的索引重复问题已解决

### 2. 集成测试数据库

✅ **已修复**：使用文件数据库和 mock 审计服务解决了连接问题

### 3. Worker 任务依赖

⚠️ **注意**：Worker 任务需要 Celery 环境，测试时使用独立脚本

---

## 开发工作流

### 启动开发环境

```bash
# 1. 安装依赖
npm install

# 2. 运行数据库迁移
cd apps/api
alembic upgrade head

# 3. 启动所有服务
npm run dev  # 启动 API + Web + Worker + Beat
```

### 添加新功能

1. **数据库**：

   - 在 `apps/api/db/models.py` 添加模型
   - 创建迁移：`alembic revision --autogenerate -m "description"`
   - 运行迁移：`alembic upgrade head`
2. **服务层**：

   - 在 `apps/api/services/` 创建服务
   - 实现业务逻辑
3. **API**：

   - 在 `apps/api/app/routes/` 创建路由
   - 在 `apps/api/app/main.py` 注册路由
4. **Worker**（可选）：

   - 在 `workers/worker/tasks/` 创建任务
   - 在 `celery_app.py` 注册任务
5. **前端**：

   - 在 `apps/web/app/` 创建页面
   - 更新导航
6. **测试**：

   - 创建单元测试：`tests/test_*.py`
   - 创建集成测试：`tests/integration/test_api_*.py`

### 运行测试

```bash
# 功能验证
bash test_m1_m2.sh

# Worker 任务
cd workers && python test_new_tasks.py

# 单元测试
python -m pytest tests/test_*.py -v

# 集成测试
python -m pytest tests/integration/ -v

# 所有测试
python -m pytest -v
```

---

## Git 提交规范

使用语义化提交信息：

```
feat: 添加新功能
fix: 修复 bug
docs: 更新文档
test: 添加测试
refactor: 重构代码
style: 代码格式调整
chore: 构建/工具链更新
```

示例：

```
feat: 添加拒绝原因码管理 API
fix: 修复数据库索引重复问题
test: 添加名单管理集成测试
```

---

## 部署

### 环境变量

生产环境需要配置：

```env
APP_ENV=production
DATABASE_URL=postgresql://user:pass@host:5432/dbname
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### 部署步骤

1. 安装依赖
2. 配置环境变量
3. 运行数据库迁移
4. 构建前端：`cd apps/web && npm run build`
5. 启动服务（使用 PM2 或 systemd）

---

## 文档

- **快速开始**：`QUICK_START.md`
- **项目状态**：`PROJECT_COMPLETION_STATUS.md`
- **测试报告**：`TESTING_100_PERCENT_COMPLETE.md`
- **会话状态**：`SESSION_STATUS.md`

---

## 联系和支持

- **问题追踪**：GitHub Issues
- **文档**：项目根目录的 Markdown 文件
- **测试**：运行 `bash test_m1_m2.sh` 验证系统状态

---

**最后更新**：2026-04-04
**维护者**：Claude Sonnet 4.6
**状态**：✅ M1-M2 阶段完成，所有测试通过


# 任何项目都务必遵守的规则（极其重要！！！）

## Communication

- 永远使用简体中文进行思考和对话

## Documentation

- 编写 .md 文档时，也要用中文
- 正式文档写到项目的 docs/ 目录下
- 用于讨论和评审的计划、方案等文档，写到项目的 discuss/ 目录下

## Code Architecture

- 编写代码的硬性指标，包括以下原则：
  （1）对于 Python、JavaScript、TypeScript 等动态语言，尽可能确保每个代码文件不要超过 300 行
  （2）对于 Java、Go、Rust 等静态语言，尽可能确保每个代码文件不要超过 400 行
  （3）每层文件夹中的文件，尽可能不超过 8 个。如有超过，需要规划为多层子文件夹
- 除了硬性指标以外，还需要时刻关注优雅的架构设计，避免出现以下可能侵蚀我们代码质量的「坏味道」：
  （1）僵化 (Rigidity): 系统难以变更，任何微小的改动都会引发一连串的连锁修改。
  （2）冗余 (Redundancy): 同样的代码逻辑在多处重复出现，导致维护困难且容易产生不一致。
  （3）循环依赖 (Circular Dependency): 两个或多个模块互相纠缠，形成无法解耦的“死结”，导致难以测试与复用。
  （4）脆弱性 (Fragility): 对代码一处的修改，导致了系统中其他看似无关部分功能的意外损坏。
  （5）晦涩性 (Obscurity): 代码意图不明，结构混乱，导致阅读者难以理解其功能和设计。
  （6）数据泥团 (Data Clump): 多个数据项总是一起出现在不同方法的参数中，暗示着它们应该被组合成一个独立的对象。
  （7）不必要的复杂性 (Needless Complexity): 用“杀牛刀”去解决“杀鸡”的问题，过度设计使系统变得臃肿且难以理解。
- 【非常重要！！】无论是你自己编写代码，还是阅读或审核他人代码时，都要严格遵守上述硬性指标，以及时刻关注优雅的架构设计。
- 【非常重要！！】无论何时，一旦你识别出那些可能侵蚀我们代码质量的「坏味道」，都应当立即询问用户是否需要优化，并给出合理的优化建议。

## Run & Debug

- 必须首先在项目的 scripts/ 目录下，维护好 Run & Debug 需要用到的全部 .sh 脚本
- 对于所有 Run & Debug 操作，一律使用 scripts/ 目录下的 .sh 脚本进行启停。永远不要直接使用 npm、pnpm、uv、python 等等命令
- 如果 .sh 脚本执行失败，无论是 .sh 本身的问题还是其他代码问题，需要先紧急修复。然后仍然坚持用 .sh 脚本进行启停
- Run & Debug 之前，为所有项目配置 Logger with File Output，并统一输出到 logs/ 目录下

## Python

- 数据结构尽可能全部定义成强类型。如果个别场景不得不使用未经结构化定义的 dict，需要先停下来征求用户的同意
- Python 虚拟环境永远使用 .venv 作为目录名
- 必须使用 uv，而不是 pip、poetry、conda、python3、python。包括依赖管理、构建、调试启动等所有环节
- 项目的根目录必须保持简洁，只保留必须存在的文件
- main.py 内容也要简洁。只保留必须存在的代码

## React / Next.js / TypeScript / JavaScript

- Next.js 强制使用 v15.4 版本，不要再用 v15.3 或 v14 或以下版本
- React 强制使用 v19 版本，不要再用 v18 或以下版本
- Tailwind CSS 强制使用 Tailwind CSS v4。不要再用 v3 或以下版本
- 严禁使用 commonjs 模块系统
- 尽可能使用 TypeScript。只有在构建工具完全不支持 TypeScript 的时候，才使用 JavaScript（如微信小程序的主工程）
- 数据结构尽可能全部定义成强类型。如果个别场景不得不使用 any 或未经结构化定义的 json，需要先停下来征求用户的同意
