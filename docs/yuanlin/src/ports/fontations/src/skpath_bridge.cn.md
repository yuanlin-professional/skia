# Fontations SkPath Bridge - C++ 侧纯虚接口定义

> 源文件: `src/ports/fontations/src/skpath_bridge.h`

## 概述

`skpath_bridge.h` 是 Skia Fontations 字体后端的 C++ 头文件，定义了两个纯虚接口类：`AxisWrapper` 和 `ColorPainterWrapper`。这些接口通过 CXX bridge 暴露给 Rust 侧，使得 Rust 代码能够回调 C++ 侧的实现，完成变体轴参数填充和 COLR 颜色字形绘制等操作。

该文件是 Rust-C++ 双向通信的关键组成部分。Rust 侧通过 CXX 生成的绑定持有这些 C++ 对象的 `Pin` 引用，并调用其虚函数将数据传递回 C++ 侧。

## 架构位置

```
Skia C++ 实现层
├── AxisWrapper 具体实现 (在 SkTypeface_fontations.cpp 中)
├── ColorPainterWrapper 具体实现 (在 SkScalerContext_fontations.cpp 中)
│
skpath_bridge.h (本文件 - 纯虚接口定义)
│
└── CXX bridge (ffi.rs 中的 unsafe extern "C++" 块)
    └── Rust 侧通过 Pin<&mut T> 调用
```

该文件位于 Fontations 桥接层中，是 C++ 侧向 Rust 侧提供回调能力的接口契约。

## 主要类与结构体

### `AxisWrapper`
```cpp
class AxisWrapper {
public:
    virtual ~AxisWrapper() = default;
    virtual bool populate_axis(
        size_t i, uint32_t axisTag,
        float min, float def, float max, bool hidden) = 0;
    virtual size_t size() const = 0;
};
```
- 用于将变体轴参数写入 Skia 的 `SkFontParameters::Variation::Axis` 数组
- 之所以使用虚接口而非直接映射结构体，是因为 `SkFontParameters::Variation::Axis` 的 `hidden` 标志为私有成员，无法通过 CXX 直接映射共享结构体来设置
- `populate_axis`: 填充第 `i` 个轴的标签、最小值、默认值、最大值和是否隐藏
- `size`: 返回调用方分配的轴数组大小

### `ColorPainterWrapper`
```cpp
class ColorPainterWrapper {
public:
    virtual ~ColorPainterWrapper() = default;
    // ... 虚函数列表
};
```
- 实现 skrifa `ColorPainter` trait 对应的 C++ 回调接口
- 用于接收 COLR 表（v0 和 v1）字形的绘制命令

**变换与裁剪操作:**
- `is_bounds_mode()` - 查询是否处于边界计算模式（用于优化 COLR 渲染）
- `push_transform` / `pop_transform` - 仿射变换栈管理
- `push_clip_glyph` / `push_clip_rectangle` / `pop_clip` - 裁剪区域栈管理

**基础填充操作:**
- `fill_solid` - 纯色填充
- `fill_linear` - 线性渐变填充
- `fill_radial` - 径向渐变填充
- `fill_sweep` - 扫描渐变填充

**优化的字形填充操作:**
- `fill_glyph_solid` - 字形纯色填充（合并裁剪+填充）
- `fill_glyph_linear` - 字形线性渐变填充
- `fill_glyph_radial` - 字形径向渐变填充
- `fill_glyph_sweep` - 字形扫描渐变填充

**图层操作:**
- `push_layer` - 推入新图层（带 COLRv1 合成模式）
- `pop_layer` - 弹出图层

### 前向声明
```cpp
struct ColorStop;
struct BridgeColorStops;
struct Transform;
struct FillLinearParams;
struct FillRadialParams;
struct FillSweepParams;
```
这些结构体在 CXX bridge 生成的代码中定义，此处仅作前向声明以供接口方法签名使用。

## 公共 API 函数

该文件仅定义纯虚接口，不包含函数实现。具体实现位于 Skia 的 C++ 代码中（如 `SkTypeface_fontations.cpp` 和相关文件）。

## 内部实现细节

### 命名空间
所有类型定义在 `fontations_ffi` 命名空间内，与 CXX bridge 中指定的命名空间一致。

### Include Guard
使用传统的 `#ifndef`/`#define`/`#endif` 包含保护，宏名为 `SkPathBridge_DEFINED`。

### 仅依赖 C 标准库头文件
仅包含 `<cstddef>` 和 `<cstdint>`，不依赖任何 Skia 头文件，保持接口的最小化和独立性。

### 虚析构函数
两个类都声明了 `virtual ~ClassName() = default`，确保通过基类指针删除派生类对象时行为正确。

## 依赖关系

- **标准库**: `<cstddef>` (size_t), `<cstdint>` (uint8_t, uint16_t, uint32_t)
- **CXX 生成的类型**: `ColorStop`, `BridgeColorStops`, `Transform`, `FillLinearParams`, `FillRadialParams`, `FillSweepParams`（通过前向声明引用）

## 设计模式与设计决策

1. **纯虚接口模式（抽象基类）**: 使用 C++ 纯虚类作为回调接口，允许 Skia C++ 侧提供具体实现，Rust 侧通过 CXX 调用虚函数表
2. **接口隔离**: `AxisWrapper` 和 `ColorPainterWrapper` 职责清晰分离，前者处理变体轴参数，后者处理颜色字形绘制
3. **最小依赖**: 头文件仅依赖 C 标准库，不引入 Skia 头文件，降低了编译依赖链的复杂度
4. **前向声明**: CXX 生成的类型仅通过前向声明引用，避免循环依赖
5. **优化的 fill_glyph_* 方法**: 提供带字形 ID 的组合绘制操作，使 C++ 实现可以将裁剪和填充优化为单次 Canvas 操作

## 性能考量

- 虚函数调用引入间接寻址开销，但每个字形的 COLR 绘制操作相对重量级，虚函数开销可忽略
- `fill_glyph_*` 系列方法通过合并裁剪和填充减少了回调次数和 Canvas 状态切换
- `is_bounds_mode()` 允许 Rust 侧在边界计算模式下跳过不必要的绘制操作

## 相关文件

- `src/ports/fontations/src/ffi.rs` - CXX bridge 定义，声明如何使用这些 C++ 接口
- `src/ports/fontations/src/colr.rs` - Rust 侧 COLR 实现，通过 `ColorPainterWrapper` 回调 C++
- `src/ports/fontations/src/base.rs` - Rust 侧基础实现，通过 `AxisWrapper` 回调 C++
- `src/ports/SkTypeface_fontations.cpp` - `AxisWrapper` 的具体 C++ 实现
- `src/ports/SkScalerContext_fontations.cpp` - `ColorPainterWrapper` 的具体 C++ 实现
