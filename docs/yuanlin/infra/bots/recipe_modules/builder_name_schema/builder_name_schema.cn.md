# builder_name_schema.py - 构建器名称解析与生成

> 源文件:
> - `infra/bots/recipe_modules/builder_name_schema/builder_name_schema.py`

## 概述

builder_name_schema.py 是 Skia CI 基础设施中的构建器名称管理模块，提供构建器名称的解析（从名称字符串到字典）和生成（从字典到名称字符串）功能。构建器命名遵循严格的分层 schema，由 `builder_name_schema.json` 定义，使用连字符（`-`）分隔各部分。该模块是 Skia CI 系统中构建器配置管理的核心组件。

## 架构位置

```
builder_name_schema.json (命名规则定义)
    ↓ (加载)
builder_name_schema.py (解析引擎)  <── 本模块
    ↓ (封装)
api.py (BuilderNameSchemaApi)
    ↓ (使用)
各种 Recipe 脚本 (vars.py 等)
```

## 主要类与结构体

无类定义。本模块使用全局变量和自由函数。

### 全局变量

| 变量 | 描述 |
|------|------|
| `BUILDER_NAME_SCHEMA` | 从 JSON 加载的完整 schema 字典 |
| `BUILDER_NAME_SEP` | 名称部分分隔符（通常为 `-`）|
| `BUILDER_ROLES` | 所有构建器角色的元组 |

### 构建器角色

| 角色常量 | 值 |
|----------|-----|
| `BUILDER_ROLE_BAZELBUILD` | `BazelBuild` |
| `BUILDER_ROLE_BAZELTEST` | `BazelTest` |
| `BUILDER_ROLE_BUILD` | `Build` |
| `BUILDER_ROLE_BUILDSTATS` | `BuildStats` |
| `BUILDER_ROLE_CANARY` | `Canary` |
| `BUILDER_ROLE_CODESIZE` | `CodeSize` |
| `BUILDER_ROLE_HOUSEKEEPER` | `Housekeeper` |
| `BUILDER_ROLE_INFRA` | `Infra` |
| `BUILDER_ROLE_PERF` | `Perf` |
| `BUILDER_ROLE_TEST` | `Test` |
| `BUILDER_ROLE_UPLOAD` | `Upload` |

## 公共 API 函数

| 函数 | 描述 |
|------|------|
| `MakeBuilderName(**parts)` | 从关键字参数构建标准格式的构建器名称 |
| `DictForBuilderName(builder_name)` | 将构建器名称解析为字典 |

## 内部实现细节

### Schema 加载（_LoadSchema）

在模块导入时自动执行：
1. 从同目录下的 `builder_name_schema.json` 读取 JSON 配置
2. 使用 `ToStr` 递归函数将所有 unicode 字符串转换为 Python 字符串
3. 断言所有定义的 `BUILDER_ROLES` 都在 schema 中有对应条目

### 名称生成（MakeBuilderName）

使用递归 `process` 函数按照 schema 层次结构组装名称：

1. **验证**: 检查所有 part 值不包含分隔符
2. **角色处理**: 从 `parts` 中提取 `role`（或 `sub-role-N`）
3. **必需键**: 按 schema 定义的 `keys` 顺序提取值
4. **递归角色**: 如果 schema 定义了 `recurse_roles`，递归处理子角色
5. **可选键**: 按 schema 定义的 `optional_keys` 提取可选值
6. **剩余验证**: 如果 `parts` 中还有未处理的键，抛出 `ValueError`
7. **拼接**: 使用 `BUILDER_NAME_SEP` 连接所有部分

### 名称解析（DictForBuilderName）

反向操作，从名称字符串提取出字典：

1. 按分隔符拆分名称
2. 递归 `_parse` 函数按 schema 逐级匹配
3. 按 `keys` 消耗必需字段
4. 按 `recurse_roles` 检测并递归处理子角色
5. 按 `optional_keys` 消耗可选字段
6. 如果有剩余部分，抛出 `ValueError`

### 构建器名称格式示例

```
Build-Debian10-Clang-x64-Release-Android
├── role: Build
├── os: Debian10
├── compiler: Clang
├── target_arch: x64
├── configuration: Release
└── extra_config: Android

Upload-Test-Debian10-Clang-GCE-CPU-AVX2-x86_64-Debug-Shard_12-Coverage
├── role: Upload
├── sub-role-1: Test
├── os: Debian10
├── compiler: Clang
├── model: GCE
├── cpu_or_gpu: CPU
├── cpu_or_gpu_value: AVX2
├── arch: x86_64
├── configuration: Debug
├── test_filter: Shard_12
└── extra_config: Coverage
```

## 依赖关系

- **标准库**: `json`（JSON 解析）、`os`（文件路径操作）
- **数据文件**: `builder_name_schema.json`（命名规则定义）

## 设计模式与设计决策

- **数据驱动**: 命名规则完全由 JSON 配置定义，修改规则不需要改代码
- **递归角色**: 支持嵌套角色（如 `Upload` 包含 `Test` 或 `Perf`），实现了复合构建器的命名
- **严格验证**: `MakeBuilderName` 和 `DictForBuilderName` 都对输入进行严格验证，确保名称的正确性
- **双向可逆**: `DictForBuilderName(MakeBuilderName(**parts)) == parts`，保证序列化和反序列化的一致性
- **模块级初始化**: `_LoadSchema()` 在 `import` 时执行，避免运行时延迟

## 性能考量

- JSON schema 仅在模块导入时加载一次，后续调用直接使用内存中的字典
- 名称解析和生成都是线性时间复杂度，与名称部分数量成正比
- `ToStr` 函数中的类型检查开销可忽略（仅在初始化时执行一次）

## 相关文件

- `infra/bots/recipe_modules/builder_name_schema/builder_name_schema.json` - 命名规则 JSON 定义
- `infra/bots/recipe_modules/builder_name_schema/api.py` - Recipe API 封装
- `infra/bots/recipe_modules/builder_name_schema/__init__.py` - 模块初始化
- `infra/bots/recipe_modules/builder_name_schema/examples/full.py` - 测试用例
- `infra/bots/recipe_modules/vars/api.py` - 使用此模块解析构建器名称
