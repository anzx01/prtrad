# CORS 跨域问题修复说明

## 问题描述

前端（http://localhost:3000）访问后端 API（http://localhost:8000）时出现 CORS 跨域错误：

```
Access to fetch at 'http://localhost:8000/markets' from origin 'http://localhost:3000' 
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present 
on the requested resource.
```

## 解决方案

已在 `apps/api/app/main.py` 中添加 CORS 中间件配置：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 使配置生效

### 方法 1：重启所有服务（推荐）

```bash
# 停止当前服务（按 Ctrl+C）
# 然后重新启动
npm run dev
```

### 方法 2：仅重启 API 服务

```bash
# 停止 API 服务
# Windows
taskkill /F /PID 14884

# 然后重启 API
npm run dev:api
```

### 方法 3：使用启动脚本

```bash
# Windows
start.bat

# Linux/Mac
./start.sh
```

## 验证修复

重启服务后，在浏览器控制台应该不再看到 CORS 错误，前端可以正常访问后端 API。

## 生产环境配置

在生产环境中，需要将 `allow_origins` 修改为实际的前端域名：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-production-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

或者使用环境变量配置：

```python
import os

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 其他注意事项

浏览器控制台中的以下错误可以忽略（来自浏览器扩展）：
```
Unchecked runtime.lastError: A listener indicated an asynchronous response...
```

这是浏览器扩展的问题，不影响应用功能。
