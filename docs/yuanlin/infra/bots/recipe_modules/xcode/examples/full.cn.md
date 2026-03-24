# Xcode Module 测试示例

> 源文件: `infra/bots/recipe_modules/xcode/examples/full.py`

## 概述

`full.py` 是 Xcode 配方模块的测试示例，验证 `vars.setup()` 和 `xcode.install()` 的基本执行流程。

## 架构位置

位于 `infra/bots/recipe_modules/xcode/examples/` 目录，是 LUCI 配方模块的标准测试示例。

## 主要类与结构体

无。

## 公共 API 函数

- `RunSteps(api)`: 执行 vars setup 和 xcode install
- `GenTests(api)`: 生成测试用例（iOS arm64 Debug 构建场景）

## 内部实现细节

测试模拟 `Build-Mac-Clang-arm64-Debug-iOS` 构建场景，验证 Xcode 安装流程。

## 依赖关系

- `recipe_engine/properties`, `vars`, `xcode`

## 设计模式与设计决策

LUCI 配方测试的标准模式：RunSteps + GenTests。

## 性能考量

无。

## 相关文件

- `infra/bots/recipe_modules/xcode/api.py`: 被测试的 API
