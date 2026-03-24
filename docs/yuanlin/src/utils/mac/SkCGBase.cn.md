# SkCGBase — Skia 与 Core Graphics 基础类型转换

> 源文件: `src/utils/mac/SkCGBase.h`

## 概述

`SkCGBase.h` 提供了 Skia 标量类型（`SkScalar`）与 Apple Core Graphics 浮点类型（`CGFloat`）之间的转换函数。

这些转换之所以需要，是因为 `CGFloat` 在不同平台上的实际类型不同：在 64 位系统上 `CGFloat` 是 `double`，在 32 位系统上是 `float`。而 Skia 的 `SkScalar` 始终是 `float`。因此在 64 位平台上，两者之间的转换涉及精度变化，需要显式的类型转换来确保正确性并避免编译器警告。

该文件仅在 macOS 或 iOS 平台上编译。

## 架构位置

```
Skia
└── src/utils/mac/
    ├── SkCGBase.h              // 本文件：基础类型转换
    ├── SkCGGeometry.h          // CGRect 辅助函数
    ├── SkUniqueCFRef.h         // CF 对象智能指针
    └── SkCreateCGImageRef.cpp  // CG 图像互操作
```

该模块位于 Skia 的 Apple 平台工具层最底层，被所有涉及 Skia/CG 类型交互的模块依赖。

## 主要类与结构体

本文件不定义任何类或结构体，仅提供 `static inline` 转换函数。

## 公共 API 函数

### `CGFloat SkScalarToCGFloat(SkScalar scalar)`

- **功能**: 将 `SkScalar` (`float`) 转换为 `CGFloat`
- **行为**: 在 64 位平台上调用 `SkScalarToDouble`（`float` -> `double`），在 32 位平台上直接返回原值

### `SkScalar SkScalarFromCGFloat(CGFloat cgFloat)`

- **功能**: 将 `CGFloat` 转换为 `SkScalar` (`float`)
- **行为**: 在 64 位平台上调用 `SkDoubleToScalar`（`double` -> `float`，可能有精度损失），在 32 位平台上直接返回原值

### `float SkFloatFromCGFloat(CGFloat cgFloat)`

- **功能**: 将 `CGFloat` 转换为 `float`
- **行为**: 在 64 位平台上使用 `static_cast<float>`，在 32 位平台上直接返回原值

## 内部实现细节

关键宏 `CGFLOAT_IS_DOUBLE` 是 Apple SDK 提供的预处理器常量：
- 在 64 位平台上（arm64、x86_64）值为 1（`CGFloat` = `double`）
- 在 32 位平台上（armv7、i386）值为 0（`CGFloat` = `float`）

三元运算 `CGFLOAT_IS_DOUBLE ? ... : ...` 在编译时会被编译器常量折叠为只保留一个分支，因此不会有运行时分支开销。

### 平台头文件差异

与 `SkCGGeometry.h` 相同的模式：
- macOS: 引入 `<ApplicationServices/ApplicationServices.h>`
- iOS: 引入 `<CoreGraphics/CoreGraphics.h>`

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `include/private/base/SkFeatures.h` | 特性检测宏 |
| `include/core/SkScalar.h` | `SkScalar` 类型定义和转换函数 |
| `ApplicationServices.h` (macOS) | `CGFloat`、`CGFLOAT_IS_DOUBLE` |
| `CoreGraphics.h` (iOS) | `CGFloat`、`CGFLOAT_IS_DOUBLE` |

## 设计模式与设计决策

1. **编译时分派**: 使用 `CGFLOAT_IS_DOUBLE` 宏在编译时选择正确的转换路径，零运行时开销
2. **显式转换**: 避免隐式的 `double` -> `float` 窄化转换导致的编译器警告
3. **内联函数**: `static inline` 确保调用点直接内联，消除函数调用开销
4. **三个转换方向**: 提供 SkScalar->CGFloat、CGFloat->SkScalar、CGFloat->float 三个方向的转换，覆盖常见需求
5. **条件编译**: 仅在 Apple 平台编译，不污染其他平台的命名空间

## 性能考量

- 所有函数均为 `static inline`，编译器会完全内联
- `CGFLOAT_IS_DOUBLE` 为编译时常量，三元表达式会被常量折叠
- 在 32 位平台上，`CGFloat` 和 `SkScalar` 都是 `float`，转换为空操作
- 在 64 位平台上，`float` <-> `double` 转换对应一条 CPU 指令

## 相关文件

- `include/core/SkScalar.h` — `SkScalar` 类型定义
- `src/utils/mac/SkCGGeometry.h` — CGRect 辅助函数
- `src/ports/SkFontHost_mac_ct.cpp` — 主要使用者（字体度量涉及大量 Skia/CG 类型转换）
- `src/ports/SkScalerContext_mac_ct.cpp` — 字形缩放（同样涉及类型转换）
