# SkUserConfig

> 源文件: `include/config/SkUserConfig.h`

## 概述

SkUserConfig.h 是 Skia 的用户级配置文件,提供了一系列可选的宏定义,允许开发者在编译期自定义 Skia 的行为。该文件在 SkTypes.h 初始化基础定义后被包含,使用户能够覆盖或扩展默认配置,是 Skia 适配不同平台和应用需求的核心机制。

## 架构位置

SkUserConfig.h 位于 Skia 配置系统的最顶层,属于编译期配置层。它在 SkTypes.h(根头文件)加载过程中被包含,早于几乎所有其他 Skia 头文件。该文件的宏定义影响整个 Skia 库的编译行为,包括调试机制、内存管理、性能优化和平台适配。

## 配置分类

### 调试与发布模式

#### SK_DEBUG / SK_RELEASE

```cpp
//#define SK_DEBUG
//#define SK_RELEASE
```

**用途**: 控制调试代码的编译

**默认行为**:
- SkTypes.h 根据 NDEBUG 宏自动定义
- 未定义 NDEBUG → SK_DEBUG
- 定义了 NDEBUG → SK_RELEASE

**调试代码包括**:
- 参数验证和断言
- 预乘 Alpha 格式检查
- 边界检查
- 内存标记

**使用场景**:
- 强制调试模式: 即使在 Release 构建中启用检查
- 强制发布模式: 在 Debug 构建中禁用检查以测试性能

**性能影响**: 调试代码可能显著降低运行速度(10%-50%)

#### SkDebugf

```cpp
//#define SkDebugf(...)  MyFunction(__VA_ARGS__)
```

**用途**: 重定向调试输出

**默认行为**: 使用 printf 风格输出到标准错误

**自定义场景**:
- 移动平台: 重定向到系统日志(如 Android logcat)
- 嵌入式系统: 输出到串口或文件
- 测试框架: 捕获输出用于验证

**示例**:
```cpp
// Android 平台
#define SkDebugf(...) __android_log_print(ANDROID_LOG_DEBUG, "Skia", __VA_ARGS__)

// 文件记录
#define SkDebugf(...) fprintf(my_log_file, __VA_ARGS__)
```

#### SK_ABORT

```cpp
//#define SK_ABORT(message, ...)
```

**用途**: 自定义断言失败处理

**默认行为**:
1. 使用 SkDebugf 打印错误消息
2. 调用 sk_abort_no_print() 终止程序

**自定义场景**:
- 异常处理: 抛出 C++ 异常而非终止
- 崩溃报告: 上传崩溃信息到服务器
- 调试器集成: 触发断点

**示例**:
```cpp
#define SK_ABORT(message, ...) \
    do { \
        log_error(message, ##__VA_ARGS__); \
        throw SkiaException(message); \
    } while(0)
```

### 缓存与内存配置

#### SK_DEFAULT_FONT_CACHE_LIMIT

```cpp
//#define SK_DEFAULT_FONT_CACHE_LIMIT   (1024 * 1024)
```

**用途**: 字体缓存内存上限(字节)

**默认值**: Skia 内置值(通常 2MB)

**说明**:
- 缓存光栅化的字形位图
- 超过限制时清理最少使用的条目
- 影响文本渲染性能

**调整建议**:
- 桌面应用: 2-8 MB(默认或更高)
- 移动应用: 1-2 MB(内存受限)
- 嵌入式: 512 KB - 1 MB(严格限制)

#### SK_DEFAULT_FONT_CACHE_COUNT_LIMIT

```cpp
// #define SK_DEFAULT_FONT_CACHE_COUNT_LIMIT   2048
```

**用途**: 字体缓存条目数量上限

**默认值**: 内置值(通常 2048)

**说明**: 限制缓存的字形数量,与内存限制配合使用

#### SK_DEFAULT_IMAGE_CACHE_LIMIT

```cpp
//#define SK_DEFAULT_IMAGE_CACHE_LIMIT (1024 * 1024)
```

**用途**: 图像缓存内存上限(字节)

**默认值**: 内置值(通常根据平台自动确定)

**说明**:
- 缓存解码后的位图
- SkGraphics::setImageCacheLimit() 可运行时修改
- 影响图像解码性能

**运行时 API**:
```cpp
// 设置缓存大小
SkGraphics::setImageCacheLimit(8 * 1024 * 1024); // 8MB

// 获取当前缓存大小
size_t cacheSize = SkGraphics::getImageCacheLimit();
```

#### SK_MAX_SIZE_FOR_LCDTEXT

```cpp
//#define SK_MAX_SIZE_FOR_LCDTEXT     48
```

**用途**: LCD 次像素文本渲染的最大字号

**默认值**: 48 点

**说明**:
- 大字号使用 LCD 渲染成本高且效果不明显
- 超过此值的文本使用灰度抗锯齿
- 影响文本渲染质量和性能

**调整建议**:
- 提高可读性: 增大到 64-96
- 优化性能: 降低到 32-36
- 高 DPI 屏幕: 可适当提高

### 平台适配

#### SK_R32_SHIFT

```cpp
//#define SK_R32_SHIFT    16
```

**用途**: 修改 kN32_SkColorType 的字节序

**默认行为**: 根据平台自动确定(BGRA 或 RGBA)

**说明**:
- 用于匹配 X Window System 的 BGRA 字节序
- 定义 R 通道在 32 位字中的位偏移
- 影响 kN32_SkColorType 的实际格式

**风险**: 不当修改可能导致颜色错误

#### SK_CANVAS_SAVE_RESTORE_PREALLOC_COUNT

```cpp
//#define SK_CANVAS_SAVE_RESTORE_PREALLOC_COUNT 32
```

**用途**: SkCanvas 预分配的保存/恢复栈大小

**默认值**: 内置值(通常 4-8)

**说明**:
- save() 和 restore() 使用的栈空间
- 超过预分配大小时动态扩展
- 影响深度嵌套绘制的性能

**调整建议**:
- 复杂 UI: 增加到 32-64(减少动态分配)
- 简单绘制: 保持默认(节省栈空间)

### 性能与优化

#### SK_USE_DRAWING_MIPMAP_DOWNSAMPLER

```cpp
//#define SK_USE_DRAWING_MIPMAP_DOWNSAMPLER
```

**用途**: 使用较小但较慢的 Mipmap 生成器

**默认行为**: 使用快速但占用更多内存的实现

**说明**:
- Mipmap 用于图像缩放的预计算级别
- 慢速版本: 节省内存,增加计算时间
- 快速版本: 消耗更多内存,减少计算时间

**适用场景**:
- 内存受限设备: 启用此选项
- 性能优先: 使用默认快速版本

#### SKVX_DISABLE_SIMD

```cpp
// #define SKVX_DISABLE_SIMD
```

**用途**: 禁用 SkVx 的 SIMD 优化

**默认行为**: 自动使用 SSE/NEON/AVX 指令

**说明**:
- SkVx: Skia 的向量化计算库
- SIMD: Single Instruction Multiple Data(单指令多数据)
- 禁用后使用标量实现

**适用场景**:
- 调试: 排查 SIMD 相关问题
- 兼容性: 不支持 SIMD 的旧 CPU
- 基准测试: 评估 SIMD 收益

**性能影响**: 禁用可能降低性能 2-4 倍

#### SKRP_CPU_SCALAR

```cpp
// #define SKRP_CPU_SCALAR
```

**用途**: 禁用 SkRasterPipeline 的 SIMD 优化

**默认行为**: 使用 SIMD 加速光栅化管线

**说明**:
- SkRasterPipeline: Skia 的 CPU 光栅化后端
- 标量模式: 逐像素处理
- SIMD 模式: 批量处理多个像素

**性能影响**: 禁用可能降低光栅化性能 3-8 倍

### 直方图与日志

#### 直方图宏

```cpp
//#define SK_HISTOGRAM_BOOLEAN(name, sample)
//#define SK_HISTOGRAM_ENUMERATION(name, sampleEnum, enumSize)
//#define SK_HISTOGRAM_EXACT_LINEAR(name, sample, valueMax)
//#define SK_HISTOGRAM_CUSTOM_EXACT_LINEAR(name, sample, value_min, value_max, bucket_count)
//#define SK_HISTOGRAM_MEMORY_KB(name, sample)
//#define SK_HISTOGRAM_CUSTOM_COUNTS(name, sample, countMin, countMax, bucketCount)
//#define SK_HISTOGRAM_CUSTOM_MICROSECONDS_TIMES(name, sampleUSec, minUSec, maxUSec, bucketCount)
```

**用途**: 集成应用的度量收集系统

**默认行为**: 空操作宏(不收集数据)

**说明**:
- Skia 内部在关键路径插入度量点
- 用户定义这些宏以收集性能和行为数据
- 数据可用于性能分析和优化决策

**示例**:
```cpp
// 集成 Chrome 的直方图系统
#define SK_HISTOGRAM_BOOLEAN(name, sample) \
    UMA_HISTOGRAM_BOOLEAN(name, sample)

#define SK_HISTOGRAM_MEMORY_KB(name, sample) \
    UMA_HISTOGRAM_MEMORY_KB(name, sample)
```

#### SK_PIPELINE_LIFETIME_LOGGING

```cpp
//#define SK_PIPELINE_LIFETIME_LOGGING
```

**用途**: 启用 Graphite 管线生命周期日志

**说明**:
- Graphite: Skia 的新一代 GPU 后端
- 记录管线对象的创建和销毁
- 用于调试资源泄漏和管理问题

### 编译器扩展

#### 内联与优化宏

```cpp
//#define SK_ALWAYS_INLINE inline __attribute__((always_inline))
//#define SK_NEVER_INLINE __attribute__((noinline))
//#define SK_PRINTF_LIKE(A, B) __attribute__((format(printf, (A), (B))))
//#define SK_NO_SANITIZE(A) __attribute__((no_sanitize(A)))
//#define SK_TRIVIAL_ABI [[clang::trivial_abi]]
```

**用途**: 自定义编译器特定的优化指令

**默认行为**: SkTypes.h 为 MSVC 和 Clang/GCC 提供默认定义

**说明**:
- **SK_ALWAYS_INLINE**: 强制内联关键函数
- **SK_NEVER_INLINE**: 防止内联(用于调试或减小代码体积)
- **SK_PRINTF_LIKE**: 启用 printf 格式字符串检查
- **SK_NO_SANITIZE**: 禁用特定 Sanitizer 检查
- **SK_TRIVIAL_ABI**: 优化小对象的传递

**适用场景**: 使用非标准编译器或需要精细控制优化

### DLL 导出

#### SK_API

```cpp
//#define SK_API __declspec(dllexport)
```

**用途**: 自定义 DLL 导出标记

**默认行为**: Clang 和 MSVC 自动定义

**说明**:
- 编译为动态库时标记公共 API
- 不同平台使用不同语法
- 影响符号可见性

**示例**:
```cpp
// Windows DLL
#define SK_API __declspec(dllexport)

// Unix 共享库
#define SK_API __attribute__((visibility("default")))
```

### 第三方库集成

#### SK_DNG_VERSION

```cpp
// #define SK_DNG_VERSION 0x01040000
```

**用途**: 指定 DNG SDK 版本

**默认值**: 0x01040000 (DNG SDK 1.4)

**说明**:
- DNG: Digital Negative(Adobe RAW 格式)
- 版本格式: 0xMMmmPPPP(主版本.次版本.补丁)
- DNG 1.4 = 0x01040000
- DNG 1.7.1 = 0x01070100

**适用场景**: 使用不同版本的 dng_sdk 时需要匹配

## 依赖关系

### 依赖的模块

SkUserConfig.h 不依赖其他头文件,是纯宏定义。

### 被依赖的模块

几乎所有 Skia 模块都间接依赖此文件:
- **SkTypes.h**: 包含并应用这些配置
- **所有公共 API**: 通过 SkTypes.h 间接受影响
- **构建系统**: 编译期决策

## 设计模式与设计决策

### 注释形式的默认配置

所有宏定义默认都被注释:
- 避免意外覆盖 Skia 的智能默认值
- 用户必须显式启用自定义配置
- 文档化所有可用选项

### 编译期配置而非运行时

优势:
- 零运行时开销
- 编译器可基于配置优化
- 减小二进制体积(排除未使用代码)

劣势:
- 需要重新编译以更改配置
- 无法动态调整

### 本地编辑而非命令行

文件编辑方式:
```cpp
// 本地修改 SkUserConfig.h
#define SK_DEBUG
#define SK_DEFAULT_FONT_CACHE_LIMIT (4 * 1024 * 1024)
```

命令行方式:
```bash
# 构建命令
clang++ -DSK_DEBUG -DSK_DEFAULT_FONT_CACHE_LIMIT=4194304 ...
```

两种方式等效,文件编辑更适合持久化配置。

## 性能考量

### 调试开销

启用 SK_DEBUG 的性能影响:
- 边界检查: 5-10% 开销
- 参数验证: 3-8% 开销
- 内存标记: 5-15% 开销
- 总体: 可能降低 20-50% 性能

### 缓存调优

缓存大小对性能的影响:

| 场景 | 字体缓存 | 图像缓存 | 性能影响 |
|------|---------|---------|---------|
| 文本密集 | 4-8 MB | 2-4 MB | 减少字形重绘 |
| 图像密集 | 1-2 MB | 16-32 MB | 减少解码次数 |
| 内存受限 | 512 KB | 1-2 MB | 可能增加缓存未命中 |

### SIMD 影响

SIMD 优化的性能提升:
- 颜色转换: 2-4x 加速
- 模糊滤镜: 3-6x 加速
- 光栅化: 3-8x 加速

禁用 SIMD 仅用于调试或兼容性。

## 平台特定建议

### 桌面平台 (Windows/macOS/Linux)

```cpp
// 充足内存,优先性能
#define SK_DEFAULT_FONT_CACHE_LIMIT (8 * 1024 * 1024)
#define SK_DEFAULT_IMAGE_CACHE_LIMIT (64 * 1024 * 1024)
// 保持 SIMD 启用
```

### 移动平台 (iOS/Android)

```cpp
// 内存受限,平衡性能
#define SK_DEFAULT_FONT_CACHE_LIMIT (2 * 1024 * 1024)
#define SK_DEFAULT_IMAGE_CACHE_LIMIT (16 * 1024 * 1024)
#define SK_MAX_SIZE_FOR_LCDTEXT 36
```

### 嵌入式平台

```cpp
// 严格内存限制
#define SK_DEFAULT_FONT_CACHE_LIMIT (512 * 1024)
#define SK_DEFAULT_IMAGE_CACHE_LIMIT (2 * 1024 * 1024)
#define SK_USE_DRAWING_MIPMAP_DOWNSAMPLER
// 可能禁用 SIMD(根据硬件)
```

## 相关文件

| 文件 | 关系 |
|------|------|
| include/core/SkTypes.h | 包含 SkUserConfig.h 并应用配置 |
| include/core/SkGraphics.h | 运行时缓存 API |
| src/core/SkRasterPipeline.h | 受 SIMD 配置影响 |
| include/private/SkVx.h | 受 SIMD 配置影响 |
