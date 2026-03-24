# RuntimeBlendUtils - 运行时混合模式工具

> 源文件:
> - [tools/RuntimeBlendUtils.h](../../tools/RuntimeBlendUtils.h)
> - [tools/RuntimeBlendUtils.cpp](../../tools/RuntimeBlendUtils.cpp)

## 概述

RuntimeBlendUtils 提供了一个工具函数，用于将标准的 SkBlendMode 转换为基于 SkRuntimeEffect 的等价混合器（Blender）。该工具确保所有混合操作都通过 SkSL 着色器执行，而非使用专用/固定功能硬件路径，主要用于验证 Runtime Blend 管线的正确性。

## 架构位置

位于 `tools/` 目录下，属于测试辅助工具。它桥接了 Skia 的固定混合模式（SkBlendMode）与运行时效果系统（SkRuntimeEffect），用于 GM 测试和回归验证。

## 主要类与结构体

本模块不包含类定义，仅提供一个全局函数。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `GetRuntimeBlendForBlendMode(SkBlendMode)` | 返回等价于指定混合模式的 Runtime Effect 混合器 |

## 内部实现细节

- 使用 `SkRuntimeEffect::MakeForBlender` 编译一段 SkSL 混合着色器。
- SkSL 代码通过 `uniform blender b` 接收子混合器，然后在 `main` 中调用 `b.eval(src, dst)` 执行实际混合。
- 将传入的 `SkBlendMode` 通过 `SkBlender::Mode()` 包装后，设置为子混合器 `"b"` 的实现。
- SkRuntimeEffect 编译结果使用 `static` 变量缓存，避免重复编译。

## 依赖关系

- **Skia 核心**：SkBlendMode、SkBlender、SkRefCnt
- **运行时效果**：SkRuntimeEffect、SkRuntimeBlendBuilder

## 设计模式与设计决策

- **委托模式**：Runtime Blend 将实际混合委托给通过 uniform 传入的子混合器，实现了固定模式到运行时路径的透明转换。
- **静态缓存**：编译结果只执行一次，所有调用共享同一个 SkRuntimeEffect 实例。
- **测试专用设计**：函数的存在纯粹是为了验证 Runtime Blend 管线与固定功能管线的一致性。

## 性能考量

- SkSL 编译使用静态缓存，仅首次调用有编译开销。
- 相比直接使用固定功能混合模式，Runtime Blend 路径可能较慢，但这是测试验证所需的代价。

## 相关文件

- `include/effects/SkRuntimeEffect.h` - 运行时效果 API
- `include/core/SkBlendMode.h` - 混合模式枚举
- `gm/runtimeblend.cpp` - 使用此工具的 GM 测试
