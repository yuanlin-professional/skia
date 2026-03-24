# Doxygen Recipe 示例

> 源文件: infra/bots/recipe_modules/doxygen/examples/full.py

## 概述

该文件是 Doxygen Recipe 模块的完整使用示例和测试代码。它展示了如何在 Skia 的 Recipe 系统中调用 Doxygen API 来生成和上传文档,同时也作为自动化测试的基础,验证 Recipe 在各种配置下的正确性。

## 架构位置

该文件位于 Recipe 模块的测试示例层:

- **层级**: 基础设施 / Recipe 示例和测试
- **功能域**: 文档生成流程的集成测试
- **作用**: 既是使用示例,也是自动化测试用例
- **关系**: 演示 `doxygen` API 模块的正确使用方式

## 主要类与结构体

该文件不定义类,而是提供两个核心函数:

### RunSteps 函数

Recipe 的主要执行步骤函数。

### GenTests 函数

测试用例生成器,为 Recipe 测试框架提供测试场景。

## 公共 API 函数

### RunSteps

```python
def RunSteps(api):
    api.vars.setup()
    api.doxygen.generate_and_upload(api.path.start_dir)
```

**功能**: 定义 Recipe 的执行流程。

**执行步骤**:
1. 初始化构建变量 (`api.vars.setup()`)
2. 调用 Doxygen API 生成并上传文档

**参数**:
- `api`: Recipe Engine 提供的 API 对象

**特点**:
- 使用 `api.path.start_dir` 作为 Skia 目录
- 简洁的两步执行流程

### GenTests

```python
def GenTests(api):
    yield (
        api.test('doxygen') +
        api.properties(buildername='Housekeeper-PerCommit',
                       repository='https://skia.googlesource.com/skia.git',
                       revision='abc123',
                       path_config='kitchen',
                       swarm_out_dir='[SWARM_OUT_DIR]')
    )
```

**功能**: 生成测试用例,模拟真实的构建环境。

**测试配置**:
- **测试名称**: `doxygen`
- **构建器**: `Housekeeper-PerCommit` (定期维护任务)
- **仓库**: Skia 官方 Git 仓库
- **修订版本**: `abc123` (示例提交哈希)
- **路径配置**: `kitchen` (Kitchen 执行环境)
- **输出目录**: Swarming 输出目录的占位符

**返回值**: 生成器,yield 一个完整的测试用例

## 内部实现细节

### 依赖声明

```python
DEPS = [
    'doxygen',
    'recipe_engine/path',
    'recipe_engine/properties',
    'vars',
]
```

该 Recipe 依赖四个模块:
- `doxygen`: 本模块要演示的 API
- `recipe_engine/path`: 路径处理工具
- `recipe_engine/properties`: 构建属性访问
- `vars`: Skia 自定义的变量管理模块

### 执行上下文

Recipe 在以下上下文中运行:
- **构建器类型**: Housekeeper (维护类任务)
- **触发方式**: PerCommit (每次提交触发)
- **执行环境**: Kitchen (Google 内部的任务执行系统)
- **隔离环境**: Swarming (分布式任务调度系统)

### 变量初始化

`api.vars.setup()` 初始化 Skia 特定的构建变量,包括:
- 构建器名称解析
- 配置标志提取
- 路径设置
- 环境变量配置

## 依赖关系

### 模块依赖

```
full.py
  ├── doxygen (API 模块)
  ├── vars (变量管理)
  ├── recipe_engine/path (路径工具)
  └── recipe_engine/properties (属性访问)
```

### 数据流

1. Recipe Engine 注入 `properties` (构建属性)
2. `vars.setup()` 解析并存储配置
3. `doxygen.generate_and_upload()` 使用配置执行文档生成
4. 结果写入 `swarm_out_dir`

## 设计模式与设计决策

### 测试优先设计

将示例代码同时作为测试用例,遵循以下原则:
- **可验证性**: 每个示例都是可执行的测试
- **文档即代码**: 示例本身就是最好的使用文档
- **回归保护**: 自动化测试防止 API 破坏性变更

### 最小化原则

示例只包含必要的步骤:
1. 变量初始化
2. 文档生成

这种简洁性使得用户能快速理解核心流程。

### 真实环境模拟

测试用例使用真实的构建器名称和配置:
- `Housekeeper-PerCommit` 是实际存在的构建器
- 属性配置反映真实的执行环境
- 便于在本地复现 CI 环境

### 生成器模式

`GenTests` 使用 Python 生成器 (`yield`):
- 支持定义多个测试用例
- 测试框架可按需加载测试
- 内存效率高

## 性能考量

### 测试执行效率

- **快速反馈**: 示例代码执行路径短,测试运行快速
- **隔离性**: 每个测试在独立环境中运行,互不影响
- **并行化**: Recipe 测试框架支持并行执行多个测试

### 模拟数据

使用占位符 `[SWARM_OUT_DIR]` 而非真实路径:
- 避免文件系统 I/O
- 测试运行不依赖外部资源
- 提高测试可移植性

### 最小依赖

只依赖必要的模块,减少:
- 初始化开销
- 模块加载时间
- 测试环境复杂度

## 相关文件

### 同模块文件
- `infra/bots/recipe_modules/doxygen/api.py`: 被测试的主 API 模块
- `infra/bots/recipe_modules/doxygen/__init__.py`: 模块入口点
- `infra/bots/recipe_modules/doxygen/resources/`: 资源文件目录

### Recipe 框架文件
- `recipe_engine/`: Recipe Engine 核心框架
- `infra/bots/recipe_modules/vars/`: 变量管理模块

### 测试基础设施
- Recipe 测试框架 (Recipe Engine 的一部分)
- 测试运行器和报告工具

### 相关构建器
- `Housekeeper-PerCommit`: 实际使用此 Recipe 的构建任务
- 其他文档相关的 CI 任务

### 实际调用
- `.recipes/*.expected/`: 存储测试期望输出
- CI 配置文件中的任务定义

该文件是理解 Doxygen Recipe 使用方式的最佳起点,也是确保模块正确性的自动化测试基础。通过结合示例和测试,它为 Recipe 开发提供了清晰的模板和验证机制。
