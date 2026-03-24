# SkTypes

> 源文件: `include/core/SkTypes.h`

## 概述
SkTypes.h 是 Skia 的核心类型定义和配置头文件,为整个库提供基础类型定义、平台配置宏、颜色通道布局定义和直方图宏。作为 Skia 最基础的头文件之一,它被几乎所有 Skia 代码包含,负责建立跨平台的类型系统和编译配置基础。

## 架构位置
该文件位于 Skia 类型系统的最底层,在整个架构中处于基础设施层。它通过包含一系列私有基础头文件(SkFeatures.h、SkAPI.h、SkAssert.h 等)来建立完整的类型和宏定义体系,是 Skia 公共 API 和内部实现的共同基础。

## 主要功能模块

### 1. 基础头文件聚合
通过 IWYU pragma 导出关键头文件:
```cpp
#include "include/private/base/SkFeatures.h"     // 平台特性检测
#include "include/private/base/SkLoadUserConfig.h"  // 用户配置加载
#include "include/private/base/SkAPI.h"          // API 导出宏
#include "include/private/base/SkAssert.h"       // 断言宏
#include "include/private/base/SkAttributes.h"   // 编译器属性
#include "include/private/base/SkDebug.h"        // 调试工具
```

### 2. GPU 后端配置
根据宏定义启用/禁用 GPU 后端:
```cpp
#if !defined(SK_GANESH) && !defined(SK_GRAPHITE)
#  undef SK_GL
#  undef SK_VULKAN
#  undef SK_METAL
#  undef SK_DAWN
#  undef SK_DIRECT3D
#endif
```
- **逻辑**: 如果没有启用 Ganesh 或 Graphite GPU 后端,则禁用所有具体的 API 后端
- **目的**: 减小二进制大小,避免链接不必要的图形 API 代码

### 3. 颜色通道布局定义

#### RGBA/BGRA 配置
```cpp
#if defined(SK_R32_SHIFT)
    static_assert(SK_R32_SHIFT == 0 || SK_R32_SHIFT == 16, "");
#elif defined(SK_BUILD_FOR_WIN)
    #define SK_R32_SHIFT 16  // Windows 默认 BGRA
#else
    #define SK_R32_SHIFT 0   // 其他平台默认 RGBA
#endif

#define SK_B32_SHIFT (16-SK_R32_SHIFT)
#define SK_G32_SHIFT 8
#define SK_A32_SHIFT 24
```

**通道布局**:
| 平台 | R 位移 | G 位移 | B 位移 | A 位移 | 布局 |
|------|--------|--------|--------|--------|------|
| Windows | 16 | 8 | 0 | 24 | BGRA |
| 其他 | 0 | 8 | 16 | 24 | RGBA |

#### SK_PMCOLOR_BYTE_ORDER 宏
```cpp
#ifdef SK_CPU_BENDIAN
#  define SK_PMCOLOR_BYTE_ORDER(C0, C1, C2, C3) \
        (SK_ ## C3 ## 32_SHIFT == 0  && ...)
#else
#  define SK_PMCOLOR_BYTE_ORDER(C0, C1, C2, C3) \
        (SK_ ## C0 ## 32_SHIFT == 0  && ...)
#endif
```
- **功能**: 编译期检查颜色通道顺序
- **用法**: `SK_PMCOLOR_BYTE_ORDER(R, G, B, A)` 判断是否为 RGBA 顺序
- **大端处理**: 在大端平台上反转字节顺序检查

### 4. Windows 调试支持
```cpp
#if defined SK_DEBUG && defined SK_BUILD_FOR_WIN
    #ifdef free
        #undef free
    #endif
    #include <crtdbg.h>  // Windows CRT 调试工具
    #undef free
#endif
```
- **目的**: 在 Windows 调试版本中集成 CRT 调试功能(内存泄漏检测等)

### 5. 全局初始化控制
```cpp
#ifndef SK_ALLOW_STATIC_GLOBAL_INITIALIZERS
    #define SK_ALLOW_STATIC_GLOBAL_INITIALIZERS 0
#endif
```
- **默认**: 禁止静态全局初始化器
- **原因**: 避免初始化顺序问题,减少启动时间

### 6. Gamma 和对比度配置
```cpp
#if !defined(SK_GAMMA_EXPONENT)
    #define SK_GAMMA_EXPONENT (0.0f)  // SRGB
#endif

#if !defined(SK_GAMMA_CONTRAST)
    #define SK_GAMMA_CONTRAST (0.5f)  // 平衡值
#endif
```
- **SK_GAMMA_EXPONENT**: Gamma 指数(0.0 表示 sRGB)
- **SK_GAMMA_CONTRAST**: 文本渲染的对比度(0.5 是平衡选择)

### 7. 直方图宏系统

#### 启用标志
```cpp
#define SK_HISTOGRAMS_ENABLED 1  // 如果定义了任何直方图宏
```

#### 直方图宏定义
```cpp
#ifndef SK_HISTOGRAM_BOOLEAN
#  define SK_HISTOGRAM_BOOLEAN(name, sample)
#endif

#ifndef SK_HISTOGRAM_ENUMERATION
#  define SK_HISTOGRAM_ENUMERATION(name, sampleEnum, enumSize)
#endif

#ifndef SK_HISTOGRAM_EXACT_LINEAR
#  define SK_HISTOGRAM_EXACT_LINEAR(name, sample, valueMax)
#endif

#ifndef SK_HISTOGRAM_MEMORY_KB
#  define SK_HISTOGRAM_MEMORY_KB(name, sample)
#endif

// ... 其他直方图宏
```
- **默认行为**: 空操作(嵌入器可以定义实际实现)
- **用途**: 性能指标和使用统计收集
- **示例**: Chromium 使用这些宏将 Skia 指标集成到 Chrome 的 UMA 系统

#### 便利宏
```cpp
#define SK_HISTOGRAM_PERCENTAGE(name, percent_as_int) \
    SK_HISTOGRAM_EXACT_LINEAR(name, percent_as_int, 101)
```

### 8. 优化配置
```cpp
#if defined(SK_ENABLE_OPTIMIZE_SIZE)
    #if !defined(SK_FORCE_RASTER_PIPELINE_BLITTER)
        #define SK_FORCE_RASTER_PIPELINE_BLITTER
    #endif
    #define SK_DISABLE_SDF_TEXT
#endif
```
- **SK_ENABLE_OPTIMIZE_SIZE**: 启用代码大小优化,牺牲部分性能
- **影响**:
  - 强制使用光栅管道 blitter(更小但可能更慢)
  - 禁用 SDF 文本(有符号距离场文本)

### 9. Fuzzing 支持
```cpp
#if defined(SK_BUILD_FOR_LIBFUZZER) || defined(SK_BUILD_FOR_AFL_FUZZ)
#if !defined(SK_BUILD_FOR_FUZZER)
    #define SK_BUILD_FOR_FUZZER
#endif
#endif
```
- **用途**: 为模糊测试构建统一的宏定义

### 10. 统计配置
```cpp
#if !defined(GR_CACHE_STATS)
  #if defined(SK_DEBUG) || defined(SK_DUMP_STATS)
      #define GR_CACHE_STATS  1
  #else
      #define GR_CACHE_STATS  0
  #endif
#endif

#if !defined(GR_GPU_STATS)
  #if defined(SK_DEBUG) || defined(SK_DUMP_STATS) || defined(GPU_TEST_UTILS)
      #define GR_GPU_STATS    1
  #else
      #define GR_GPU_STATS    0
  #endif
#endif
```
- **GR_CACHE_STATS**: GPU 缓存统计(调试或显式启用时开启)
- **GR_GPU_STATS**: GPU 统计(调试、统计或测试时开启)

## 核心类型定义

### SkUnichar
```cpp
typedef int32_t SkUnichar;
```
- **用途**: 表示 Unicode 码点
- **范围**: 0 到 0x10FFFF(完整 Unicode 范围)

### SkGlyphID
```cpp
typedef uint16_t SkGlyphID;
```
- **用途**: 表示字体中的字形索引
- **范围**: 0 到 65535

### 无效 ID 常量
```cpp
static constexpr uint32_t SK_InvalidGenID = 0;
static constexpr uint32_t SK_InvalidUniqueID = 0;
```
- **用途**: Skia 中的生成 ID 和唯一 ID 保留 0 作为无效标记

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkFeatures.h | 平台特性检测 |
| include/private/base/SkLoadUserConfig.h | 加载用户自定义配置 |
| include/private/base/SkAPI.h | SK_API 宏定义 |
| include/private/base/SkAssert.h | 断言宏 |
| include/private/base/SkAttributes.h | 编译器属性宏 |
| include/private/base/SkDebug.h | 调试工具 |
| <cstdint> | 标准整数类型 |

### 被依赖的模块
几乎所有 Skia 头文件都直接或间接包含此文件:
- **SkCanvas.h**: 绘图 API
- **SkPaint.h**: 绘制属性
- **SkBitmap.h**: 位图类
- **所有 GPU 后端**: Ganesh、Graphite
- **所有效果和滤镜**: SkImageFilter、SkShader 等

## 设计模式与设计决策

### 中心化配置
将所有平台相关的配置集中在一个文件中,便于:
- 理解平台差异
- 统一修改配置策略
- 避免配置分散导致的不一致

### 用户可配置性
通过 SkLoadUserConfig.h,允许嵌入器在不修改 Skia 源码的情况下覆盖默认配置。

### 条件编译优化
大量使用 `#if` 和 `#ifndef` 实现编译期配置,避免运行时开销。

### 静态断言
使用 `static_assert` 在编译期验证配置的合法性:
```cpp
static_assert(SK_R32_SHIFT == 0 || SK_R32_SHIFT == 16, "");
```

## 性能考量

### 颜色通道布局
RGBA vs BGRA 的选择影响:
- **内存布局**: 与硬件/操作系统原生格式匹配可减少转换
- **SIMD 优化**: 通道顺序影响向量化代码的效率

### 直方图宏
默认为空操作,零运行时开销;嵌入器实现时应考虑性能影响。

### 静态全局初始化
禁用静态全局初始化器减少:
- 应用启动时间
- 初始化顺序问题

## 平台相关说明

### Windows 特殊处理
- 默认使用 BGRA 颜色布局(与 GDI 一致)
- 集成 CRT 调试工具

### 大端平台
通过 `SK_CPU_BENDIAN` 宏调整字节序相关的宏定义。

### 移动平台
在移动平台上,`SK_ENABLE_OPTIMIZE_SIZE` 更常见,优先考虑二进制大小。

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkFeatures.h | 平台检测实现 |
| include/private/base/SkLoadUserConfig.h | 用户配置加载 |
| include/core/SkColor.h | 使用颜色通道布局宏 |
| include/core/SkCanvas.h | 使用基础类型 |
| src/core/SkOpts.h | 使用平台宏选择优化实现 |
