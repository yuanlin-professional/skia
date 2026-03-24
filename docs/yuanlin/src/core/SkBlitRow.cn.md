# SkBlitRow

> 源文件: src/core/SkBlitRow.h

## 概述

`SkBlitRow.h` 是 Skia 图形库中用于行级像素位块传输（row blitting）的核心接口头文件。该文件定义了 `SkBlitRow` 类，提供了一组用于高性能行级像素混合操作的函数指针类型和工厂方法。

行级位块传输是 2D 图形渲染中的基础操作之一，该文件通过函数指针和运行时优化框架（`SkOpts`），使得 Skia 能够根据不同的 CPU 特性选择最优的 SIMD 实现，在保持 API 简洁的同时实现高性能的像素混合操作。

## 架构位置

在 Skia 的整体架构中，`SkBlitRow.h` 位于核心渲染层的位块传输子系统：

```
Skia Graphics Library
├── Public API Layer
│   └── SkCanvas, SkPaint
├── Core Rendering Layer
│   ├── SkDraw (绘图协调器)
│   ├── Blitting Subsystem
│   │   ├── SkBlitter (位块传输器基类)
│   │   ├── SkBlitRow (行级混合接口) ← 当前文件
│   │   ├── SkBlitRow_D32.cpp (32 位实现)
│   │   ├── SkBlitMask (遮罩混合)
│   │   └── 其他 Blit 组件
│   └── Optimization Layer (SkOpts)
│       ├── blit_row_color32 (函数指针)
│       └── blit_row_s32a_opaque (函数指针)
└── Base Types
    └── SkColor, SkBitmap, SkPMColor
```

该文件作为行级混合操作的接口层，连接上层绘图 API 和底层优化实现。

## 主要类与结构体

### SkBlitRow 类

该类是一个静态工具类，不包含实例成员，只提供静态方法和类型定义。

#### 继承关系

```
SkBlitRow (无继承关系，纯静态类)
```

#### 关键成员

| 类型 | 名称 | 说明 |
|------|------|------|
| `enum` | `Flags32` | 32 位混合操作的标志位 |
| `typedef` | `Proc32` | 32 位混合函数指针类型 |
| `static method` | `Factory32()` | 根据标志位返回相应的混合函数 |
| `static method` | `Color32()` | 用单一颜色填充/混合一行像素 |

### Flags32 枚举

```cpp
enum Flags32 {
    kGlobalAlpha_Flag32     = 1 << 0,  // 0x01
    kSrcPixelAlpha_Flag32   = 1 << 1   // 0x02
};
```

| 标志位 | 值 | 含义 |
|--------|-----|------|
| `kGlobalAlpha_Flag32` | 0x01 | 使用全局 Alpha 值 |
| `kSrcPixelAlpha_Flag32` | 0x02 | 使用源像素的 Alpha 通道 |

**组合使用**:
- `0`: 不透明源像素，无全局 Alpha
- `1`: 不透明源像素，有全局 Alpha
- `2`: 预乘 Alpha 源像素，无全局 Alpha
- `3`: 预乘 Alpha 源像素，有全局 Alpha

### Proc32 函数指针类型

```cpp
typedef void (*Proc32)(uint32_t dst[], const SkPMColor src[], int count, U8CPU alpha);
```

**参数说明**:
- `dst[]`: 目标像素数组（32 位 ARGB）
- `src[]`: 源像素数组（预乘 Alpha 的 ARGB）
- `count`: 像素数量
- `alpha`: 全局 Alpha 值 (0-255)

## 公共 API 函数

### `SkBlitRow::Factory32()`

```cpp
static Proc32 Factory32(unsigned flags32);
```

**功能**: 根据标志位返回相应的 32 位混合函数指针。

**参数**:
- `flags32`: `Flags32` 枚举值的组合

**返回值**: `Proc32` 函数指针，指向优化的混合实现

**使用示例**:
```cpp
// 获取支持源像素 Alpha 的混合函数
SkBlitRow::Proc32 blitProc = SkBlitRow::Factory32(
    SkBlitRow::kSrcPixelAlpha_Flag32
);

// 使用函数进行混合
blitProc(dstPixels, srcPixels, width, 255);
```

**实现策略**:
根据不同的标志位组合，返回不同的优化实现：
- 不透明混合（无 Alpha）
- 全局 Alpha 混合
- 源像素 Alpha 混合
- 源像素 Alpha + 全局 Alpha 混合

### `SkBlitRow::Color32()`

```cpp
static void Color32(SkPMColor dst[], int count, SkPMColor color);
```

**功能**: 用单一颜色填充或混合到一行目标像素。

**参数**:
- `dst[]`: 目标像素数组
- `count`: 像素数量
- `color`: 源颜色（预乘 Alpha 的 ARGB）

**返回值**: 无 (void)

**行为**:
- 如果 `color` 完全透明（Alpha = 0），不执行任何操作
- 如果 `color` 完全不透明（Alpha = 255），使用优化的 `memset32` 填充
- 其他情况，使用优化的 `blit_row_color32` 进行混合

**使用示例**:
```cpp
SkPMColor red = SkPackARGB32(255, 255, 0, 0);  // 不透明红色
SkBlitRow::Color32(dstPixels, width, red);      // 填充一行红色
```

## 内部实现细节

### SkOpts 命名空间

该文件声明了 `SkOpts` 命名空间中的优化函数指针：

```cpp
namespace SkOpts {
    extern void (*blit_row_color32)(SkPMColor* dst, int count, SkPMColor color);
    extern void (*blit_row_s32a_opaque)(SkPMColor* dst, const SkPMColor* src,
                                        int count, U8CPU alpha);
    void Init_BlitRow();
}
```

#### `blit_row_color32`

**功能**: 使用单一颜色（带 Alpha）混合一行像素

**参数**:
- `dst`: 目标像素数组
- `count`: 像素数量
- `color`: 源颜色（预乘 Alpha）

**实现**: 根据 CPU 特性在运行时初始化，可能使用 SSE2、NEON、AVX2 等 SIMD 指令集优化

#### `blit_row_s32a_opaque`

**功能**: 混合一行预乘 Alpha 的源像素到目标（源像素被视为不透明或应用全局 Alpha）

**参数**:
- `dst`: 目标像素数组
- `src`: 源像素数组（预乘 Alpha）
- `count`: 像素数量
- `alpha`: 全局 Alpha 值

**实现**: 根据 CPU 特性选择 SIMD 优化实现

#### `Init_BlitRow()`

**功能**: 初始化行混合优化函数指针

**行为**:
- 检测 CPU 特性（SSE2、SSSE3、AVX2、NEON 等）
- 将函数指针设置为最优实现
- 通过静态初始化自动调用，用户无需手动调用

## 依赖关系

### 依赖的模块

| 模块 | 路径 | 用途 |
|------|------|------|
| SkBitmap | include/core/SkBitmap.h | 提供位图数据结构（虽然此文件只声明了类型） |
| SkColor | include/core/SkColor.h | 提供 `SkColor`、`SkPMColor`、`U8CPU` 类型 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| SkBlitRow_D32.cpp | 实现 `Factory32()` 和 `Color32()` |
| SkBlitter 子类 | 使用 `Factory32()` 获取优化函数进行像素混合 |
| SkDraw | 高层绘图操作中使用行混合功能 |
| SkOpts 初始化系统 | 调用 `Init_BlitRow()` 初始化优化 |

## 设计模式与设计决策

### 1. 工厂方法模式 (Factory Method Pattern)

`Factory32()` 根据参数创建（返回）不同的函数实现：
- **产品接口**: `Proc32` 函数指针类型
- **具体产品**: 不同标志位组合对应的优化函数
- **工厂方法**: `Factory32(unsigned flags32)`

### 2. 策略模式 (Strategy Pattern)

通过函数指针实现运行时算法选择：
- **策略接口**: `Proc32` 函数签名
- **具体策略**: SSE2 实现、NEON 实现、标量实现等
- **上下文**: `SkOpts` 命名空间和函数指针变量

### 3. 静态工具类模式

`SkBlitRow` 只包含静态方法，无实例状态：
- 简化使用，无需创建对象
- 避免不必要的内存分配
- 清晰表达"工具函数集合"的语义

### 设计决策

**决策1: 为什么使用函数指针而不是虚函数？**
- **零对象开销**: 无需对象实例和虚函数表
- **更低调用开销**: 函数指针调用比虚函数调用快（无需对象指针解引用）
- **C 风格兼容**: 易于与 C 代码互操作
- **简洁性**: 对于简单的函数选择，函数指针更直接

**决策2: 为什么区分 `Factory32()` 和直接的函数指针？**
- `Factory32()`: 编译时已知标志位，可内联优化
- 函数指针（如 `blit_row_color32`）: 运行时选择，更灵活
- 两者结合提供编译时和运行时的双重优化机会

**决策3: 为什么 `Color32()` 特殊处理完全透明和完全不透明？**
```cpp
switch (SkGetPackedA32(color)) {
    case   0: return;                            // 透明，不做任何事
    case 255: SkOpts::memset32(dst, color, count); return;  // 不透明，快速填充
}
```
- **透明优化**: 避免不必要的内存写入
- **不透明优化**: 使用 `memset32`（SIMD 优化）比通用混合快 3-5 倍
- **常见情况**: 这两种情况在实际应用中非常常见

**决策4: 为什么使用位标志而不是枚举所有组合？**
```cpp
enum Flags32 {
    kGlobalAlpha_Flag32     = 1 << 0,
    kSrcPixelAlpha_Flag32   = 1 << 1
};
```
- **灵活性**: 易于添加新标志位
- **紧凑性**: 用一个整数表示多个布尔选项
- **效率**: 位运算检查标志位非常快

## 性能考量

### SIMD 优化收益

针对不同操作的典型加速比（相对于标量实现）：

| 操作 | SSE2 | NEON | AVX2 |
|------|------|------|------|
| `blit_row_color32` | 3-4x | 3-4x | 5-6x |
| `blit_row_s32a_opaque` | 2-3x | 2-3x | 4-5x |
| 预乘 Alpha 混合 | 2-3x | 2-3x | 3-4x |

### 内存带宽

行混合操作通常是内存带宽受限的：
- **读取**: 每像素 4 字节（源）+ 4 字节（目标）= 8 字节
- **写入**: 每像素 4 字节
- **总带宽**: 每像素 12 字节

**1920x1080 屏幕的理论带宽需求**:
- 60 FPS: ~24 GB/s（假设全屏更新）
- 现代 DDR4 内存带宽（~50 GB/s）足够

### 缓存友好性

- **顺序访问**: 行级处理天然具有良好的空间局部性
- **预取**: 现代 CPU 可以有效预取顺序访问的数据
- **写合并**: 顺序写入可以利用 CPU 的写合并缓冲区

### 函数调用开销

- **直接调用**: ~2-3 个时钟周期
- **函数指针调用**: ~5-10 个时钟周期（包括分支预测）
- **相对开销**: 对于处理一行像素（数百到数千像素），调用开销可忽略（< 1%）

### 优化建议

**对于使用者**:
1. 批量处理多行以分摊调用开销
2. 使用 `Factory32()` 获取函数指针后重复使用
3. 避免频繁切换混合模式

**对于实现者**:
1. 确保数据 16 字节对齐以利用 SIMD
2. 使用编译器内联提示
3. 针对常见屏幕分辨率（如 1920、1080）优化循环展开

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/core/SkBlitRow_D32.cpp | 实现 | 实现 `Factory32()` 和 `Color32()`，包含多种 SIMD 优化版本 |
| include/core/SkColor.h | 依赖 | 定义 `SkColor`、`SkPMColor`、`U8CPU` 类型 |
| include/core/SkBitmap.h | 依赖 | 提供位图数据结构 |
| src/core/SkBlitter.cpp | 使用者 | Blitter 类使用行混合功能 |
| src/core/SkDraw.cpp | 使用者 | 高层绘图操作使用行混合 |
| src/opts/SkBlitRow_opts.h | 优化实现 | SIMD 优化实现 |
| src/core/SkOpts.h | 优化框架 | 运行时优化系统 |
| src/core/SkMemset.h | 辅助 | 提供 `memset32` 等优化内存操作 |
