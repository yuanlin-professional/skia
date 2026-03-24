# api.py - Builder Name Schema Recipe API

> 源文件:
> - `infra/bots/recipe_modules/builder_name_schema/api.py`

## 概述

api.py 是 `builder_name_schema` Recipe 模块的公共 API 层，将底层的 `builder_name_schema.py` 模块封装为 Recipe 引擎兼容的 API 类。它通过 `BuilderNameSchemaApi` 类暴露构建器名称的生成和解析功能，使其他 Recipe 模块能够通过 `api.builder_name_schema` 访问这些功能。

## 架构位置

```
builder_name_schema.py (核心逻辑)
    ↓ (封装)
api.py (Recipe API 层)  <── 本文件
    ↓ (注册于 __init__.py)
Recipe 引擎 → api.builder_name_schema.*
```

## 主要类与结构体

### `BuilderNameSchemaApi`

- **继承**: `recipe_api.RecipeApi`
- **暴露的属性**:
  - `BUILDER_NAME_SCHEMA`: 完整 schema 字典
  - `BUILDER_NAME_SEP`: 名称分隔符
  - `BUILDER_ROLE_BUILD` / `HOUSEKEEPER` / `INFRA` / `PERF` / `TEST`: 常用角色常量
  - `BUILDER_ROLES`: 所有角色元组

## 公共 API 函数

| 函数 | 描述 |
|------|------|
| `MakeBuilderName(**kwargs)` | 从关键字参数生成构建器名称（委托给 `builder_name_schema.MakeBuilderName`）|
| `DictForBuilderName(*args, **kwargs)` | 解析构建器名称为字典（委托给 `builder_name_schema.DictForBuilderName`）|

## 内部实现细节

`BuilderNameSchemaApi` 是一个纯粹的代理层：

```python
class BuilderNameSchemaApi(recipe_api.RecipeApi):
  def __init__(self, *args, **kwargs):
    super(BuilderNameSchemaApi, self).__init__(*args, **kwargs)
    # 直接引用底层模块的全局变量
    self.BUILDER_NAME_SCHEMA = builder_name_schema.BUILDER_NAME_SCHEMA
    self.BUILDER_NAME_SEP = builder_name_schema.BUILDER_NAME_SEP
    # ... 等常量
```

所有方法调用直接转发到 `builder_name_schema` 模块，不添加额外逻辑。

### 属性绑定详情

构造函数中绑定了以下底层模块属性：

| API 属性 | 底层模块来源 | 描述 |
|----------|-------------|------|
| `BUILDER_NAME_SCHEMA` | `builder_name_schema.BUILDER_NAME_SCHEMA` | 从 JSON 加载的完整命名规则 |
| `BUILDER_NAME_SEP` | `builder_name_schema.BUILDER_NAME_SEP` | 名称分隔符（`-`）|
| `BUILDER_ROLE_BUILD` | `builder_name_schema.BUILDER_ROLE_BUILD` | `'Build'` 角色常量 |
| `BUILDER_ROLE_HOUSEKEEPER` | `builder_name_schema.BUILDER_ROLE_HOUSEKEEPER` | `'Housekeeper'` 角色常量 |
| `BUILDER_ROLE_INFRA` | `builder_name_schema.BUILDER_ROLE_INFRA` | `'Infra'` 角色常量 |
| `BUILDER_ROLE_PERF` | `builder_name_schema.BUILDER_ROLE_PERF` | `'Perf'` 角色常量 |
| `BUILDER_ROLE_TEST` | `builder_name_schema.BUILDER_ROLE_TEST` | `'Test'` 角色常量 |
| `BUILDER_ROLES` | `builder_name_schema.BUILDER_ROLES` | 所有角色的元组 |

注意未暴露的角色包括：`BazelBuild`、`BazelTest`、`BuildStats`、`Canary`、`CodeSize`、`Upload`。这些角色不常在 Recipe 中直接使用，需要时可通过 `BUILDER_ROLES` 元组访问。

### 使用示例

在其他 Recipe 模块中的典型用法：

```python
# 解析构建器名称
cfg = api.builder_name_schema.DictForBuilderName(
    'Test-Debian10-Clang-GCE-CPU-AVX2-x86_64-Debug-All')
# cfg['role'] == 'Test'
# cfg['os'] == 'Debian10'
# cfg['compiler'] == 'Clang'

# 构建构建器名称
name = api.builder_name_schema.MakeBuilderName(
    role='Build', os='Debian10', compiler='Clang',
    target_arch='x64', configuration='Release')
# name == 'Build-Debian10-Clang-x64-Release'
```

## 依赖关系

- **Recipe 引擎**: `recipe_engine.recipe_api.RecipeApi`（基类）
- **核心模块**: `builder_name_schema.py`（实际实现）

## 设计模式与设计决策

- **代理模式**: 所有调用直接委托给底层模块，不添加任何额外逻辑
- **Recipe 适配**: 将普通 Python 模块适配为 Recipe 引擎 API 的标准做法
- **选择性暴露**: 只暴露常用的角色常量（Build、Housekeeper、Infra、Perf、Test），而非全部 11 种角色
- **构造时绑定**: 在 `__init__` 中绑定底层模块的属性，确保访问一致性

## 性能考量

API 层无额外开销，所有调用直接转发到底层模块。属性在构造时一次性绑定。

## 相关文件

- `infra/bots/recipe_modules/builder_name_schema/builder_name_schema.py` - 核心解析逻辑
- `infra/bots/recipe_modules/builder_name_schema/__init__.py` - 模块注册
- `infra/bots/recipe_modules/builder_name_schema/examples/full.py` - 测试用例
