# DawnErrorChecker

> 源文件:
> - `src/gpu/graphite/dawn/DawnErrorChecker.h`
> - `src/gpu/graphite/dawn/DawnErrorChecker.cpp`

## 概述

`DawnErrorChecker` 是 Skia Graphite 渲染引擎 Dawn (WebGPU) 后端的错误检测工具类。它采用 RAII 模式，在构造时自动推入三种错误作用域（Validation、OutOfMemory、Internal），在析构或显式调用 `popErrorScopes()` 时弹出并检查这些作用域中捕获的错误。该类用于在关键 GPU 操作（如管线创建、资源分配）周围进行同步错误检测。

## 架构位置

```
Graphite Dawn 后端
  └── DawnErrorChecker (RAII 错误检测工具)
        ├── 构造：PushErrorScope x 3 (Validation, OutOfMemory, Internal)
        └── 析构/popErrorScopes：PopErrorScope x 3 + 等待回调
```

在 `DawnResourceProvider` 和 `DawnGraphicsPipeline` 中作为局部变量使用，包裹可能产生错误的 Dawn API 调用。

## 主要类与结构体

### `DawnErrorType`（枚举位掩码）
```cpp
enum class DawnErrorType : uint32_t {
    kNoError     = 0b00000000,
    kValidation  = 0b00000001,
    kOutOfMemory = 0b00000010,
    kInternal    = 0b00000100,
};
```
- 可通过位运算组合，支持 `SK_MAKE_BITMASK_OPS` 提供的运算符。
- 用于表示一次检查中可能同时出现的多种错误类型。

### `DawnErrorChecker`
- 构造时推入三个错误作用域。
- `fArmed` 布尔标志指示是否还有未弹出的错误作用域。
- 析构时自动弹出并断言无错误。

## 公共 API 函数

- **`DawnErrorChecker(const DawnSharedContext*)`**：构造函数，调用 `device.PushErrorScope()` 推入 Validation、OutOfMemory、Internal 三个错误作用域。
- **`~DawnErrorChecker()`**：析构函数，调用 `popErrorScopes()` 并断言无错误被捕获。
- **`popErrorScopes() -> SkEnumBitMask<DawnErrorType>`**：弹出所有错误作用域，同步等待回调结果。返回捕获到的错误类型的位掩码组合。多次调用时，第二次及之后直接返回 `kNoError`。

## 内部实现细节

### 错误作用域机制
Dawn 的错误作用域是一个栈式结构：
1. **推入顺序**：Validation -> OutOfMemory -> Internal（最后推入的最先弹出）。
2. **弹出顺序**：Internal -> OutOfMemory -> Validation（LIFO）。
3. 每个作用域只捕获对应类型的错误。

### Emscripten 实现
- 使用 `DawnAsyncWait` 进行忙等待（`busyWait()`）。
- 使用旧式 C 回调 API（`WGPUErrorType` + `void* userData`）。
- 每次弹出一个作用域后等待完成，然后 `reset()` 重置等待状态。
- 通过 `ErrorState` 结构体维护错误状态和作用域索引。

### 原生 Dawn 实现
- 使用 `wgpu::Future` 和 `instance.WaitAny()` 进行同步等待。
- 使用 C++ 回调 API（`wgpu::PopErrorScopeStatus` + `wgpu::ErrorType`）。
- 三个 `PopErrorScope` 调用返回各自的 Future，然后依次等待完成。
- 使用无限超时确保等待成功。

### 武装/解除机制
`fArmed` 标志确保错误作用域只被弹出一次：
- 构造时 `fArmed = true`。
- `popErrorScopes()` 执行后 `fArmed = false`。
- 析构时再次调用 `popErrorScopes()` 时因 `fArmed = false` 直接返回。

## 依赖关系

- **Dawn 后端类**: `DawnSharedContext`、`DawnAsyncWait`、`DawnCaps`
- **Skia 基础**: `SkEnumBitMask`、`SkAssert`
- **WebGPU API**: `wgpu::Device`（PushErrorScope/PopErrorScope）、`wgpu::Instance`（WaitAny）

## 设计模式与设计决策

1. **RAII 模式**：构造推入作用域，析构弹出并验证，确保错误作用域不会泄漏。
2. **位掩码错误类型**：允许一次检查中报告多种错误，调用者可灵活判断。
3. **可选使用**：调用处通过 `DawnCaps::allowScopedErrorChecks()` 判断是否启用，使用 `std::optional<DawnErrorChecker>` 包装。
4. **平台适配**：Emscripten 和原生 Dawn 使用不同的异步等待机制。

## 性能考量

- **同步等待**：`popErrorScopes()` 会阻塞等待所有回调完成，因此仅在需要立即确认错误的场景使用。
- **条件启用**：通过 `allowScopedErrorChecks()` 控制是否在特定环境下启用错误检查，避免在生产环境中的额外开销。
- **栈式作用域**：Dawn 的错误作用域为栈结构，推入和弹出开销极小。

## 相关文件

- `src/gpu/graphite/dawn/DawnSharedContext.h` - 提供 device 和 instance 访问
- `src/gpu/graphite/dawn/DawnAsyncWait.h` - Emscripten 异步等待辅助类
- `src/gpu/graphite/dawn/DawnCaps.h` - `allowScopedErrorChecks()` 能力查询
- `src/gpu/graphite/dawn/DawnResourceProvider.cpp` - 使用场景之一
- `src/gpu/graphite/dawn/DawnGraphicsPipeline.cpp` - 使用场景之一
