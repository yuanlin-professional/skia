# SkCGGeometry — Core Graphics 几何辅助函数

> 源文件: `src/utils/mac/SkCGGeometry.h`

## 概述

`SkCGGeometry.h` 提供了 Apple Core Graphics `CGRect` 类型的内联辅助函数，作为系统 `CGGeometry.h` 中对应函数（如 `CGRectGetMinX`、`CGRectIsEmpty`）的高性能替代。

Apple 系统提供的 `CGRectGetMinX` 等函数是真正的函数调用，涉及调用开销和 `CGRect` 结构体的栈拷贝。这些内联版本直接访问结构体成员，消除了函数调用开销，在频繁调用的场景（如字形测量、布局计算）中可显著提升性能。

该文件仅在 macOS 或 iOS 平台上编译。

## 架构位置

```
Skia
└── src/utils/mac/
    ├── SkCGGeometry.h          // 本文件
    ├── SkCGBase.h              // CG 基础定义
    ├── SkUniqueCFRef.h         // CF 对象智能指针
    └── SkCreateCGImageRef.cpp  // CG 图像互操作
```

该模块被 Skia 在 Apple 平台上与 Core Graphics/Core Text 交互的代码使用，特别是字体渲染和度量模块。

## 主要类与结构体

本文件不定义任何类或结构体，仅提供 `static inline` 辅助函数。

## 公共 API 函数

### `bool SkCGRectIsEmpty(const CGRect& rect)`

- **功能**: 判断 `CGRect` 是否为空（宽度或高度小于等于 0）
- **对应系统函数**: `CGRectIsEmpty`

### `CGFloat SkCGRectGetMinX(const CGRect& rect)`

- **功能**: 获取矩形左边界 X 坐标
- **对应系统函数**: `CGRectGetMinX`

### `CGFloat SkCGRectGetMaxX(const CGRect& rect)`

- **功能**: 获取矩形右边界 X 坐标
- **对应系统函数**: `CGRectGetMaxX`

### `CGFloat SkCGRectGetMinY(const CGRect& rect)`

- **功能**: 获取矩形下边界 Y 坐标
- **对应系统函数**: `CGRectGetMinY`

### `CGFloat SkCGRectGetMaxY(const CGRect& rect)`

- **功能**: 获取矩形上边界 Y 坐标
- **对应系统函数**: `CGRectGetMaxY`

### `CGFloat SkCGRectGetWidth(const CGRect& rect)`

- **功能**: 获取矩形宽度
- **对应系统函数**: `CGRectGetWidth`

## 内部实现细节

所有函数都是简单的内联成员访问：

- `SkCGRectGetMinX` 直接返回 `rect.origin.x`
- `SkCGRectGetMaxX` 返回 `rect.origin.x + rect.size.width`
- `SkCGRectIsEmpty` 检查 `width <= 0 || height <= 0`

注意：与系统的 `CGRectIsEmpty` 不同，这里的实现没有处理 `CGRectNull`（系统版本对 null rect 返回 true），但对于 Skia 的使用场景这不是问题。

### 平台差异

macOS 和 iOS 引入不同的头文件来获取 `CGRect` 类型定义：
- macOS: `<ApplicationServices/ApplicationServices.h>`
- iOS: `<CoreGraphics/CoreGraphics.h>`

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `include/core/SkTypes.h` | 平台编译宏 |
| `ApplicationServices.h` (macOS) | `CGRect`、`CGFloat` 类型定义 |
| `CoreGraphics.h` (iOS) | `CGRect`、`CGFloat` 类型定义 |

## 设计模式与设计决策

1. **内联替代**: 用 `static inline` 函数替代系统函数调用，消除不必要的调用开销
2. **const 引用参数**: 使用 `const CGRect&` 而非值传递，避免结构体拷贝
3. **条件编译**: 使用 `SK_BUILD_FOR_MAC` 和 `SK_BUILD_FOR_IOS` 分别引入正确的平台头文件
4. **命名约定**: 使用 `Sk` 前缀 + 原函数名的命名方式，便于识别和替换

## 性能考量

- 所有函数均为 `static inline`，编译器会将其内联展开
- 消除了系统函数调用的函数调用开销（参数压栈、跳转、返回）
- 避免了 `CGRect` 结构体的值传递拷贝（系统函数接受值传递）
- 在字体度量等高频调用场景中，性能提升可能是可观的

## 相关文件

- `src/utils/mac/SkCGBase.h` — CG 基础定义
- `src/ports/SkFontHost_mac_ct.cpp` — Core Text 字体渲染（主要使用者）
- `src/ports/SkScalerContext_mac_ct.cpp` — Core Text 字形缩放
- `src/utils/mac/SkCreateCGImageRef.cpp` — CG 图像互操作
