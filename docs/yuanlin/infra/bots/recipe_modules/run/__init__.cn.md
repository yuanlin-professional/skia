# Run Recipe 模块初始化

> 源文件: infra/bots/recipe_modules/run/__init__.py

## 概述

`__init__.py` 是 `run` Recipe 模块的入口点和配置文件。Run 模块提供命令执行、失败处理、文件操作和资产版本管理等核心功能,是 Skia Recipe 系统中使用最广泛的工具模块之一。该文件定义了模块的依赖关系和 API 类绑定。

## 架构位置

该文件位于 Recipe 模块的元数据层:

- **层级**: 基础设施 / Recipe 模块定义
- **功能域**: 命令执行和工具函数
- **作用**: 模块初始化和依赖声明
- **使用者**: 几乎所有 Skia Recipe

## 主要类与结构体

### DEPS (依赖列表)

```python
DEPS = [
    'env',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/step',
    'vars',
]
```

声明模块依赖的其他 Recipe 模块。

### API (API 类绑定)

```python
API = _api.SkiaStepApi
```

指定模块的 API 实现类为 `SkiaStepApi`。

## 公共 API 函数

该文件本身不提供函数,而是通过配置对象暴露功能。

### 依赖说明

**自定义模块**:
- `env`: 环境变量管理
- `vars`: Skia 变量管理(构建器配置等)

**Recipe Engine 内置模块**:
- `file`: 文件系统操作
- `path`: 路径处理
- `properties`: 构建属性访问
- `step`: 步骤执行

## 内部实现细节

### 导入结构

```python
from . import api as _api
```

使用相对导入加载 `api.py` 模块,其中包含 `SkiaStepApi` 实现。

### API 类引用

Recipe Engine 会自动实例化 `SkiaStepApi` 类:
- 传入依赖模块作为 `api.xxx` 可用
- 提供丰富的命令执行和工具函数
- 支持失败处理和重试逻辑

## 依赖关系

### 模块依赖图

```
run module
  ├── env (环境变量)
  ├── vars (Skia 变量)
  ├── recipe_engine/file (文件操作)
  ├── recipe_engine/path (路径处理)
  ├── recipe_engine/properties (属性访问)
  └── recipe_engine/step (步骤执行)
```

### 被依赖者

几乎所有 Skia Recipe 模块都依赖 `run`:
- `build`: 构建模块
- `flavor`: 测试执行模块
- `docker`: Docker 操作
- `doxygen`: 文档生成
- `infra`: 基础设施任务
- 所有 Recipe 文件

### 核心地位

`run` 模块是 Skia Recipe 系统的基础层:
- 提供命令执行抽象
- 统一失败处理
- 简化文件操作
- 管理资产版本

## 设计模式与设计决策

### 最小依赖

只依赖必要的模块:
- `env` 和 `vars` 用于配置
- Recipe Engine 核心模块用于基础功能
- 保持模块轻量和高效

### 功能聚合

将相关功能聚合在一个模块:
- 命令执行
- 文件操作
- 失败处理
- 资产管理

**优势**:
- 减少模块数量
- 简化依赖关系
- 提供一站式工具集

### 命名简洁

模块名 `run` 简短直观:
- 易于记忆和使用
- 反映主要功能(运行命令)
- 符合 Recipe 命名惯例

## 性能考量

### 模块加载

- **轻量级**: 最小依赖确保快速加载
- **延迟初始化**: SkiaStepApi 按需初始化内部状态
- **共享实例**: Recipe 通常只创建一个实例

### 运行时开销

- **无额外层**: 直接调用底层 API
- **状态管理**: 失败步骤列表和缓存开销极小
- **高频调用**: 优化用于频繁执行

## 相关文件

### 同模块文件
- `infra/bots/recipe_modules/run/api.py`: SkiaStepApi 实现
- `infra/bots/recipe_modules/run/examples/full.py`: 使用示例和测试

### 依赖模块
- `infra/bots/recipe_modules/env/`: env 模块
- `infra/bots/recipe_modules/vars/`: vars 模块
- `recipe_engine/`: Recipe Engine 核心

### 使用者
- 几乎所有 `infra/bots/recipe_modules/*/` 下的模块
- 所有 `infra/bots/recipes/*.py` Recipe 文件

### 测试
- `.recipes/*.expected/`: 测试期望输出
- Run 模块测试用例

该文件虽然简短,但定义了 Skia Recipe 系统中最重要的工具模块之一,为命令执行和常用操作提供统一的、易于使用的接口。
