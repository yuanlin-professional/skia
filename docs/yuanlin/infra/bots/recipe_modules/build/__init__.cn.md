# Build Recipe 模块初始化

> 源文件: infra/bots/recipe_modules/build/__init__.py

## 概述

`__init__.py` 是 `build` Recipe 模块的入口点和配置文件。它定义了模块的依赖关系、属性和 API 类,是 Recipe Engine 加载和初始化构建模块的关键文件。该文件使用 Recipe Engine 的声明式配置,建立模块与其他组件之间的连接。

## 架构位置

该文件位于 Recipe 模块的元数据层:

- **层级**: 基础设施 / Recipe 模块定义
- **功能域**: 模块初始化和配置
- **作用**: 声明依赖、属性和 API 入口
- **加载时机**: Recipe Engine 启动时自动加载

## 主要类与结构体

该文件定义三个核心配置对象:

### DEPS (依赖列表)

```python
DEPS = [
    'depot_tools/gclient',
    'docker',
    'env',
    'infra',
    'recipe_engine/cipd',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/step',
    'run',
    'vars',
    'xcode',
]
```

声明模块依赖的其他 Recipe 模块。

### PROPERTIES (属性定义)

```python
PROPERTIES = {
    'buildername': Property(default=None),
}
```

定义可从外部传入的构建属性。

### API (API 类绑定)

```python
API = _api.BuildApi
```

指定模块的 API 实现类。

## 公共 API 函数

该文件本身不提供函数,而是通过配置对象暴露功能:

### 依赖声明

通过 `DEPS` 声明,模块可以访问:
- `api.gclient`: 源码同步工具
- `api.docker`: Docker 容器操作
- `api.env`: 环境变量管理
- `api.file`: 文件系统操作
- 等等

### 属性注入

通过 `PROPERTIES` 声明,Recipe 可以接收:
- `buildername`: 构建器名称 (可选,默认 None)

## 内部实现细节

### 导入结构

```python
from . import api as _api
from recipe_engine.recipe_api import Property
```

- 相对导入本地 `api.py` 模块
- 从 Recipe Engine 导入 `Property` 类

### 依赖分类

**Depot Tools 依赖**:
- `depot_tools/gclient`: Git 和 DEPS 管理

**自定义模块**:
- `docker`: Docker 容器支持
- `env`: 环境变量工具
- `infra`: 基础设施工具
- `run`: 命令执行包装
- `vars`: 变量管理
- `xcode`: macOS/iOS 开发工具

**Recipe Engine 内置模块**:
- `cipd`: CIPD 包管理器
- `context`: 执行上下文管理
- `file`: 文件操作
- `path`: 路径处理
- `step`: 步骤执行

### 属性默认值

```python
'buildername': Property(default=None)
```

- `default=None`: 允许不传入 buildername
- 实际使用时通常由 CI 系统自动注入
- BuildApi 初始化时会使用此值

### API 类引用

```python
API = _api.BuildApi
```

- Recipe Engine 会实例化 `BuildApi` 类
- 传入 `buildername` 属性作为构造参数
- 其他依赖作为 `api.xxx` 可用

## 依赖关系

### 模块依赖图

```
build module
  ├── depot_tools/gclient (源码管理)
  ├── docker (容器化构建)
  ├── env (环境配置)
  ├── infra (基础设施)
  ├── run (命令执行)
  ├── vars (变量管理)
  ├── xcode (Apple 开发)
  └── recipe_engine/* (核心功能)
```

### 被依赖者

- 所有构建类 Recipe:
  - `compile.py`
  - `sync_and_compile.py`
  - `test.py`
  - 等等

### 依赖传递

当其他 Recipe 依赖 `build` 模块时,它们间接获得:
- 所有 `DEPS` 中列出的模块访问权
- 通过 `api.build` 调用构建功能

## 设计模式与设计决策

### 声明式配置

使用模块级常量而非代码逻辑:
- **清晰性**: 一目了然的依赖关系
- **可分析性**: 工具可静态分析依赖图
- **标准化**: 符合 Recipe Engine 规范

### 依赖注入

Recipe Engine 基于声明自动注入依赖:
- 无需手动初始化依赖对象
- 测试时可以 mock 依赖
- 循环依赖在加载时检测

### 属性参数化

`buildername` 作为可选属性:
- 允许测试时不传入
- 实际运行时由 CI 系统提供
- BuildApi 可以根据名称选择构建策略

### 延迟加载

```python
from . import api as _api
```

使用 `_api` 私有导入避免命名冲突:
- `API` 变量引用类,而非模块
- Recipe Engine 按需实例化 API 类

## 性能考量

### 模块加载

- **初始化顺序**: Recipe Engine 自动处理依赖顺序
- **懒加载**: 只有实际使用的模块才完全初始化
- **缓存**: 模块定义在进程生命周期内缓存

### 依赖最小化

虽然依赖了 12 个模块,但都是必要的:
- 每个依赖支持特定构建场景
- 避免功能重复实现
- 共享模块减少总体内存占用

### 属性传递

属性通过 Recipe Engine 传递,无额外开销:
- 不涉及序列化/反序列化
- 直接作为构造参数传入

## 相关文件

### 同模块文件
- `infra/bots/recipe_modules/build/api.py`: BuildApi 实现类
- `infra/bots/recipe_modules/build/default.py`: 默认构建逻辑
- `infra/bots/recipe_modules/build/android.py`: Android 构建
- `infra/bots/recipe_modules/build/cmake.py`: CMake 构建
- `infra/bots/recipe_modules/build/docker.py`: Docker 构建
- `infra/bots/recipe_modules/build/chromebook.py`: Chromebook 构建
- `infra/bots/recipe_modules/build/canvaskit.py`: CanvasKit 构建
- `infra/bots/recipe_modules/build/util.py`: 工具函数

### 依赖模块
- `infra/bots/recipe_modules/vars/__init__.py`: vars 模块定义
- `infra/bots/recipe_modules/docker/__init__.py`: docker 模块定义
- `infra/bots/recipe_modules/run/__init__.py`: run 模块定义
- `recipe_engine/`: Recipe Engine 核心模块

### 使用示例
- `infra/bots/recipe_modules/build/examples/full.py`: 完整使用示例
- `infra/bots/recipes/compile.py`: 实际调用 build 模块的 Recipe

### Recipe Engine 文档
- Recipe Engine API 参考
- 模块开发指南
- 依赖管理文档

该文件虽然简短,但在 Recipe 模块系统中起着关键作用,它定义了模块的接口契约和依赖关系,是理解 build 模块如何集成到整个 Recipe 系统的入口点。
