# Flavor 模块初始化

> 源文件: infra/bots/recipe_modules/flavor/__init__.py

## 概述

这是 `flavor` recipe 模块的初始化文件,定义了模块的依赖关系和对外暴露的 API 类。`flavor` 模块是 Skia 构建基础设施中的核心抽象层,用于处理不同平台(桌面、Android、iOS、Chromebook)上的代码执行差异。该文件通过声明依赖和导出 API 类,建立了 flavor 系统的入口点。

## 架构位置

该文件是 recipe 模块系统的标准组成部分:
- 位于 `recipe_modules/flavor/` 目录根目录
- 被 Recipe Engine 自动加载
- 定义模块的公共接口
- 连接内部实现与外部使用者

**模块加载流程:**
```
Recipe Engine
  → 扫描 recipe_modules/
  → 读取 __init__.py
  → 加载 DEPS 依赖
  → 实例化 API 类
```

## 主要类与结构体

### DEPS 依赖声明

```python
DEPS = [
  'env',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'run',
  'vars',
  'xcode',
]
```

**依赖分类:**

**自定义模块:**
- `env`: 环境变量管理
- `run`: 命令执行和重试
- `vars`: 构建器变量
- `xcode`: Xcode 管理(iOS)

**Recipe Engine 核心模块:**
- `context`: 执行上下文
- `file`: 文件操作
- `json`: JSON 处理
- `path`: 路径处理
- `platform`: 平台检测
- `raw_io`: 原始 I/O
- `step`: 步骤执行

### API 导出

```python
API = _api.SkiaFlavorApi
```

导出 `SkiaFlavorApi` 类作为模块的公共 API 接口。

## 公共 API 函数

### 模块导入机制

Recipe Engine 通过以下方式使用该模块:

1. **依赖注入:**
```python
# 在其他 recipe 中
DEPS = ['flavor']

def RunSteps(api):
    api.flavor.setup('dm')  # 访问 SkiaFlavorApi
```

2. **API 实例化:**
Recipe Engine 自动创建 `SkiaFlavorApi` 实例并注入到 `api` 对象中。

3. **依赖传递:**
所有 DEPS 中声明的模块都会被传递给 API 类构造函数。

## 内部实现细节

### 模块加载机制

**Recipe Engine 的处理流程:**

1. **发现模块:**
   - 扫描 `recipe_modules/` 目录
   - 识别包含 `__init__.py` 的目录

2. **解析依赖:**
   - 读取 `DEPS` 列表
   - 构建依赖图
   - 进行拓扑排序

3. **实例化 API:**
   - 创建 `API` 类的实例
   - 注入依赖的模块
   - 绑定到 `api` 对象

4. **命名空间:**
   - 模块名为目录名(`flavor`)
   - 通过 `api.flavor` 访问

### 依赖解析顺序

Recipe Engine 确保依赖按正确顺序加载:
```
recipe_engine/* (核心模块)
  ↓
env, run, vars, xcode (自定义模块)
  ↓
flavor (当前模块)
  ↓
使用 flavor 的 recipe
```

### 循环依赖避免

Recipe 系统不允许循环依赖:
- `flavor` 依赖 `run`
- `run` 不能依赖 `flavor`
- 违反会导致加载失败

## 依赖关系

### 依赖图

```
flavor
├── env (环境变量)
├── run (命令执行)
├── vars (构建变量)
├── xcode (iOS 支持)
├── recipe_engine/context
├── recipe_engine/file
├── recipe_engine/json
├── recipe_engine/path
├── recipe_engine/platform
├── recipe_engine/raw_io
└── recipe_engine/step
```

### 被依赖者

该模块被以下 recipe 使用:
- `recipes/test.py`: 运行测试
- `recipes/perf.py`: 性能测试
- `recipes/compile.py`: 编译任务
- 其他需要跨平台执行的 recipe

### 传递依赖

使用 `flavor` 的 recipe 自动获得其所有依赖:
```python
# 在使用 flavor 的 recipe 中
DEPS = ['flavor']
# 自动可用: env, run, vars, xcode, 等
```

## 设计模式与设计决策

### 依赖注入模式

Recipe Engine 使用依赖注入:
- **优点:** 松耦合
- **优点:** 易于测试
- **优点:** 依赖明确

### 抽象工厂模式

`SkiaFlavorApi` 作为工厂类:
- 根据平台创建不同的 Flavor 实现
- 隐藏实现细节
- 提供统一接口

### 命名空间隔离

每个模块有独立的命名空间:
- 避免名称冲突
- 清晰的模块边界
- 便于维护和重构

### 最小依赖原则

仅声明必需的依赖:
- 减少加载时间
- 降低复杂度
- 提高模块独立性

## 性能考量

### 模块加载开销

**一次性成本:**
- 模块发现和解析: 毫秒级
- 依赖图构建: O(n + e),n 为模块数,e 为依赖边数
- API 实例化: 微秒级

**优化策略:**
- 延迟加载依赖(Recipe Engine 内部)
- 缓存模块元数据
- 最小化依赖数量

### 运行时性能

**依赖注入的开销:**
- 几乎为零
- 仅在初始化时解析
- 后续访问是直接引用

**最佳实践:**
- 避免过深的依赖链
- 合理拆分模块职责
- 控制依赖数量(推荐 < 15)

## 相关文件

**模块核心:**
- `api.py`: `SkiaFlavorApi` 实现
- `default.py`: 默认 Flavor 实现
- `android.py`: Android Flavor
- `ios.py`: iOS Flavor
- `chromebook.py`: Chromebook Flavor
- `ssh.py`: SSH 基类

**示例和测试:**
- `examples/full.py`: 完整使用示例
- Recipe Engine 测试框架自动测试

**文档:**
- Recipe Engine 官方文档
- Skia 构建系统文档
- 各平台 Flavor 的详细文档

**使用该模块的 Recipe:**
- `recipes/test.py`
- `recipes/perf.py`
- `recipes/compile.py`
- 其他测试和构建 recipe
