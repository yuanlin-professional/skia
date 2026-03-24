# SkSVGRectPriv

> 源文件: [modules/svg/src/SkSVGRectPriv.h](../../../../modules/svg/src/SkSVGRectPriv.h)

## 概述

`SkSVGRectPriv.h` 是一个内部私有头文件，声明了一个工具函数 `ResolveOptionalRadii`，用于解析 SVG 矩形元素（`<rect>`）中可选的圆角半径属性 `rx` 和 `ry`。该函数处理 SVG 规范中关于 `rx`/`ry` 缺省值的互推规则：当仅指定一个半径时，另一个半径自动取相同的值；当两个都未指定时，矩形没有圆角。

## 架构位置

该文件位于 `modules/svg/src/` 目录下（而非 `include/`），表明它是模块内部的私有实现头文件，不对外暴露。它服务于 SVG 矩形相关节点（如 `SkSVGRect`）的圆角半径解析。

```
modules/svg/src/
  └── SkSVGRectPriv.h  ← 私有工具头文件
        └── 被 SkSVGRect.cpp 等引用
              └── 处理 <rect> 元素的 rx/ry 属性解析
```

在 SVG 规范中，`<rect>` 元素的 `rx` 和 `ry` 属性遵循以下规则：
1. 若 `rx` 和 `ry` 都指定，则使用各自的值
2. 若仅指定 `rx`，则 `ry` 取 `rx` 的值
3. 若仅指定 `ry`，则 `rx` 取 `ry` 的值
4. 若都未指定，则不生成圆角（两者为 0）

## 主要类与结构体

本文件不定义类或结构体，仅声明一个自由函数。

### 前向声明
- `SkSVGLength` - SVG 长度类型，支持多种单位（px、em、%、cm 等）
- `SkSVGLengthContext` - SVG 长度解析上下文，提供视口尺寸和 DPI 等信息用于将相对单位转换为绝对像素值

### 头文件保护
使用传统的 `#ifndef`/`#define`/`#endif` 头文件保护宏 `SkSVGRectPriv_DEFINED`，防止重复包含。

## 公共 API 函数

### `ResolveOptionalRadii`
```cpp
std::tuple<float, float> ResolveOptionalRadii(
    const std::optional<SkSVGLength>& rx,
    const std::optional<SkSVGLength>& ry,
    const SkSVGLengthContext&);
```
- 接受可选的 `rx` 和 `ry` 值以及长度上下文
- 返回解析后的浮点数元组 `(rx_resolved, ry_resolved)`
- 处理 SVG 规范中的缺省逻辑：若仅指定 `rx` 则 `ry` 取 `rx` 的值，反之亦然
- 使用 `SkSVGLengthContext` 将可能包含百分比或其他单位的长度值转换为绝对像素值

## 内部实现细节

- 使用 `std::optional<SkSVGLength>` 区分「未指定」和「指定为 0」两种情况。这一区分至关重要：`rx="0"` 表示显式设置圆角半径为 0（无圆角），而未指定 `rx` 则需要根据 `ry` 的值来推导。
- 使用 `std::tuple` 返回两个浮点值，允许调用方通过 C++17 结构化绑定接收结果：`auto [rx, ry] = ResolveOptionalRadii(...);`
- 需要 `SkSVGLengthContext` 将 `SkSVGLength`（可能包含百分比或其他 CSS 单位）解析为绝对像素值。例如，`rx="50%"` 需要知道视口宽度才能计算实际像素值。
- 该函数作为自由函数（非类成员）声明，保持了与面向对象设计的松耦合。

## 依赖关系

- **Skia 核心**: `SkTypes.h`（基础类型和平台抽象）
- **标准库**: `<optional>`（可选值语义）、`<tuple>`（多返回值）
- **SVG 模块**: `SkSVGLength`（前向声明，实际定义在 `SkSVGTypes.h`）、`SkSVGLengthContext`（前向声明，实际定义在 `SkSVGRenderContext.h`）

## 设计模式与设计决策

1. **私有头文件模式**: 放置在 `src/` 而非 `include/` 目录中，限制了可见范围，避免模块外部代码依赖内部实现细节。这是 Skia 项目中管理内部 API 的标准做法。

2. **值语义返回**: 使用 `std::tuple` 返回两个浮点数，避免输出参数，符合现代 C++ 的值语义设计风格。调用方可以直接通过结构化绑定解包结果。

3. **Optional 语义**: 使用 `std::optional` 精确表达 SVG 中属性「未指定」的语义，这与 SVG 规范中 `rx`/`ry` 的互推规则直接对应。相比使用特殊值（如 -1）表示未设置，`std::optional` 更加类型安全和自文档化。

4. **前向声明最小化依赖**: 仅前向声明 `SkSVGLength` 和 `SkSVGLengthContext`，不包含它们的完整头文件，减少了编译依赖传播。

## 性能考量

- 该函数仅在 SVG 解析/渲染阶段使用，不在每帧的渲染热路径中调用（除非矩形需要重新解析），无性能敏感性。
- 函数本身仅涉及简单的条件判断和长度单位转换，计算开销极小。
- `std::optional` 的开销在现代编译器优化下可以忽略不计。

## 相关文件

- `modules/svg/src/SkSVGRect.cpp` - SVG 矩形元素实现（调用此函数解析圆角半径）
- `modules/svg/include/SkSVGTypes.h` - `SkSVGLength` 类型定义
- `modules/svg/include/SkSVGRenderContext.h` - `SkSVGLengthContext` 类型定义
- `modules/svg/include/SkSVGRect.h` - SVG 矩形元素声明
