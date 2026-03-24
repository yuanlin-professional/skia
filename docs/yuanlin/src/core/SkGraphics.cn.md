# SkGraphics

> 源文件
> - include/core/SkGraphics.h
> - src/core/SkGraphics.cpp

## 概述

`SkGraphics` 是 Skia 库的全局初始化和资源管理接口类,提供了库级别的配置、缓存管理和内存统计功能。该类作为 Skia 的入口点,负责初始化运行时优化(CPU 特性检测、SIMD 函数指针选择)、管理字体缓存和资源缓存的生命周期、提供全局内存限制设置。所有方法都是静态方法,不需要实例化对象。

## 架构位置

`SkGraphics` 位于 Skia 架构的最顶层,作为库的全局管理器:

- **初始化层**: 在应用启动时调用,初始化底层优化模块
- **缓存管理层**: 控制 `SkStrikeCache`(字体缓存)、`SkResourceCache`(资源缓存)、`SkTypefaceCache`(字体实例缓存)
- **工厂注册层**: 管理自定义解码器和 SVG 解码器的全局工厂函数
- **诊断层**: 提供内存使用统计和缓存清理接口

## 主要类与结构体

### SkGraphics

纯静态类,无成员变量,所有状态通过底层模块管理。

**公共类型定义**:

```cpp
using ImageGeneratorFromEncodedDataFactory =
    std::unique_ptr<SkImageGenerator> (*)(sk_sp<const SkData>);

using OpenTypeSVGDecoderFactory =
    std::unique_ptr<SkOpenTypeSVGDecoder> (*)(const uint8_t* svg, size_t length);
```

## 公共 API 函数

### 初始化

```cpp
static void Init();
```
初始化 Skia 库,必须在多线程环境下第一次使用 Skia 前调用。线程安全且幂等。

### 字体缓存管理

```cpp
// 限制管理
static size_t GetFontCacheLimit();
static size_t SetFontCacheLimit(size_t bytes);
static int GetFontCacheCountLimit();
static int SetFontCacheCountLimit(int count);

// 状态查询
static size_t GetFontCacheUsed();
static int GetFontCacheCountUsed();

// 缓存清理
static void PurgeFontCache();
static void PurgePinnedFontCache();
```

### Typeface 缓存管理

```cpp
static int GetTypefaceCacheCountLimit();
static int SetTypefaceCacheCountLimit(int count);
```

### 资源缓存管理

```cpp
// 总大小限制
static size_t GetResourceCacheTotalBytesUsed();
static size_t GetResourceCacheTotalByteLimit();
static size_t SetResourceCacheTotalByteLimit(size_t newLimit);

// 单次分配限制
static size_t GetResourceCacheSingleAllocationByteLimit();
static size_t SetResourceCacheSingleAllocationByteLimit(size_t newLimit);

// 缓存清理
static void PurgeResourceCache();
```

### 全局缓存清理

```cpp
static void PurgeAllCaches();
```
清理所有私有缓存(字体、图像、资源),不影响 GPU 上下文相关缓存。

### 诊断工具

```cpp
static void DumpMemoryStatistics(SkTraceMemoryDump* dump);
```
使用 `SkTraceMemoryDump` 接口导出内存使用统计。

### 工厂函数管理

```cpp
static ImageGeneratorFromEncodedDataFactory
    SetImageGeneratorFromEncodedDataFactory(ImageGeneratorFromEncodedDataFactory);

static OpenTypeSVGDecoderFactory
    SetOpenTypeSVGDecoderFactory(OpenTypeSVGDecoderFactory);

static OpenTypeSVGDecoderFactory
    GetOpenTypeSVGDecoderFactory();
```

## 内部实现细节

### 初始化流程

`Init()` 方法按顺序初始化优化模块:

```cpp
void SkGraphics::Init() {
    SkCpu::CacheRuntimeFeatures();      // CPU 特性检测(SSE/AVX/NEON)
    SkOpts::Init();                     // 通用优化函数指针选择
    SkOpts::Init_BitmapProcState();     // 位图处理优化
    SkOpts::Init_BlitMask();            // 遮罩混合优化
    SkOpts::Init_BlitRow();             // 行混合优化
    SkOpts::Init_Memset();              // 内存设置优化
    SkOpts::Init_Swizzler();            // 颜色通道交换优化
}
```

所有初始化都是线程安全的,使用原子操作或锁保护。

### 字体缓存委托

字体缓存方法直接委托给 `SkStrikeCache::GlobalStrikeCache()`:

```cpp
size_t SkGraphics::GetFontCacheLimit() {
    return SkStrikeCache::GlobalStrikeCache()->getCacheSizeLimit();
}

void SkGraphics::PurgeFontCache() {
    SkStrikeCache::GlobalStrikeCache()->purgeAll();
    SkTypefaceCache::PurgeAll();  // 同时清理 typeface 缓存
}
```

### 资源缓存委托

资源缓存方法委托给 `SkResourceCache` 的静态方法:

```cpp
size_t SkGraphics::GetResourceCacheTotalBytesUsed() {
    return SkResourceCache::GetTotalBytesUsed();
}

void SkGraphics::PurgeResourceCache() {
    SkImageFilter_Base::PurgeCache();  // 先清理图像滤镜缓存
    return SkResourceCache::PurgeAll();
}
```

### Typeface 缓存限制

Typeface 缓存限制使用全局变量存储:

```cpp
static int gTypefaceCacheCountLimit = 1024;  // 历史默认值

int SkGraphics::SetTypefaceCacheCountLimit(int count) {
    const int prev = gTypefaceCacheCountLimit;
    gTypefaceCacheCountLimit = count;
    return prev;
}
```

注意: 限制变更仅在下次修改缓存对象时生效。

### SVG 解码器工厂

使用全局函数指针存储:

```cpp
static SkGraphics::OpenTypeSVGDecoderFactory gSVGDecoderFactory = nullptr;

SkGraphics::OpenTypeSVGDecoderFactory
SkGraphics::SetOpenTypeSVGDecoderFactory(OpenTypeSVGDecoderFactory svgDecoderFactory) {
    OpenTypeSVGDecoderFactory old(gSVGDecoderFactory);
    gSVGDecoderFactory = svgDecoderFactory;
    return old;
}
```

允许外部库(如 skia-svg)注入 OpenType SVG 支持。

### PurgeAllCaches 实现

```cpp
void SkGraphics::PurgeAllCaches() {
    SkGraphics::PurgeFontCache();
    SkGraphics::PurgeResourceCache();
    SkImageFilter_Base::PurgeCache();
}
```

综合清理所有类型的缓存,用于低内存场景。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkCpu | CPU 特性检测 |
| SkOpts | 运行时函数指针优化 |
| SkStrikeCache | 字形缓存管理 |
| SkTypefaceCache | Typeface 实例缓存 |
| SkResourceCache | 通用资源缓存(位图、mipmap) |
| SkImageFilter_Base | 图像滤镜缓存 |
| SkBitmapProcState | 位图处理优化 |
| SkBlitMask | 遮罩混合优化 |
| SkBlitRow | 行混合优化 |
| SkMemset | 内存设置优化 |
| SkSwizzlePriv | 颜色通道交换 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| 应用启动代码 | 调用 Init() 初始化库 |
| 内存管理系统 | 调用缓存限制和清理接口 |
| 测试框架 | 使用 PurgeAllCaches() 清理测试状态 |
| 平台集成层 | 注册自定义解码器工厂 |

## 设计模式与设计决策

### 外观模式(Facade Pattern)

`SkGraphics` 为底层多个缓存和优化模块提供统一接口:
- 隐藏 `SkStrikeCache`、`SkResourceCache` 等实现细节
- 简化 Skia 的使用门槛
- 提供一致的命名约定(`Get/Set/Purge`)

### 单例模式(隐式)

虽然没有显式单例实现,但通过静态方法访问全局单例:
```cpp
SkStrikeCache::GlobalStrikeCache()  // 返回全局 strike 缓存
```

### 策略模式(工厂注入)

允许运行时替换解码器实现:
```cpp
SetImageGeneratorFromEncodedDataFactory(customFactory);
SetOpenTypeSVGDecoderFactory(customSVGDecoder);
```

优点: 支持可插拔的编解码器,无需重新编译 Skia。

### 设计决策: 纯静态类

为什么不使用实例方法:
- Skia 是全局库,不需要多个实例
- 简化 API 调用(无需创建对象)
- 与 C 语言环境集成更容易

### 设计决策: Init() 幂等性

为什么 Init() 可以多次调用:
- 简化多模块初始化场景
- 避免"谁先初始化"的依赖问题
- 线程安全保证多线程启动的正确性

### 设计决策: 单次分配限制

为什么需要 `SetResourceCacheSingleAllocationByteLimit`:
- 防止单个大对象(如大位图)清空整个缓存
- 平衡缓存命中率和内存使用
- 默认值为 0(总是尝试缓存)

## 性能考量

### 初始化开销

`Init()` 仅在首次调用时执行实际工作:
- 后续调用通过原子标志快速返回
- CPU 特性检测结果缓存在静态变量中
- 函数指针选择一次性完成

### 缓存限制的权衡

**字体缓存**:
- 限制过小: 频繁重建字形,CPU 密集
- 限制过大: 内存占用高,可能触发系统内存压力

**资源缓存**:
- 缓存 mipmap、缩放位图等
- 单次分配限制防止缓存抖动

### PurgePinnedFontCache 优化

```cpp
void PurgePinnedFontCache();
```

专门清理被"固定"的 strike:
- 某些情况下 strike 被客户端代码引用
- 常规清理无法回收这些内存
- 客户端释放引用后调用此方法回收

### 内存统计开销

`DumpMemoryStatistics()` 使用:
- 遍历缓存条目计算内存使用
- 不应在性能关键路径调用
- 主要用于调试和性能分析

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/core/SkCpu.h | 依赖 | CPU 特性检测 |
| src/core/SkOpts.h | 依赖 | 运行时优化选择 |
| src/core/SkStrikeCache.h | 依赖 | 字形缓存 |
| src/core/SkResourceCache.h | 依赖 | 资源缓存 |
| src/core/SkTypefaceCache.h | 依赖 | Typeface 缓存 |
| src/core/SkImageFilter_Base.h | 依赖 | 图像滤镜缓存 |
| include/core/SkImageGenerator.h | 接口 | 图像解码器基类 |
| include/core/SkOpenTypeSVGDecoder.h | 接口 | OpenType SVG 解码器 |
| include/core/SkTraceMemoryDump.h | 接口 | 内存统计接口 |
