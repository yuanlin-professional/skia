# BuildApi 主接口

> 源文件: infra/bots/recipe_modules/build/api.py

## 概述

`api.py` 定义了 `BuildApi` 类,这是 Skia 构建系统在 Recipe 中的统一入口点。该类实现了策略模式,根据构建器名称自动选择合适的编译函数和产物复制函数,支持 Android、Chromebook、CanvasKit、CMake、Docker 和默认(GN/Ninja)等多种构建方式。

## 架构位置

该模块位于构建系统的抽象层:

- **层级**: 基础设施 / 构建 API / 策略分发
- **功能域**: 构建入口点和策略选择
- **设计模式**: 策略模式 + 门面模式
- **调用者**: 所有构建相关的 Recipe

## 主要类与结构体

### BuildApi

继承自 `recipe_api.RecipeApi` 的主要 API 类。

**核心职责**:
1. 根据构建器名称选择构建策略
2. 提供统一的编译接口
3. 提供统一的产物复制接口

**实例变量**:
- `compile_fn`: 编译函数引用
- `copy_fn`: 产物复制函数引用

## 公共 API 函数

### __init__

```python
def __init__(self, buildername, *args, **kwargs):
```

**功能**: 初始化 BuildApi,根据构建器名称选择策略。

**参数**:
- `buildername`: 构建器名称字符串
- `*args`, `**kwargs`: 传递给父类的参数

**策略选择逻辑**:

```python
if 'Android' in b and not 'Flutter' in b:
    # Android 构建 (排除 Flutter)
    self.compile_fn = android.compile_fn
    self.copy_fn = android.copy_build_products
elif 'Chromebook' in b:
    # Chromebook 构建
    self.compile_fn = chromebook.compile_fn
    self.copy_fn = chromebook.copy_build_products
elif 'EMCC' in b and not 'StandaloneWasm' in b:
    # CanvasKit (WebAssembly)
    self.compile_fn = canvaskit.compile_fn
    self.copy_fn = canvaskit.copy_build_products
elif 'CMake' in b:
    # CMake 构建
    self.compile_fn = cmake.compile_fn
    self.copy_fn = cmake.copy_build_products
elif 'Docker' in b:
    # Docker 容器化构建
    self.compile_fn = docker.compile_fn
    self.copy_fn = docker.copy_build_products
else:
    # 默认 GN/Ninja 构建
    self.compile_fn = default.compile_fn
    self.copy_fn = default.copy_build_products
```

**特殊规则**:
- Android 构建排除 Flutter (Flutter 有自己的构建流程)
- CanvasKit 排除 StandaloneWasm (独立 Wasm 使用不同流程)

### __call__

```python
def __call__(self, checkout_root, out_dir):
    """Compile the code."""
    self.compile_fn(self.m, checkout_root, out_dir)
```

**功能**: 执行编译操作 (可调用对象协议)。

**参数**:
- `checkout_root`: 源码根目录
- `out_dir`: 构建输出目录

**实现**: 委托给选定的 `compile_fn`

**使用方式**:
```python
api.build(checkout_root, out_dir)  # 直接调用对象
```

### copy_build_products

```python
def copy_build_products(self, out_dir, dst):
    """Copy selected build products to dst."""
    self.copy_fn(self.m, out_dir, dst)
```

**功能**: 复制构建产物到目标目录。

**参数**:
- `out_dir`: 构建输出目录
- `dst`: 目标目录

**实现**: 委托给选定的 `copy_fn`

## 内部实现细节

### 导入结构

```python
from . import android
from . import canvaskit
from . import chromebook
from . import cmake
from . import default
from . import docker
```

所有策略模块在初始化时导入,保持代码结构清晰。

### 策略函数签名

所有 `compile_fn` 遵循统一签名:
```python
def compile_fn(api, checkout_root, out_dir):
    # 编译实现
```

所有 `copy_fn` 遵循统一签名:
```python
def copy_build_products(api, src, dst):
    # 复制实现
```

### Recipe API 访问

通过 `self.m` 访问其他 Recipe 模块:
```python
self.compile_fn(self.m, checkout_root, out_dir)
```

`self.m` 是 `recipe_api.RecipeApi` 提供的模块访问器。

### 构建器名称解析

使用简单的字符串包含检查:
- 优点: 简单直观,易于理解
- 缺点: 可能有歧义(如同时包含多个关键字)
- 实践: Skia 的构建器命名规范避免了冲突

## 依赖关系

### 直接依赖
- `android.py`: Android 构建策略
- `canvaskit.py`: CanvasKit 构建策略
- `chromebook.py`: Chromebook 构建策略
- `cmake.py`: CMake 构建策略
- `default.py`: 默认 GN 构建策略
- `docker.py`: Docker 容器化构建策略
- `recipe_engine`: Recipe Engine 框架

### 被依赖者
- `infra/bots/recipes/compile.py`: 编译 Recipe
- `infra/bots/recipes/sync_and_compile.py`: 同步和编译 Recipe
- `infra/bots/recipes/test.py`: 测试 Recipe (需要先编译)
- 其他需要编译 Skia 的 Recipe

### 依赖图

```
BuildApi
  ├── android.py
  ├── canvaskit.py
  ├── chromebook.py
  ├── cmake.py
  ├── docker.py
  └── default.py
        └── util.py
```

## 设计模式与设计决策

### 策略模式 (Strategy Pattern)

**意图**: 定义一系列算法,把它们封装起来,并使它们可以相互替换。

**实现**:
- **策略接口**: 统一的函数签名 (`compile_fn`, `copy_fn`)
- **具体策略**: 各个构建模块 (android, docker, etc.)
- **上下文**: `BuildApi` 类

**优势**:
- 新增构建方式只需添加新模块和选择逻辑
- 各策略独立维护,互不影响
- 运行时选择策略,灵活性高

### 门面模式 (Facade Pattern)

`BuildApi` 为复杂的构建子系统提供简化接口:
- 隐藏内部策略选择逻辑
- 提供 `__call__` 和 `copy_build_products` 两个简单方法
- Recipe 无需了解具体构建方式

### 命名约定驱动

通过构建器名称约定驱动策略选择:
- **约定**: 构建器名称包含平台/工具标识
- **好处**: 无需额外配置,自描述
- **示例**:
  - `Build-Debian11-GCC-x86_64-Release-Docker` → Docker 策略
  - `Build-Mac-Clang-arm64-Release-iOS` → 默认策略

### 可调用对象协议

实现 `__call__` 方法:
```python
api.build(checkout_root, out_dir)
```

更简洁的调用语法,符合 Python 习惯用法。

## 性能考量

### 初始化开销

- **模块导入**: 所有策略模块在类定义时导入
- **选择逻辑**: 简单字符串检查,O(1) 时间复杂度
- **内存占用**: 所有策略代码都加载,但未执行

**优化空间**: 延迟导入(按需加载策略模块)

### 运行时开销

- **策略选择**: 构造时一次性完成,无运行时开销
- **函数调用**: 直接调用,无额外间接层
- **委托开销**: 单层委托,性能影响可忽略

### 缓存和复用

Recipe 通常在单次执行中只创建一个 `BuildApi` 实例:
- 策略选择只执行一次
- 函数引用存储在实例变量中
- 后续调用直接使用缓存的引用

## 相关文件

### 策略实现
- `infra/bots/recipe_modules/build/android.py`: Android 构建
- `infra/bots/recipe_modules/build/canvaskit.py`: CanvasKit 构建
- `infra/bots/recipe_modules/build/chromebook.py`: Chromebook 构建
- `infra/bots/recipe_modules/build/cmake.py`: CMake 构建
- `infra/bots/recipe_modules/build/docker.py`: Docker 构建
- `infra/bots/recipe_modules/build/default.py`: 默认 GN 构建
- `infra/bots/recipe_modules/build/util.py`: 共享工具函数

### 模块定义
- `infra/bots/recipe_modules/build/__init__.py`: 模块入口点

### 使用示例
- `infra/bots/recipe_modules/build/examples/full.py`: 完整使用示例
- `infra/bots/recipes/compile.py`: 实际调用示例

### 构建器配置
- `infra/bots/tasks.json`: 构建器名称和配置
- `infra/bots/jobs.json`: 任务调度

### 测试
- `.recipes/*.expected/`: Recipe 测试期望输出
- 各策略模块的单元测试

该模块是 Skia 构建系统的核心抽象,通过策略模式优雅地支持多种构建方式,同时保持简洁的对外接口。这种设计使得添加新的构建方式变得简单,只需实现统一的函数签名并在初始化时注册即可。
