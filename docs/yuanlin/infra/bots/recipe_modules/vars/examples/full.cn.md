# Vars Module 测试示例

> 源文件: `infra/bots/recipe_modules/vars/examples/full.py`

## 概述

`full.py` 是 Vars 配方模块的测试示例，验证 `SkiaVarsApi` 的各个属性和方法在不同构建场景下的行为。覆盖了 Linux Release、Windows Debug（trybot）和整数 issue ID 等测试用例。

## 架构位置

位于 `infra/bots/recipe_modules/vars/examples/` 目录，是 LUCI 配方模块的标准测试文件。

## 主要类与结构体

无。

## 公共 API 函数

- `RunSteps(api)`: 执行 setup 并展示所有变量属性
- `GenTests(api)`: 生成多种测试场景

## 内部实现细节

1. `RunSteps` 调用 `api.vars.setup()`，然后读取 swarming_bot_id 和 swarming_task_id
2. 展示步骤显示 16 个变量属性
3. 测试构建器:
   - `Build-Debian10-Clang-x86_64-Release-SKVX_DISABLE_SIMD`
   - `Housekeeper-Weekly-RecreateSKPs`
   - `Test-Win11-Clang-Dell3930-GPU-GTX1660-x86_64-Debug-All`（Windows trybot）
   - `Upload-Test-Debian10-Clang-GCE-CPU-AVX2-x86_64-Debug-All-ASAN_Vulkan`（整数 issue 测试）

## 依赖关系

- `vars`, `recipe_engine/path`, `recipe_engine/platform`, `recipe_engine/properties`, `recipe_engine/step`

## 设计模式与设计决策

- 多场景测试: 覆盖不同 OS、角色、trybot 状态
- 属性展示: 将所有变量输出到步骤 presentation，便于调试

## 性能考量

无。

## 相关文件

- `infra/bots/recipe_modules/vars/api.py`: 被测试的 API
