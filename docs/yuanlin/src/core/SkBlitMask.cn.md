# SkBlitMask

> 源文件: src/core/SkBlitMask.h

## 概述

`SkBlitMask.h` 是 Skia 图形库中遮罩位块传输（mask blitting）的核心接口头文件。该文件定义了 `SkOpts` 命名空间中的优化遮罩混合函数指针和初始化接口，提供了将带有 Alpha 通道的遮罩高效混合到 32 位目标像素缓冲区的能力。

该文件是 Skia 运行时优化框架的一部分，通过函数指针机制支持根据 CPU 特性动态选择最优的 SIMD 实现（如 SSSE3、AVX2 等），在保持接口简洁的同时提供高性能的遮罩渲染功能。遮罩混合广泛应用于文字渲染、抗锯齿、阴影效果等图形操作中。

## 架构位置

在 Skia 的整体架构中，`SkBlitMask.h` 位于核心渲染层的位块传输子系统：

```
Skia Graphics Library
├── Public API Layer
│   └── SkCanvas, SkPaint, SkPath
├── Core Rendering Layer
│   ├── SkDraw (绘图协调器)
│   ├── Blitting Subsystem
│   │   ├── SkBlitter (位块传输器基类)
│   │   ├── SkBlitMask (遮罩混合接口) ← 当前文件
│   │   ├── SkBlitMask_opts.cpp (优化调度器)
│   │   ├── SkBlitMask_opts_ssse3.cpp (SSSE3 实现)
│   │   ├── SkBlitRow (行级混合)
│   │   └── 其他 Blit 组件
│   └── Optimization Layer (SkOpts)
│       └── blit_mask_d32_a8 (函数指针)
└── Base Types
    └── SkColor, SkAlpha, SkPMColor
```

该文件作为遮罩混合的接口层，连接上层绘图 API 和底层优化实现。

## 主要类与结构体

该文件不定义类或结构体，而是在 `SkOpts` 命名空间中声明函数指针和初始化函数。

### SkOpts 命名空间

| 命名空间 | 作用 |
|---------|------|
| `SkOpts` | Skia 优化函数命名空间，包含运行时可配置的优化函数指针 |

### 关键函数指针

| 函数指针 | 签名 | 说明 |
|---------|------|------|
| `blit_mask_d32_a8` | `void (*)(SkPMColor* dst, size_t dstRB, const SkAlpha* mask, size_t maskRB, SkColor color, int w, int h)` | 将 8 位 Alpha 遮罩与颜色混合到 32 位目标缓冲区 |

## 公共 API 函数

### `SkOpts::blit_mask_d32_a8`

```cpp
extern void (*blit_mask_d32_a8)(SkPMColor* dst, size_t dstRB,
                                const SkAlpha* mask, size_t maskRB,
                                SkColor color, int w, int h);
```

**功能**: 将带有 8 位 Alpha 通道的遮罩混合到 32 位目标像素缓冲区。

**参数**:
- `dst`: 目标像素缓冲区指针（32 位预乘 Alpha ARGB 格式）
- `dstRB`: 目标缓冲区的行字节数（row bytes），即一行像素的字节跨度
- `mask`: 遮罩数据指针（8 位 Alpha 值，0-255）
- `maskRB`: 遮罩的行字节数
- `color`: 源颜色（非预乘 Alpha 的 ARGB）
- `w`: 混合区域的宽度（像素）
- `h`: 混合区域的高度（像素）

**返回值**: 无 (void)

**行为**:
1. 对于遮罩中的每个像素，读取其 Alpha 值
2. 将源颜色与遮罩 Alpha 结合
3. 使用混合模式（通常是 SrcOver）与目标像素混合
4. 写入结果到目标缓冲区

**数学公式**（典型的 SrcOver 混合）:
```
src_alpha = mask[i] / 255.0 * color.alpha / 255.0
src_premul = color.rgb * src_alpha
dst_result = src_premul + dst[i] * (1 - src_alpha)
```

**使用示例**:
```cpp
// 初始化优化函数
SkOpts::Init_BlitMask();

// 准备数据
SkPMColor dstPixels[1920 * 1080];
uint8_t mask[1920 * 1080];
SkColor color = SK_ColorRED;

// 执行混合
SkOpts::blit_mask_d32_a8(
    dstPixels, 1920 * sizeof(SkPMColor),
    mask, 1920,
    color,
    1920, 1080
);
```

### `SkOpts::Init_BlitMask()`

```cpp
void Init_BlitMask();
```

**功能**: 初始化遮罩混合优化函数指针。

**参数**: 无

**返回值**: 无 (void)

**行为**:
1. 检测当前 CPU 支持的指令集（SSSE3、AVX2 等）
2. 将 `blit_mask_d32_a8` 函数指针设置为最优实现
3. 通过静态初始化自动调用，通常无需手动调用

**调用时机**:
- Skia 库初始化时自动调用
- 可以在首次使用遮罩混合前显式调用确保初始化完成

## 内部实现细节

### 函数指针初始化机制

该文件只声明函数指针，实际初始化在 `SkBlitMask_opts.cpp` 中：

```cpp
// SkBlitMask_opts.cpp 中的初始化逻辑
namespace SkOpts {
    DEFINE_DEFAULT(blit_mask_d32_a8);  // 定义并设置默认实现

    void Init_BlitMask() {
        static bool initialized = init();  // 只执行一次
    }

    static bool init() {
        #if defined(SK_CPU_X86)
            if (SkCpu::Supports(SkCpu::SSSE3)) {
                Init_BlitMask_ssse3();  // 激活 SSSE3 优化
            }
        #endif
        return true;
    }
}
```

### 优化实现选择

根据 CPU 特性，函数指针可能指向以下实现之一：

| 实现 | 文件 | 指令集 | 性能 |
|------|------|--------|------|
| 默认实现 | src/opts/SkBlitMask_opts.h | 标量 | 基准 |
| SSSE3 实现 | src/opts/SkBlitMask_opts.h | SSSE3 | 2-3x |
| AVX2 实现 | src/opts/SkBlitMask_opts.h | AVX2 | 3-5x |
| NEON 实现 | src/opts/SkBlitMask_opts.h | NEON (ARM) | 2-4x |

### 行字节数 (Row Bytes) 的作用

```cpp
dstRB  // 目标缓冲区的行字节数
maskRB // 遮罩的行字节数
```

**用途**:
- 支持带有填充（padding）的缓冲区
- 支持在大缓冲区中处理子区域
- 允许不连续的内存布局

**计算下一行的地址**:
```cpp
dst_next_row = (SkPMColor*)((uint8_t*)dst + dstRB);
mask_next_row = mask + maskRB;
```

### 颜色格式

- **输入颜色** (`SkColor`): 非预乘 Alpha 的 ARGB，格式为 `0xAARRGGBB`
- **目标像素** (`SkPMColor`): 预乘 Alpha 的 ARGB
- **遮罩** (`SkAlpha`): 8 位 Alpha 值（0-255）

**预乘 Alpha 的优势**:
- 混合计算更高效
- 避免除法运算
- 更适合 SIMD 优化

## 依赖关系

### 依赖的模块

| 模块 | 路径 | 用途 |
|------|------|------|
| SkColor | include/core/SkColor.h | 提供 `SkColor`、`SkPMColor`、`SkAlpha` 类型 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| SkBlitMask_opts.cpp | 实现 `Init_BlitMask()` 和初始化逻辑 |
| SkBlitMask_opts_ssse3.cpp | 提供 SSSE3 优化实现 |
| SkA8_Blitter | 使用遮罩混合功能绘制 Alpha 遮罩 |
| SkARGB32_Blitter | 使用遮罩混合功能 |
| SkDraw | 高层绘图操作中使用遮罩混合 |
| 文字渲染系统 | 使用遮罩混合渲染字形 |
| 阴影效果 | 使用遮罩混合渲染阴影 |

## 设计模式与设计决策

### 1. 策略模式 (Strategy Pattern)

通过函数指针实现运行时算法选择：
- **策略接口**: `blit_mask_d32_a8` 函数签名
- **具体策略**: 默认实现、SSSE3 实现、AVX2 实现等
- **上下文**: `SkOpts` 命名空间

### 2. 外观模式 (Facade Pattern)

简化的接口隐藏了复杂的优化选择逻辑：
- **外观**: `blit_mask_d32_a8` 函数指针
- **子系统**: CPU 检测、SIMD 实现、条件编译
- **收益**: 使用者无需关心底层优化细节

### 3. 延迟初始化 (Lazy Initialization)

优化函数在首次使用前才初始化：
- 避免不必要的 CPU 检测开销
- 使用静态局部变量确保线程安全
- C++11 保证静态局部变量的线程安全初始化

### 设计决策

**决策1: 为什么使用函数指针而不是虚函数？**
- **零对象开销**: 无需对象实例
- **调用效率**: 函数指针调用比虚函数快
- **灵活性**: 可以在运行时动态替换实现
- **C 兼容**: 便于与 C 代码互操作

**决策2: 为什么分离接口定义和实现？**
```
SkBlitMask.h       // 接口定义
SkBlitMask_opts.cpp      // 调度器
SkBlitMask_opts_ssse3.cpp // SSSE3 实现
```
- **模块化**: 清晰的职责划分
- **条件编译**: SIMD 实现需要特殊编译标志
- **可维护性**: 易于添加新的优化版本

**决策3: 为什么使用 8 位 Alpha 遮罩而不是 1 位黑白遮罩？**
- **抗锯齿**: 8 位 Alpha 支持平滑边缘
- **质量**: 更好的视觉效果
- **文字渲染**: 现代字体渲染需要灰度抗锯齿

**决策4: 为什么将颜色作为参数传入而不是预先应用到遮罩？**
```cpp
blit_mask_d32_a8(dst, dstRB, mask, maskRB, color, w, h);
```
- **内存效率**: 避免创建临时的彩色遮罩缓冲区
- **性能**: 在混合过程中应用颜色，减少内存访问
- **灵活性**: 同一遮罩可以用不同颜色绘制多次

**决策5: 为什么需要 row bytes 参数？**
```cpp
dstRB, maskRB  // 行字节数
```
- **内存对齐**: 支持对齐填充（如 16 字节对齐）
- **子区域**: 支持在大缓冲区中处理子矩形
- **GPU 兼容**: 与 GPU 纹理的行跨度概念一致

**决策6: 为什么命名为 `d32_a8`？**
- `d32`: 目标（destination）是 32 位像素
- `a8`: Alpha 遮罩是 8 位
- **清晰性**: 函数名明确表达输入输出格式

## 性能考量

### SIMD 优化收益

不同实现的性能对比（相对于标量实现）：

| 实现 | 指令集 | 典型加速比 | 适用平台 |
|------|--------|-----------|----------|
| 标量实现 | 无 | 1x (基准) | 所有平台 |
| SSSE3 | SSSE3 | 2-3x | x86/x64 (2006+) |
| AVX2 | AVX2 | 3-5x | x86/x64 (2013+) |
| NEON | NEON | 2-4x | ARM (大多数现代 ARM) |

### 内存带宽分析

遮罩混合操作的内存访问：
- **读取**: 每像素 4 字节（目标）+ 1 字节（遮罩）= 5 字节
- **写入**: 每像素 4 字节（目标）
- **总带宽**: 每像素 9 字节

**1920x1080 屏幕的理论带宽需求**:
- 单帧: 1920 × 1080 × 9 = 18.66 MB
- 60 FPS 全屏更新: ~1.1 GB/s
- 现代内存带宽（~50 GB/s）足够

### 缓存优化

- **顺序访问**: 按行处理，良好的空间局部性
- **预取**: CPU 可以有效预取顺序数据
- **缓存行**: 一次加载 64 字节（16 个像素）

### 典型性能指标

在现代 CPU 上混合 1920x1080 遮罩的时间：

| 实现 | 时间 | 吞吐量 |
|------|------|--------|
| 标量实现 | ~8-10 ms | ~200 M pixels/s |
| SSSE3 | ~3-4 ms | ~500 M pixels/s |
| AVX2 | ~2-3 ms | ~700 M pixels/s |

### 优化建议

**对于使用者**:
1. 批量处理多个遮罩以分摊函数调用开销
2. 确保数据对齐（16 字节对齐获得最佳性能）
3. 使用适当的 row bytes 以利用硬件预取

**对于实现者**:
1. 使用 SIMD 并行处理多个像素
2. 循环展开减少分支开销
3. 使用 `__restrict__` 关键字提示无别名

### 瓶颈分析

对于大多数场景：
- **内存带宽受限**: 当数据不在缓存中时
- **计算受限**: 当数据在缓存中且使用复杂混合模式时
- **优化重点**: 减少内存访问，提高缓存命中率

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/core/SkBlitMask_opts.cpp | 实现 | 实现初始化逻辑和调度器 |
| src/core/SkBlitMask_opts_ssse3.cpp | 实现 | SSSE3 优化实现 |
| src/opts/SkBlitMask_opts.h | 实现 | 包含所有平台的优化实现 |
| include/core/SkColor.h | 依赖 | 定义颜色类型 |
| src/core/SkCpu.h | 依赖 | CPU 特性检测 |
| src/core/SkOptsTargets.h | 依赖 | 优化目标定义 |
| src/core/SkA8_Blitter.cpp | 使用者 | 8 位 Alpha Blitter 使用遮罩混合 |
| src/core/SkARGB32_Blitter.cpp | 使用者 | 32 位 ARGB Blitter 使用遮罩混合 |
| src/core/SkDraw.cpp | 使用者 | 高层绘图操作使用遮罩混合 |
| src/core/SkGlyphRun.cpp | 使用者 | 文字渲染使用遮罩混合 |
| src/effects/SkMaskFilter.cpp | 使用者 | 遮罩滤镜使用遮罩混合 |
