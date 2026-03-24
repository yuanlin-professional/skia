# Gold Upload Module 测试示例

> 源文件: `infra/bots/recipe_modules/gold_upload/examples/full.py`

## 概述

`full.py` 是 Gold Upload 配方模块的测试示例，验证测试结果上传流程在 Android（trybot）和 Mac（Graphite）两种平台配置下的正确行为。

## 架构位置

位于 `infra/bots/recipe_modules/gold_upload/examples/` 目录。

## 主要类与结构体

无。

## 公共 API 函数

- `RunSteps(api)`: 设置 vars 和 flavor，执行 gold_upload.upload()
- `GenTests(api)`: 生成两种测试场景

## 内部实现细节

1. **upload_tests**: Android Pixel5 Vulkan Release 测试（trybot 场景，含 patch_ref/issue/patchset）
2. **upload_mac**: Mac Intel Graphite Debug 测试（Mac 平台，验证并行限制）

## 依赖关系

- `gold_upload`, `flavor`, `recipe_engine/path`, `recipe_engine/platform`, `recipe_engine/properties`, `recipe_engine/step`, `run`, `vars`

## 设计模式与设计决策

- 覆盖 trybot 和非 trybot 场景
- 覆盖 Android 和 Mac 平台差异

## 性能考量

无。

## 相关文件

- `infra/bots/recipe_modules/gold_upload/api.py`: 被测试的 API
