# Checkout Module 测试示例

> 源文件: `infra/bots/recipe_modules/checkout/examples/full.py`

## 概述

`full.py` 是 Checkout 配方模块的测试示例，验证纯 Git 检出（NoDEPS）和 bot_update 检出两种模式，以及 trybot 和跨仓库补丁的场景。

## 架构位置

位于 `infra/bots/recipe_modules/checkout/examples/` 目录。

## 主要类与结构体

无。

## 公共 API 函数

- `RunSteps(api)`: 根据构建器名称选择检出模式
- `GenTests(api)`: 生成三种测试场景

## 内部实现细节

1. **NoDEPS 构建器**: 使用 `api.checkout.git()` 纯 Git 检出
2. **正常构建器**: 使用 `api.checkout.bot_update()` 完整检出
3. 测试场景:
   - `Build-Debian10-Clang-x86_64-Release-NoDEPS`: 纯 Git + trybot
   - `cross_repo_trybot`: 跨仓库（parent_repo）补丁
   - `trybot`: 标准 trybot 场景

## 依赖关系

- `checkout`, `recipe_engine/file`, `recipe_engine/path`, `recipe_engine/platform`, `recipe_engine/properties`, `run`, `vars`

## 设计模式与设计决策

- 基于构建器名称中的 "NoDEPS" 关键字自动选择检出策略

## 性能考量

无。

## 相关文件

- `infra/bots/recipe_modules/checkout/api.py`: 被测试的 API
