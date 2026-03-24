# SkPngCodecBase

> 源文件: src/codec/SkPngCodecBase.h, src/codec/SkPngCodecBase.cpp

## 概述

`SkPngCodecBase` 是 Skia 图像解码框架中 PNG 解码器的抽象基类，封装了 `SkPngCodec`（基于 libpng）和 `SkPngRustCodec`（基于 Rust 实现）的共享功能。该类提供了 PNG 格式解码的核心流程，包括像素格式转换、颜色空间变换、调色板处理等通用逻辑，使不同底层实现可以复用相同的转换管线。

该类的设计遵循模板方法模式，定义了解码的标准流程，而将具体的 PNG 数据读取和初步解析交给子类实现。它特别关注性能优化，通过智能选择转换路径（仅 swizzle、仅颜色转换或两者结合）来减少不必要的中间步骤。

## 架构位置

`SkPngCodecBase` 在 Skia 编解码器架构中的位置：

```
SkCodec (抽象基类)
  └── SkPngCodecBase (PNG 通用基类)
        ├── SkPngCodec (libpng 实现)
        └── SkPngRustCodec (Rust 实现)
```

**在解码流程中的角色：**
1. **入口层**：`SkCodec::MakeFromStream` 识别 PNG 格式
2. **工厂层**：创建具体的 PNG 解码器实例
3. **基类层**：`SkPngCodecBase` 提供通用转换逻辑
4. **实现层**：子类处理底层 PNG 数据解析

**协作组件：**
- **SkSwizzler**: 像素格式转换和子区域提取
- **SkColorPalette**: 调色板存储
- **SkColorSpaceXform**: 颜色空间转换
- **skcms**: 颜色管理系统

## 主要类与结构体

### SkPngCodecBase

PNG 解码器的抽象基类，定义通用解码流程。

**核心成员变量：**
- `XformMode fXformMode`: 转换模式枚举，决定解码路径
- `std::unique_ptr<SkSwizzler> fSwizzler`: 像素格式转换器
- `skia_private::AutoTMalloc<uint8_t> fStorage`: 中间缓冲区，用于多步转换
- `sk_sp<SkColorPalette> fColorTable`: 调色板（用于索引色 PNG）
- `int fXformWidth`: 实际转换的像素宽度
- `size_t fEncodedRowBytes`: 编码行字节数
- `size_t fDstRowBytes`: 目标行字节数

**核心方法：**
- `initializeXforms()`: 初始化转换管线，选择最优转换路径
- `initializeXformParams()`: 设置转换参数（在采样后调用）
- `applyXformRow()`: 对单行像素应用格式转换和颜色转换
- `createColorTable()`: 从 PLTE 和 tRNS 块创建调色板
- `allocateStorage()`: 根据转换模式分配中间缓冲区

### PaletteColorEntry

```cpp
struct PaletteColorEntry {
    uint8_t red;
    uint8_t green;
    uint8_t blue;
};
```

表示 PNG PLTE 块中的调色板条目，与 PNG 规范的 3 字节结构完全对应。

### XformMode

```cpp
enum XformMode {
    kSwizzleOnly_XformMode,      // 仅需要 swizzle
    kColorOnly_XformMode,         // 仅需要颜色转换
    kSwizzleColor_XformMode,      // 需要 swizzle 和颜色转换
};
```

定义三种转换路径，根据源格式和目标格式智能选择。

## 公共 API 函数

### 静态函数

```cpp
static bool isCompatibleColorProfileAndType(
    const SkCodecs::ColorProfile* profile,
    SkEncodedInfo::Color color)
```

验证颜色配置文件与 PNG 颜色类型的兼容性。检查 CMYK 配置文件（PNG 不支持）和灰度配置文件与颜色类型的匹配。

**返回值：** 如果配置和类型兼容返回 true

### 构造函数

```cpp
SkPngCodecBase(SkEncodedInfo&& encodedInfo,
               std::unique_ptr<SkStream> stream,
               SkEncodedOrigin origin)
```

初始化 PNG 解码器基类，设置编码信息、输入流和方向。自动根据编码信息确定 skcms 像素格式。

### 转换初始化

```cpp
Result initializeXforms(const SkImageInfo& dstInfo,
                       const Options& options,
                       int frameWidth)
```

初始化转换管线的核心方法，智能选择转换路径：
- 计算编码行和目标行的字节数
- 决定是否跳过格式转换（skcms 直接支持时）
- 为调色板 PNG 创建颜色表
- 初始化 swizzler
- 分配中间存储

**参数：**
- `frameWidth`: 帧宽度，可能小于图像宽度（用于动画帧）

```cpp
void initializeXformParams()
```

完成转换参数设置，必须在 `onStartIncrementalDecode` 之后调用，因为采样可能改变 swizzle 宽度。

### 行转换

```cpp
void applyXformRow(SkSpan<uint8_t> dstRow, SkSpan<const uint8_t> srcRow)
void applyXformRow(void* dstRow, const uint8_t* srcRow)
```

对单行像素应用完整转换流程，根据 `fXformMode` 选择路径：
- **kSwizzleOnly_XformMode**: 直接 swizzle 到目标
- **kColorOnly_XformMode**: 直接颜色转换到目标
- **kSwizzleColor_XformMode**: swizzle 到中间缓冲区，再颜色转换到目标

### 访问器

```cpp
size_t getEncodedRowBytes() const
const SkSwizzler* swizzler() const
```

## 内部实现细节

### 转换路径选择逻辑

`initializeXforms()` 中的智能路径选择：

1. **检查 skcms 直接支持**：
   - RGBA 8/16 位、RGB 16 位、灰度 8 位可跳过格式转换
   - 条件：有颜色转换且非子区域解码
   - 路径：`kColorOnly_XformMode`

2. **标准路径**：
   - 创建调色板（如果是索引色）
   - 初始化 swizzler
   - 根据是否有颜色转换选择 `kSwizzleOnly_XformMode` 或 `kSwizzleColor_XformMode`

### 调色板创建流程

`createColorTable()` 实现复杂的调色板处理：

1. **缓存检查**：如果 `dstInfo` 与上次相同，复用现有调色板
2. **读取 PLTE 块**：通过虚函数 `onTryGetPlteChunk()` 获取
3. **读取 tRNS 块**：获取透明度信息
4. **构建颜色表**：
   - 前 N 个条目：使用 alpha + RGB（可能预乘）
   - 剩余条目：纯色（alpha = 255）
   - 使用 SIMD 优化（`SkOpts::RGB_to_RGB1/BGR1`）
5. **应用颜色转换**：如果需要且不在解码时转换
6. **填充多余索引**：用最后一个颜色或黑色填充到 2^bpp 个条目

### 内存管理

- **中间缓冲区**：根据转换模式分配
  - `kSwizzleOnly_XformMode`: 无需缓冲区
  - `kColorOnly_XformMode` 和 `kSwizzleColor_XformMode`:
    - 高精度（>32 bpp）：保持精度
    - 标准精度：使用 4 字节/像素（RGBA_8888）
- **调色板**：使用引用计数的 `sk_sp<SkColorPalette>`

### 格式转换优化

针对不同格式的优化路径：

- **RGB 16 位 → RGBA**: skcms 直接支持，跳过 swizzle
- **RGBA 8/16 位 → 目标**: 颜色转换优先
- **灰度 → 目标**: 保持灰度格式到颜色转换阶段
- **索引色 → 目标**: 必须先 swizzle（查表）

### 预乘 Alpha 处理

- **需要预乘的条件**：目标是 `kPremul_SkAlphaType` 且源是非预乘
- **实现时机**：
  - 调色板：在构建时预乘（除非需要后续颜色转换）
  - 直接像素：在 swizzle 或颜色转换时处理

## 依赖关系

### 直接依赖

- **SkCodec**: 父类，提供编解码器框架
- **SkSwizzler**: 像素格式转换和子区域提取
- **SkColorPalette**: 调色板存储
- **skcms**: 颜色空间转换库
- **SkOpts**: SIMD 优化函数

### 间接依赖

- **SkEncodedInfo**: 编码格式信息
- **SkImageInfo**: 目标图像信息
- **SkStream**: 输入流接口
- **SkColorSpaceXform**: 颜色空间转换（通过基类）

### 被依赖关系

- **SkPngCodec**: libpng 实现的子类
- **SkPngRustCodec**: Rust 实现的子类

### 纯虚函数（子类必须实现）

```cpp
virtual std::optional<SkSpan<const PaletteColorEntry>> onTryGetPlteChunk() = 0;
virtual std::optional<SkSpan<const uint8_t>> onTryGetTrnsChunk() = 0;
```

## 设计模式与设计决策

### 模板方法模式

基类定义解码流程框架，子类实现具体细节：
- 基类：转换管线、调色板处理、格式转换
- 子类：PNG 数据读取、块解析

### 策略模式

通过 `XformMode` 枚举实现不同的转换策略，根据源和目标格式动态选择。

### 延迟初始化

- **swizzler 创建**：在 `getSampler(true)` 时按需创建
- **调色板构建**：在 `initializeXforms()` 时创建并缓存
- **存储分配**：在确定转换模式后按需分配

### 设计决策

1. **智能路径选择**：避免不必要的中间转换，直接使用 skcms 支持的格式
2. **调色板缓存**：避免重复构建（常见于多次解码同一图像）
3. **两步初始化**：`initializeXforms` + `initializeXformParams`，适应采样变化
4. **frameWidth 参数**：支持 APNG 等动画格式的子帧解码
5. **子区域解码限制**：子区域时必须 frameWidth == dstInfo.width()

## 性能考量

### 优化策略

1. **路径优化**：
   - 直接颜色转换：减少一次 swizzle 开销
   - SIMD 加速：调色板构建使用 `SkOpts::RGB_to_RGB1/BGR1`

2. **内存布局**：
   - 中间缓冲区大小恰好一行，减少缓存未命中
   - 调色板对齐到 4 字节边界

3. **计算优化**：
   - 编码行字节数预计算，避免逐行重新计算
   - 断言检查溢出，使用发布版本优化的假设

### 性能瓶颈

- **颜色空间转换**：计算密集型，尤其是 16 位精度
- **调色板查表**：索引色 PNG 需要额外的内存访问
- **多步转换**：`kSwizzleColor_XformMode` 需要两次内存写入

### 内存使用

- **中间缓冲区**：width × 4 或 width × bpp/8 字节
- **调色板**：最多 256 × 4 = 1024 字节
- **swizzler**：取决于配置，通常几百字节

### 典型场景性能

- **RGBA 8 位 → RGBA 8 位（无颜色转换）**：最快，单次 swizzle
- **RGB 16 位 → RGBA 8 位（有颜色转换）**：较快，直接颜色转换
- **索引色 → RGBA 8 位（有颜色转换）**：中等，swizzle + 颜色转换
- **灰度 8 位 → RGBA 8 位（有颜色转换）**：较快，灰度保持到颜色转换

## 相关文件

### 子类实现

- `src/codec/SkPngCodec.h/cpp`: libpng 实现
- `src/codec/SkPngRustCodec.h/cpp`: Rust 实现

### 核心依赖

- `src/codec/SkSwizzler.h/cpp`: 像素格式转换器
- `src/codec/SkColorPalette.h/cpp`: 调色板封装
- `modules/skcms/skcms.h`: 颜色管理系统
- `src/core/SkSwizzlePriv.h`: swizzle 内部实现

### 辅助文件

- `src/codec/SkCodecPriv.h`: 编解码器私有工具
- `include/private/SkEncodedInfo.h`: 编码信息定义
- `include/codec/SkCodec.h`: 编解码器基类

### 测试文件

- `tests/CodecTest.cpp`: 编解码器测试
- `tests/PngTest.cpp`: PNG 特定测试
- `resources/*.png`: 测试图像资源

### 优化相关

- `src/opts/SkOpts.h`: SIMD 优化函数接口
- `src/opts/SkOpts_*.cpp`: 平台特定优化实现
