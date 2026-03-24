# GrNativeRect

> 源文件
> - src/gpu/ganesh/GrNativeRect.h

## 概述

`GrNativeRect` 是 Ganesh GPU 后端中用于处理不同表面原点（top-down vs bottom-up）的轻量级矩形结构体。它主要用于将 Skia 的坐标系统（通常是 top-down）转换为 GPU 原生坐标系统（可能是 bottom-up，如 OpenGL）。该结构体提供了便利的方法来创建相对于表面原点的矩形，以及在不同坐标系统之间进行转换，是处理跨平台图形 API 坐标差异的关键工具。

## 架构位置

`GrNativeRect` 位于 Ganesh 渲染管线的坐标转换层，处于高级绘图命令和底层 GPU API 之间：

```
Skia 坐标系统（Top-Down）
    │
    └── GrNativeRect（坐标转换）
        │
        ├── OpenGL (Bottom-Up)
        ├── Vulkan (Top-Down)
        ├── Metal (Top-Down)
        └── Direct3D (Top-Down)
```

它在设置视口、裁剪矩形和渲染区域时被广泛使用，确保坐标系统的正确转换。

## 主要类与结构体

### GrNativeRect

表示 GPU 原生坐标系统中的矩形。

**继承关系**
- 无继承关系（纯数据结构体）

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fX` | `int` | 矩形左边缘的 x 坐标 |
| `fY` | `int` | 矩形顶部/底部边缘的 y 坐标（取决于原点） |
| `fWidth` | `int` | 矩形宽度 |
| `fHeight` | `int` | 矩形高度 |

注意：成员变量使用固定的内存布局，可以安全地转换为 `int` 数组。

## 公共 API 函数

### 静态工厂方法

| 函数签名 | 说明 |
|----------|------|
| `static GrNativeRect MakeRelativeTo(GrSurfaceOrigin origin, int rtHeight, SkIRect devRect)` | 创建相对于指定原点的 GrNativeRect |
| `static SkIRect MakeIRectRelativeTo(GrSurfaceOrigin origin, int rtHeight, SkIRect devRect)` | 创建相对于指定原点的 SkIRect |

### 数组转换

| 函数签名 | 说明 |
|----------|------|
| `const int* asInts() const` | 将矩形作为 const int 数组访问 |
| `int* asInts()` | 将矩形作为 int 数组访问 |

### 类型转换

| 函数签名 | 说明 |
|----------|------|
| `SkIRect asSkIRect() const` | 转换为 SkIRect，使用 XYWH 格式 |

### 坐标设置

| 函数签名 | 说明 |
|----------|------|
| `void setRelativeTo(GrSurfaceOrigin org, int rtHeight, const SkIRect& devRect)` | 根据表面原点设置矩形，从 SkIRect 转换 |
| `void setRelativeTo(GrSurfaceOrigin origin, int surfaceHeight, int leftOffset, int topOffset, int width, int height)` | 根据表面原点设置矩形，从独立参数转换 |

### 辅助方法

| 函数签名 | 说明 |
|----------|------|
| `bool contains(int width, int height) const` | 检查矩形是否包含指定尺寸 |
| `void invalidate()` | 使矩形无效（所有值设为 -1） |
| `bool isInvalid() const` | 检查矩形是否无效 |

### 比较操作符

| 函数签名 | 说明 |
|----------|------|
| `bool operator==(const GrNativeRect& that) const` | 相等比较 |
| `bool operator!=(const GrNativeRect& that) const` | 不等比较 |

## 内部实现细节

### 坐标系统转换逻辑

核心转换逻辑在 `setRelativeTo` 方法中：

```cpp
void setRelativeTo(GrSurfaceOrigin origin, int surfaceHeight,
                   int leftOffset, int topOffset,
                   int width, int height) {
    fX = leftOffset;
    fWidth = width;
    if (kBottomLeft_GrSurfaceOrigin == origin) {
        // 底部原点：需要翻转 Y 坐标
        fY = surfaceHeight - topOffset - height;
    } else {
        // 顶部原点：保持 Y 坐标不变
        fY = topOffset;
    }
    fHeight = height;

    SkASSERT(fWidth >= 0);
    SkASSERT(fHeight >= 0);
}
```

关键转换：
- **X 坐标和宽度**：无论原点如何都保持不变
- **Y 坐标（底部原点）**：`y = surfaceHeight - topOffset - height`
- **Y 坐标（顶部原点）**：`y = topOffset`
- **高度**：无论原点如何都保持不变

### 底部原点的 Y 坐标计算

对于底部原点（如 OpenGL）：

```
Skia Top-Down:
0 ──────────────
│
│   topOffset
│   ┌─────┐
│   │rect │ height
│   └─────┘
│
rtHeight

OpenGL Bottom-Up:
rtHeight
│   ┌─────┐
│   │rect │ height
│   └─────┘
│   (rtHeight - topOffset - height)
│
0 ──────────────
```

转换公式：`y_bottomUp = rtHeight - y_topDown - height`

### 内存布局保证

结构体使用 `static_assert` 确保成员变量的内存布局：

```cpp
const int* asInts() const {
    return &fX;

    static_assert(0 == offsetof(GrNativeRect, fX));
    static_assert(4 == offsetof(GrNativeRect, fY));
    static_assert(8 == offsetof(GrNativeRect, fWidth));
    static_assert(12 == offsetof(GrNativeRect, fHeight));
    static_assert(16 == sizeof(GrNativeRect));  // For an array of GrNativeRect.
}
```

这保证：
- 成员按声明顺序连续存储
- 可以安全地作为 `int[4]` 数组访问
- 适用于需要数组表示的 GPU API（如 `glScissor`）

### 包含测试

`contains` 方法检查矩形是否覆盖整个表面：

```cpp
bool contains(int width, int height) const {
    return fX <= 0 &&
           fY <= 0 &&
           fX + fWidth >= width &&
           fY + fHeight >= height;
}
```

这是检查是否可以跳过裁剪的优化方法。

### 无效状态管理

提供特殊的无效状态表示：

```cpp
void invalidate() { fX = fWidth = fY = fHeight = -1; }
bool isInvalid() const {
    return fX == -1 && fWidth == -1 && fY == -1 && fHeight == -1;
}
```

用于表示未初始化或已释放的矩形。

### 相等性比较

使用 `memcmp` 实现快速比较：

```cpp
bool operator==(const GrNativeRect& that) const {
    return 0 == memcmp(this, &that, sizeof(GrNativeRect));
}
```

这利用了紧凑的内存布局，避免逐个比较成员变量。

## 依赖关系

### 依赖的模块

| 模块名 | 用途 |
|--------|------|
| `SkRect.h` | Skia 矩形类型 |
| `GrTypes.h` | GrSurfaceOrigin 枚举 |
| `SkAssert.h` | 断言宏 |
| `<cstddef>` | offsetof 宏 |
| `<cstring>` | memcmp 函数 |

### 被依赖的模块

| 模块名 | 使用方式 |
|--------|----------|
| 视口设置 | 将 Skia 矩形转换为 GPU 视口 |
| 裁剪设置 | 设置裁剪矩形 |
| 渲染目标操作 | 指定渲染区域 |
| 后端实现 | OpenGL/Vulkan/Metal 等各种后端 |

## 设计模式与设计决策

### 值语义（Value Semantics）

`GrNativeRect` 是一个简单的值类型：
- 无虚函数
- 无动态分配
- 可按值传递和复制
- POD（Plain Old Data）类型

这使其非常轻量，适合频繁创建和传递。

### 不可变性的部分实现

虽然成员是公共的，但设计鼓励通过 `setRelativeTo` 设置，而不是直接修改：
- 提供静态工厂方法（`MakeRelativeTo`）
- 封装转换逻辑
- 确保坐标转换的正确性

### 策略模式的变体

`setRelativeTo` 根据 `GrSurfaceOrigin` 枚举选择不同的转换策略：
- `kTopLeft_GrSurfaceOrigin`：直接复制坐标
- `kBottomLeft_GrSurfaceOrigin`：翻转 Y 坐标

这避免了使用虚函数或函数指针的开销。

### 类型安全的数组访问

提供 `asInts()` 方法而不是直接访问成员：
- 明确意图（作为数组使用）
- 编译时检查内存布局（`static_assert`）
- 类型安全（返回 `const int*`）

### 防御性编程

多处使用断言确保正确性：
- 检查宽度和高度非负
- 验证内存布局
- 检查偏移量

### 命名约定

使用 "Native" 前缀强调：
- 这是 GPU 原生坐标系统
- 可能与 Skia 坐标系统不同
- 需要显式转换

### 无依赖性设计

除了基本类型和 Skia 核心类型，不依赖其他复杂模块：
- 易于理解和测试
- 编译速度快
- 减少耦合

## 性能考量

### 轻量级结构

- **大小**：仅 16 字节（4 个 int）
- **对齐**：自然对齐，适合栈分配
- **无堆分配**：完全在栈上操作

### 内联友好

所有方法都在头文件中定义，编译器可以内联：
- 消除函数调用开销
- 允许进一步优化（如常量传播）
- 特别有利于 `setRelativeTo` 这样的简单方法

### 快速比较

使用 `memcmp` 进行相等性比较：
- 单次内存比较操作
- 利用编译器优化（可能优化为单个指令）
- 避免分支

### 直接数组访问

`asInts()` 允许直接传递给 GPU API：

```cpp
GrNativeRect rect = ...;
glScissor(rect.asInts()[0], rect.asInts()[1],
          rect.asInts()[2], rect.asInts()[3]);
// 或更简洁：
glScissorv(rect.asInts());
```

避免临时数组分配和复制。

### 编译时检查

使用 `static_assert` 在编译时验证内存布局：
- 零运行时开销
- 早期捕获潜在问题
- 确保跨平台一致性

### 分支预测

坐标转换中的分支（`if (kBottomLeft_GrSurfaceOrigin == origin)`）通常是可预测的：
- 在单次渲染中，原点通常不变
- 现代 CPU 的分支预测器可以有效处理
- 相比虚函数调用仍然更快

### 无虚函数开销

作为纯数据结构体：
- 无虚函数表指针
- 无虚函数调用开销
- 适合放入紧凑的数组

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/core/SkRect.h` | 依赖 | Skia 矩形类型 |
| `include/gpu/ganesh/GrTypes.h` | 依赖 | GrSurfaceOrigin 枚举定义 |
| `src/gpu/ganesh/gl/GrGLGpu.h/cpp` | 使用者 | OpenGL 后端使用（底部原点） |
| `src/gpu/ganesh/vk/GrVkGpu.h/cpp` | 使用者 | Vulkan 后端使用（顶部原点） |
| `src/gpu/ganesh/mtl/GrMtlGpu.h/mm` | 使用者 | Metal 后端使用（顶部原点） |
| `src/gpu/ganesh/d3d/GrD3DGpu.h/cpp` | 使用者 | Direct3D 后端使用（顶部原点） |
| `src/gpu/ganesh/GrOpsRenderPass.h/cpp` | 使用者 | 渲染通道设置裁剪和视口 |
| `src/gpu/ganesh/GrRenderTarget.h` | 相关 | 渲染目标原点信息 |
| `src/gpu/ganesh/GrSurface.h` | 相关 | 表面原点定义 |
