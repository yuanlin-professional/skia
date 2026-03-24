# SkPngEncoder

> 源文件: `include/encode/SkPngEncoder.h`

## 概述

`SkPngEncoder` 是 Skia 图形库中用于将像素数据编码为 PNG（Portable Network Graphics）格式图像的命名空间。PNG 是一种无损图像压缩格式，支持透明度（Alpha 通道），广泛用于需要精确像素再现的场景，如 UI 截图、图标、技术绘图等。

`SkPngEncoder` 提供了丰富的编码配置选项，包括过滤器策略选择、zlib 压缩级别、tEXt 文本注释块、HDR 元数据以及增益图（Gainmap）嵌入。底层依赖 libpng 库（或可选的 Rust PNG 编码器）执行实际的压缩操作。

### 核心功能

- 支持五种 PNG 行过滤器及其任意组合
- 支持 zlib 压缩级别配置（0-9）
- 支持 tEXt 文本元数据嵌入
- 支持 HDR 元数据（通过 `skhdr::Metadata`）
- 支持增益图（Gainmap）编码，用于 HDR 显示兼容
- 支持增量编码（逐行编码）
- 支持 GPU 纹理图像的读回与编码

## 架构位置

`SkPngEncoder` 位于 Skia 编码器子系统中，与 `SkJpegEncoder` 和 `SkWebpEncoder` 并列为三大核心图像编码器。

```
Skia 编码子系统架构
====================

  应用层 (Application)
        |
        v
  SkPngEncoder (公共 API 命名空间)
        |
        v
  SkEncoder (基类)
        |
        +---> SkPngEncoderBase (PNG 编码基础逻辑)
        |           |
        |           +---> SkPngEncoderImpl (libpng 实现)
        |           |
        |           +---> SkPngRustEncoderImpl (Rust PNG 实现)
        |
        v
  libpng / png-rs (第三方底层库)
        |
        v
  zlib (压缩库)
```

PNG 编码器在实现层具有双后端架构：传统的 libpng C 实现和较新的 Rust PNG 实现。两者共享 `SkPngEncoderBase` 基类中的公共逻辑，但使用不同的底层库完成实际的 PNG 压缩。

## 主要类与结构体

### `SkPngEncoder::FilterFlag` 枚举

PNG 规范定义了五种行过滤器，用于在压缩前对像素数据进行预处理，以提高后续 zlib 压缩的效率。此枚举使用位标志设计，支持通过按位或运算组合多个过滤器。

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| `kZero` | `0x00` | 零过滤器（特殊值，不进行任何过滤） |
| `kNone` | `0x08` | None 过滤器：不修改原始字节 |
| `kSub` | `0x10` | Sub 过滤器：每个字节减去其左侧对应字节 |
| `kUp` | `0x20` | Up 过滤器：每个字节减去其上方对应字节 |
| `kAvg` | `0x40` | Average 过滤器：每个字节减去左侧和上方字节的平均值 |
| `kPaeth` | `0x80` | Paeth 过滤器：使用 Paeth 预测算法 |
| `kAll` | `0xF8` | 所有五种过滤器的组合（默认值） |

```cpp
// 组合多个过滤器的用法示例
auto flags = SkPngEncoder::FilterFlag::kSub | SkPngEncoder::FilterFlag::kPaeth;
```

当选择单个过滤器时，libpng 将对每一行使用该固定过滤器。当选择多个过滤器时，libpng 会使用启发式算法逐行选择编码后最小的过滤器。

### `SkPngEncoder::Options` 结构体

```cpp
struct Options {
    FilterFlag fFilterFlags = FilterFlag::kAll;       // 过滤器策略
    int fZLibLevel = 6;                               // zlib 压缩级别 [0, 9]
    sk_sp<SkDataTable> fComments;                     // tEXt 文本注释
    skhdr::Metadata fHdrMetadata;                     // HDR 元数据
    const SkPixmap* fGainmap = nullptr;               // 增益图像素数据
    const SkGainmapInfo* fGainmapInfo = nullptr;      // 增益图元信息
};
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fFilterFlags` | `FilterFlag` | `kAll` | 选择使用哪些行过滤器策略 |
| `fZLibLevel` | `int` | `6` | zlib 压缩级别，范围 [0, 9]，9 为最大压缩 |
| `fComments` | `sk_sp<SkDataTable>` | 空 | PNG tEXt 块中的键值对注释 |
| `fHdrMetadata` | `skhdr::Metadata` | 默认 | HDR 元数据容器 |
| `fGainmap` | `const SkPixmap*` | `nullptr` | 可选的增益图像素数据 |
| `fGainmapInfo` | `const SkGainmapInfo*` | `nullptr` | 可选的增益图元信息 |

#### tEXt 注释格式

`fComments` 字段使用 `SkDataTable` 存储键值对，其中偶数索引（0, 2, 4, ...）为关键字（keyword），奇数索引（1, 3, 5, ...）为对应的文本内容。例如：

```
索引 0: "Author"      (关键字)
索引 1: "Skia Team"   (文本)
索引 2: "Description"  (关键字)
索引 3: "Test image"   (文本)
```

#### 增益图（Gainmap）支持

增益图是一种用于在 SDR 和 HDR 显示之间进行自适应渲染的技术。`SkPngEncoder` 使用自定义 PNG 块来嵌入增益图：

- **gmAP 块**: 包含增益图数据的完整 PNG 容器
- **gdAT 块**: 位于 gmAP 块内部，存储增益图的元信息（`SkGainmapInfo`）

此方案遵循 W3C PNG 工作组讨论中的 Option B 提案。需要注意的是，`fGainmapInfo` 不能为 `nullptr`（如果 `fGainmap` 非空），因为增益图元数据是正确解释编码增益图所必需的。

## 公共 API 函数

### 一次性编码到流

```cpp
SK_API bool Encode(SkWStream* dst, const SkPixmap& src, const Options& options);
```

将 `SkPixmap` 像素数据编码为 PNG 并写入输出流。这是最常用的 PNG 编码入口。

- **参数**:
  - `dst` - 目标输出流（不转移所有权）
  - `src` - 源像素数据
  - `options` - 编码选项
- **返回值**: 成功返回 `true`，输入无效或不支持时返回 `false`

### 一次性编码到内存

```cpp
SK_API sk_sp<SkData> Encode(const SkPixmap& src, const Options& options);
```

将像素数据编码为 PNG 并以 `SkData` 对象返回编码后的字节数据。适用于需要将编码结果保存在内存中进行后续处理的场景。

- **返回值**: 成功返回包含 PNG 数据的 `sk_sp<SkData>`，失败返回 `nullptr`

### GPU 图像编码

```cpp
SK_API sk_sp<SkData> Encode(GrDirectContext* ctx, const SkImage* img, const Options& options);
```

编码一个 `SkImage` 对象。支持 GPU 纹理图像的自动像素读回。

- **参数**:
  - `ctx` - GPU 上下文；对纹理图像必须提供，光栅图像可传 `nullptr`
  - `img` - 待编码的图像对象
  - `options` - 编码选项
- **返回值**: 成功返回 `sk_sp<SkData>`，像素无法读取或编码失败返回 `nullptr`

### 增量编码器工厂

```cpp
SK_API std::unique_ptr<SkEncoder> Make(SkWStream* dst, const SkPixmap& src, const Options& options);
```

创建增量 PNG 编码器。主要用于需要逐步编码像素行的高级场景，例如在生成大图像时控制内存峰值使用量。

- **注意**: `dst` 的所有权不会被转移，在编码器生存期间必须保持有效
- **返回值**: 成功返回编码器实例，输入无效或不支持时返回 `nullptr`

## 内部实现细节

### 双后端架构

PNG 编码器具有两种实现后端：

1. **libpng 后端**（`SkPngEncoderImpl`）：传统的 C 语言实现，使用成熟的 libpng 库
2. **Rust PNG 后端**（`SkPngRustEncoderImpl`）：使用 Rust 编写的 PNG 库，可能提供更好的内存安全性

两者共享 `SkPngEncoderBase` 基类，该基类处理公共的像素预处理逻辑（如颜色空间转换、行过滤器选择前的数据准备等），而具体的 PNG 块写入和 zlib 压缩则由各自的后端完成。

### 过滤器选择启发式算法

当 `fFilterFlags` 包含多个过滤器时，libpng 使用最小和绝对值（Minimum Sum of Absolute Differences）启发式算法，对每一行分别尝试所有选定的过滤器，然后选择产生最小过滤后数据的那个。这可以优化压缩比，但会增加编码时间。

### 禁用构建支持

`SkPngEncoder_none.cpp` 提供了所有 API 函数的桩实现，当 PNG 编码功能未在构建配置中启用时，确保链接不会失败。所有桩函数将始终返回失败结果。

### 增益图编码流程

1. 将增益图像素数据编码为独立的 PNG 数据流
2. 将 `SkGainmapInfo` 序列化到 gdAT 块
3. 将 PNG 数据流和 gdAT 块包装到 gmAP 自定义块中
4. 将 gmAP 块嵌入主 PNG 文件

## 依赖关系

### 头文件依赖

| 依赖 | 说明 |
|------|------|
| `include/core/SkDataTable.h` | 数据表容器，用于存储 tEXt 注释的键值对 |
| `include/core/SkRefCnt.h` | 引用计数智能指针 `sk_sp` |
| `include/private/SkHdrMetadata.h` | HDR 元数据结构定义 |
| `include/private/base/SkAPI.h` | `SK_API` 导出宏定义 |
| `include/encode/SkEncoder.h` | 编码器基类（IWYU 兼容保留） |

### 前向声明依赖

| 类型 | 说明 |
|------|------|
| `GrDirectContext` | GPU 上下文（Ganesh 后端） |
| `SkData` | 不可变二进制数据容器 |
| `SkImage` | 图像对象 |
| `SkPixmap` | 光栅像素数据视图 |
| `SkWStream` | 可写流抽象接口 |
| `skcms_ICCProfile` | ICC 色彩配置文件 |
| `SkGainmapInfo` | 增益图元信息结构 |

### 第三方库依赖

- **libpng**: 传统 PNG 编码后端
- **zlib**: libpng 使用的数据压缩库
- **png (Rust crate)**: 可选的 Rust PNG 编码后端

## 设计模式与设计决策

### 位标志枚举设计

`FilterFlag` 使用位标志模式，允许通过按位或运算符组合多个过滤器选项。这种设计比使用 `std::set` 或数组更加紧凑高效，同时提供了类型安全的操作符重载（`operator|`）。

### 命名空间组织

与 `SkJpegEncoder` 和 `SkWebpEncoder` 保持一致，使用命名空间而非类来组织 API。这种设计：
- 避免了不必要的对象创建
- 提供了清晰的函数式 API
- 隐藏了内部实现类的细节

### 可选功能的指针语义

增益图相关字段（`fGainmap`、`fGainmapInfo`）使用裸指针并默认为 `nullptr`，表示这些是可选功能。这种设计比使用 `std::optional` 更适合大型对象，因为避免了不必要的拷贝开销。

### IWYU 兼容性

头文件显式包含 `SkEncoder.h` 并带有 `IWYU pragma: keep` 注释，这是为了向后兼容——确保现有客户端代码不需要额外添加 `#include "include/encode/SkEncoder.h"` 即可使用 `SkEncoder` 类型。

### 编码后端可插拔

通过 `SkPngEncoderBase` 抽象层，PNG 编码器可以在 libpng 和 Rust PNG 库之间切换，这是策略模式（Strategy Pattern）的应用。此设计允许 Skia 逐步迁移到更安全的 Rust 实现而不影响公共 API。

## 性能考量

### 过滤器策略与编码速度

| 策略 | 编码速度 | 压缩比 | 适用场景 |
|------|----------|--------|----------|
| `kZero` 单一过滤器 | 最快 | 最低 | 对性能要求极高的场景 |
| `kNone` 或 `kSub` 单一 | 快 | 一般 | 平衡性能和文件大小 |
| `kAll`（默认） | 最慢 | 最佳 | 对文件大小敏感的场景 |

使用单一过滤器可以显著加快编码速度，因为跳过了逐行过滤器选择的启发式计算。对于实时应用或大量图像的批处理，建议选择单一过滤器。

### zlib 压缩级别权衡

| 级别 | 编码速度 | 文件大小 | 说明 |
|------|----------|----------|------|
| 0 | 极快 | 极大 | 完全跳过 zlib 压缩 |
| 1 | 快 | 大 | 最快压缩 |
| 6（默认） | 中等 | 较小 | libpng 默认值，平衡选择 |
| 9 | 慢 | 最小 | 最大压缩 |

`fZLibLevel = 0` 是一个特殊值，会完全跳过 zlib 压缩，生成体积显著增大的 PNG 文件，但编码速度极快。适用于临时存储或管道传输场景。

### 内存使用

- PNG 编码需要为行过滤器和 zlib 压缩缓冲区分配内存
- 使用增量编码器（`Make()`）可以避免一次性加载整个图像的开销
- 增益图嵌入会增加额外的内存消耗，因为增益图需要单独编码为完整的 PNG 数据流

### GPU 图像读回瓶颈

与 JPEG 编码器相同，从 GPU 纹理编码 PNG 需要同步读回像素数据，这可能导致 GPU 管线停顿。建议在渲染间隙或后台线程中执行此操作。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/encode/SkPngEncoder.h` | 公共 API 头文件（本文件） |
| `include/encode/SkEncoder.h` | 编码器基类定义 |
| `src/encode/SkPngEncoderBase.h` | PNG 编码器公共基类头文件 |
| `src/encode/SkPngEncoderBase.cpp` | PNG 编码器公共基类实现 |
| `src/encode/SkPngEncoderImpl.h` | libpng 后端实现头文件 |
| `src/encode/SkPngEncoderImpl.cpp` | libpng 后端实现 |
| `src/encode/SkPngRustEncoderImpl.h` | Rust PNG 后端实现头文件 |
| `src/encode/SkPngRustEncoderImpl.cpp` | Rust PNG 后端实现 |
| `src/encode/SkPngEncoder_none.cpp` | PNG 编码功能禁用时的桩实现 |
| `include/encode/SkJpegEncoder.h` | JPEG 编码器公共 API |
| `include/encode/SkWebpEncoder.h` | WebP 编码器公共 API |
| `include/core/SkDataTable.h` | 数据表容器 |
| `include/private/SkHdrMetadata.h` | HDR 元数据定义 |
