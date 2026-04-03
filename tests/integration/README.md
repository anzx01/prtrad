# 集成测试

## 状态

集成测试框架已创建，但需要额外配置才能成功运行。

## 已创建的文件

- `tests/integration/conftest.py` - 测试fixture和数据库设置
- `tests/integration/test_api_markets.py` - Markets API端点测试（7个测试）
- `tests/integration/test_api_dq.py` - Data Quality API端点测试（7个测试）
- `tests/integration/test_api_tagging.py` - Tagging API端点测试（8个测试）

## 当前问题

集成测试无法运行，原因是SQLAlchemy引擎隔离问题。路由使用的是在模块导入时创建的生产引擎，使用pytest fixture很难覆盖测试引擎。

## 推荐解决方案

要使集成测试正常工作，应该实现以下方法之一：

### 方案1：依赖注入（推荐）
修改API路由使用FastAPI的依赖注入来获取数据库会话，而不是直接导入 `session_scope`：

```python
# 在路由中
from fastapi import Depends
from db.session import get_db

@router.get("/markets")
def list_markets(session: Session = Depends(get_db)):
    # 在这里使用session
```

这样测试可以轻松覆盖 `get_db`。

### 方案2：基于环境变量的引擎创建
修改 `db/session.py` 检查测试环境变量，如果设置则使用全局测试引擎：

```python
if os.getenv("PYTEST_CURRENT_TEST"):
    # 使用环境中的测试引擎
    engine = test_engine
else:
    # 使用生产引擎
    engine = create_engine(settings.database_url, ...)
```

### 方案3：使用真实数据库进行集成测试
不使用SQLite内存数据库，而是使用与生产环境匹配的真实测试数据库（PostgreSQL/MySQL），这样可以避免引擎兼容性问题。

## 运行单元测试

单元测试工作正常，可以运行：

```bash
pytest tests/test_*.py -v
```

所有17个单元测试都成功通过。
