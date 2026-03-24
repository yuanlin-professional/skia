# Housekeeper Recipe (日常维护任务)

> 源文件: `infra/bots/recipes/housekeeper.py`

## 概述

此 recipe 实现了 Skia 的 PerCommit Housekeeper（每次提交触发的日常维护）任务。它的主要职责是在每次代码提交后执行代码库维护工作，目前的核心功能是生成并上传 Skia API 的 Doxygen 文档。该任务仅在非 trybot 的 CI 构建中执行文档生成，trybot 构建则跳过此步骤。

## 架构位置

Housekeeper recipe 位于 Skia CI 基础设施的维护任务层：

- **触发方式**: 每次提交到主分支后由任务调度器触发
- **职责范围**: 代码库维护（文档生成、静态分析等）
- **与构建/测试平行**: 独立于编译和测试流水线，不阻塞其他任务

## 主要类与结构体

| 名称 | 类型 | 说明 |
|------|------|------|
| `DEPS` | 列表 | 依赖模块：checkout、doxygen、file、path、properties、run、vars |

## 公共 API 函数

### `RunSteps(api)`

Recipe 入口函数，执行以下步骤：
1. 初始化构建变量 (`api.vars.setup()`)
2. 使用 bot_update 检出代码到默认检出根目录
3. 创建临时目录
4. 对非 trybot 构建，调用 `api.doxygen.generate_and_upload` 生成并上传 Doxygen 文档

### `GenTests(api)`

生成两个测试用例：
- `Housekeeper-PerCommit` -- 标准 CI 构建，会执行文档生成
- `Housekeeper-PerCommit-Trybot` -- Trybot 构建，跳过文档生成

## 内部实现细节

- **Trybot 条件判断**: 使用 `api.vars.is_trybot` 检查是否为 trybot 构建，仅在 CI 构建（非 trybot）时生成文档
- **Doxygen 生成**: 委托给 `api.doxygen.generate_and_upload(skia_dir)` 方法，传入 Skia 源代码根目录
- **TODO 注释**: 源代码中有关于检测静态初始化器（static initializers）的 TODO，表明未来可能扩展维护任务范围
- **检出路径**: 使用 `api.checkout.default_checkout_root` 和 `checkout_root.joinpath('skia')` 获取 Skia 目录

## 依赖关系

- **checkout** -- 代码检出模块
- **doxygen** -- Doxygen 文档生成和上传模块
- **run** -- 步骤执行模块
- **vars** -- 构建变量管理
- **recipe_engine/file** -- 文件操作
- **recipe_engine/path** -- 路径操作
- **recipe_engine/properties** -- 构建属性

## 设计模式与设计决策

- **CI/Trybot 分离**: Trybot 构建跳过文档生成，避免每个代码审查都触发文档部署
- **单一职责**: 当前仅负责文档生成，但架构预留了扩展空间（如静态初始化器检测）
- **委托模式**: 文档生成的具体逻辑委托给专门的 `doxygen` recipe 模块，保持 recipe 本身简洁
- **默认检出路径**: 使用 `default_checkout_root` 而非硬编码路径，提高可移植性

## 性能考量

- Doxygen 文档生成是 I/O 和 CPU 密集型操作，但由于独立运行不影响其他构建/测试任务
- 仅在非 trybot 构建时执行文档生成，减少了 trybot 的运行时间
- bot_update 检出是主要的时间开销

## 相关文件

- `infra/bots/recipe_modules/doxygen/` -- Doxygen 文档生成模块
- `infra/bots/recipe_modules/checkout/` -- 代码检出模块
- `infra/bots/recipe_modules/vars/` -- 构建变量模块
- `include/` -- Skia 公共头文件（Doxygen 文档的源材料）
