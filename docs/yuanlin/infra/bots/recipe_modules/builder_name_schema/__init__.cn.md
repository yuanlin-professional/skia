# __init__.py - Builder Name Schema 模块初始化

> 源文件:
> - `infra/bots/recipe_modules/builder_name_schema/__init__.py`

## 概述

`__init__.py` 是 `builder_name_schema` Recipe 模块的初始化文件，负责声明模块的依赖关系并注册公共 API 类。该文件是 Recipe 引擎模块系统的标准入口点，将 `BuilderNameSchemaApi` 暴露为模块的公共接口。

在 Chromium Recipe 引擎的模块系统中，每个模块目录必须包含一个 `__init__.py` 文件，其中定义 `DEPS` 列表（声明对其他模块的依赖）和 `API` 变量（指向模块的公共 API 类）。Recipe 引擎在启动时会扫描所有模块目录，加载这些初始化文件，并根据 `DEPS` 构建模块依赖图，然后将各模块的 API 实例注入到 Recipe 步骤函数的 `api` 参数中。

## 架构位置

```
infra/bots/recipe_modules/builder_name_schema/
├── __init__.py (模块注册)  <── 本文件
├── api.py (BuilderNameSchemaApi)
├── builder_name_schema.py (核心逻辑)
├── builder_name_schema.json (命名规则定义)
└── examples/full.py (测试用例)
```

## 主要类与结构体

无。本文件仅进行模块注册。

## 公共 API 函数

无函数定义。

## 内部实现细节

### 模块注册代码

```python
from . import api as _api

DEPS = []

API = _api.BuilderNameSchemaApi
```

### 各字段含义

- **`DEPS = []`**: 声明该模块在 Recipe 级别没有依赖其他模块。这意味着 `BuilderNameSchemaApi` 的构造和使用不需要其他 Recipe 模块的 API 实例。与之对比，`flavor` 模块的 `DEPS` 中包含 `run`、`vars` 等依赖
- **`API = _api.BuilderNameSchemaApi`**: 将 `BuilderNameSchemaApi` 类注册为模块的公共 API。注册后，任何在 `DEPS` 中声明了 `builder_name_schema` 依赖的 Recipe 模块，都可以通过 `api.builder_name_schema` 访问该 API 实例
- **`from . import api as _api`**: 使用相对导入并使用 `_api` 这一下划线前缀名称，这是 Python 的约定，表示该名称是模块内部使用的，不应被外部直接引用

### Recipe 引擎的模块加载流程

1. Recipe 引擎扫描 `recipe_modules/` 目录下的所有子目录
2. 加载每个子目录的 `__init__.py`
3. 读取 `DEPS` 构建依赖拓扑排序
4. 按顺序实例化各模块的 `API` 类
5. 将实例化的 API 对象注入到 Recipe 的 `api` 参数中

## 依赖关系

- **内部**: `api.py`（`BuilderNameSchemaApi` 类）
- **外部**: 无 Recipe 依赖（`DEPS` 为空）

## 设计模式与设计决策

- **Recipe 模块约定**: 遵循 Recipe 引擎的模块注册约定（`DEPS`、`API` 变量）
- **零依赖**: 该模块完全自包含，不依赖其他 Recipe 模块
- **私有导入**: 使用 `_api` 前缀避免名称冲突

## 性能考量

无运行时性能影响。模块注册在 Recipe 引擎启动时一次性完成。

## 相关文件

- `infra/bots/recipe_modules/builder_name_schema/api.py` - API 类定义（`BuilderNameSchemaApi`）
- `infra/bots/recipe_modules/builder_name_schema/builder_name_schema.py` - 核心解析逻辑
- `infra/bots/recipe_modules/builder_name_schema/builder_name_schema.json` - 命名规则 JSON 配置
- `infra/bots/recipe_modules/builder_name_schema/examples/full.py` - 模块测试用例
- `infra/bots/recipe_modules/vars/__init__.py` - vars 模块初始化（依赖本模块的典型使用者）
