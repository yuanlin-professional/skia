# SkOpts_RestoreTarget

> 源文件: `src/opts/SkOpts_RestoreTarget.h`

## 概述

`SkOpts_RestoreTarget.h` 是 Skia 优化系统中与 `SkOpts_SetTarget.h` 配对使用的编译环境恢复文件。它的唯一职责是撤销 `SkOpts_SetTarget.h` 对编译环境所做的修改，将 CPU 指令集级别宏和编译器目标属性恢复到包含 `SkOpts_SetTarget.h` 之前的状态。

与 `SkOpts_SetTarget.h` 一样，该文件有意不使用 include guard，因为它需要在同一编译单元中被多次包含。

## 架构位置

`SkOpts_RestoreTarget.h` 与 `SkOpts_SetTarget.h` 形成配对（bracket）关系，在 Skia 的多指令集编译架构中扮演"后括号"的角色：

```
#define SK_OPTS_TARGET SK_OPTS_TARGET_SSSE3
#include "src/opts/SkOpts_SetTarget.h"     // <-- 开始：设置 SSSE3 编译环境

#include "src/opts/SkSomeOptimized_opts.h" // 这些代码在 SSSE3 模式下编译

#include "src/opts/SkOpts_RestoreTarget.h" // <-- 结束：恢复原始编译环境（本文件）
#undef SK_OPTS_TARGET
```

## 主要类与结构体

该文件不定义任何类或结构体。它完全由预处理器指令组成。

## 公共 API 函数

该文件不包含任何函数定义。

## 内部实现细节

### 两种工作模式

#### 1. 默认目标模式（`SK_OPTS_TARGET_DEFAULT`）

```cpp
#if SK_OPTS_TARGET == SK_OPTS_TARGET_DEFAULT
    // Nothing to do here
```

当编译目标为默认值时，`SkOpts_SetTarget.h` 不会修改编译环境（只设置命名空间），因此不需要恢复任何内容。

#### 2. 指定目标模式

当 `SK_OPTS_TARGET` 为具体指令集（如 `SK_OPTS_TARGET_SSSE3`、`SK_OPTS_TARGET_HSW` 等）时，执行以下恢复操作：

**步骤 1 - 安全检查**:
```cpp
#if !defined(SK_OLD_CPU_SSE_LEVEL)
    #error Include SkOpts_SetTarget before including SkOpts_RestoreTarget
#endif
```
确保 `SkOpts_SetTarget.h` 确实已经被先行包含。如果未包含则产生编译错误。

**步骤 2 - 恢复 SSE 级别**:
```cpp
#undef SK_CPU_SSE_LEVEL
#define SK_CPU_SSE_LEVEL SK_OLD_CPU_SSE_LEVEL
#undef SK_OLD_CPU_SSE_LEVEL
```
将 `SK_CPU_SSE_LEVEL` 从 `SkOpts_SetTarget.h` 设置的值恢复为保存在 `SK_OLD_CPU_SSE_LEVEL` 中的原始值，然后清除临时保存宏。

**步骤 3 - 恢复编译器属性**:
```cpp
#if defined(__clang__)
    #pragma clang attribute pop
#elif defined(__GNUC__)
    #pragma GCC pop_options
#endif
```
使用编译器的 pop 机制撤销 `SkOpts_SetTarget.h` 中 push 的目标指令集属性，使后续代码恢复为原始的编译器目标设置。

## 依赖关系

### 直接依赖
- `include/private/base/SkFeatures.h` - CPU 特性检测宏（`SK_OPTS_TARGET_DEFAULT` 等常量定义）

### 配对依赖
- `src/opts/SkOpts_SetTarget.h` - 必须在本文件之前包含，否则会触发编译错误

## 设计模式与设计决策

### Push/Pop 对称设计
本文件与 `SkOpts_SetTarget.h` 的 push 操作严格对称，确保编译环境的修改具有明确的作用域。这遵循了 RAII（资源获取即初始化）的思想，只不过是在预处理器层面实现。

### 编译时错误检测
通过检查 `SK_OLD_CPU_SSE_LEVEL` 是否已定义来验证使用顺序的正确性。如果开发者忘记先包含 `SkOpts_SetTarget.h`，会得到清晰的编译错误信息而非难以调试的运行时问题。

### 无 include guard
与 `SkOpts_SetTarget.h` 一样，有意省略 include guard 以支持在同一编译单元中多次使用。

## 性能考量

- 该文件完全由预处理器指令组成，不产生任何运行时代码，因此没有任何运行时性能开销。
- 编译器的 `pragma push/pop` 操作对编译速度的影响可以忽略不计。

## 相关文件

- `src/opts/SkOpts_SetTarget.h` - 配对使用的编译环境设置文件
- `include/private/base/SkFeatures.h` - CPU 特性检测宏定义
- `src/opts/SkOpts_skx.cpp` - 使用 SetTarget/RestoreTarget 配对的典型编译单元示例
