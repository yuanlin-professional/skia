# SkWebpEncoder

> 源文件: `include/encode/SkWebpEncoder.h`

## 概述

`SkWebpEncoder` 是 Skia 图形库中用于将像素数据编码为 WebP 格式图像的命名空间。WebP 是由 Google 开发的现代图像格式，同时支持有损和无损压缩，相比 JPEG 和 PNG 通常能提供更优的压缩效率。

`SkWebpEncoder` 是 Skia 三大核心图像编码器中唯一支持动画编码的编码器，通过 `EncodeAnimated()` 函数可以将多帧图像序列编码为 WebP 动画文件。底层依赖 libwebp 库执行实际的 WebP 编码操作。

### 核心功能

- 支持有损（Lossy）和无损（Lossless）两种压缩模式
- 支持可配置的质量/压缩力度参数（0.0 - 100.0）
- 支持静态图像编码和多帧动画编码
- 支持从 `SkPixmap`、`SkImage`（包括 GPU 纹理图像）进行编码
- API 设计与 libwebp 原生接口风格对齐

## 架构位置

`SkWebpEncoder` 位于 Skia 编码器子系统中，与 `SkJpegEncoder` 和 `SkPngEncoder` 并列。

```
Skia 编码子系统架构
====================

  应用层 (Application)
        |
        v
  SkWebpEncoder (公共 API 命名空间)
        |
        +---> Encode()          静态图像编码
        |
        +---> EncodeAnimated()  多帧动画编码
        |
        v
  SkEncoder (基类)
        |
        v
  SkWebpEncoderImpl (内部实现)
        |
        v
  libwebp (第三方底层库)
        |
        +---> WebP 有损编码器 (基于 VP8)
        +---> WebP 无损编码器
        +---> WebP Mux (动画容器)
```

与 JPEG 和 PNG 编码器不同，WebP 编码器没有提供 `Make()` 工厂函数来创建增量编码器实例。这是因为 libwebp 的 API 设计不太适合逐行增量编码的模式。对于动画编码，使用了专门的 `EncodeAnimated()` 函数。

## 主要类与结构体

### `SkWebpEncoder::Compression` 枚举

控制 WebP 编码使用的压缩方式。

| 枚举值 | 说明 |
|--------|------|
| `kLossy` | 有损压缩（默认）。基于 VP8 视频编码技术，适合照片和自然场景 |
| `kLossless` | 无损压缩。适合需要精确像素再现的场景，如截图、图标 |

### `SkWebpEncoder::Options` 结构体

```cpp
struct SK_API Options {
    Compression fCompression = Compression::kLossy;  // 压缩模式
    float fQuality = 100.0f;                         // 质量/压缩力度 [0.0, 100.0]
};
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fCompression` | `Compression` | `kLossy` | 压缩模式选择 |
| `fQuality` | `float` | `100.0f` | 质量参数，范围 [0.0, 100.0] |

#### fQuality 参数的双重含义

`fQuality` 参数的语义取决于所选的压缩模式：

| 压缩模式 | fQuality 含义 | 值越低 | 值越高 |
|----------|--------------|--------|--------|
| `kLossy` | 视觉质量 | 质量更低，文件更小 | 质量更高，文件更大 |
| `kLossless` | 压缩力度（编码努力程度） | 压缩更快，文件更大 | 压缩更慢，文件更小 |

这种设计直接映射了 libwebp 原生 API 的行为语义，避免了不必要的抽象层。

## 公共 API 函数

### 一次性编码到流

```cpp
SK_API bool Encode(SkWStream* dst, const SkPixmap& src, const Options& options);
```

将 `SkPixmap` 像素数据编码为 WebP 并写入输出流。

- **参数**:
  - `dst` - 目标输出流
  - `src` - 源像素数据
  - `options` - 编码选项
- **返回值**: 成功返回 `true`，输入无效或不支持时返回 `false`

### 一次性编码到内存

```cpp
SK_API sk_sp<SkData> Encode(const SkPixmap& src, const Options& options);
```

将像素数据编码为 WebP 并返回编码后的字节数据。

- **返回值**: 成功返回包含 WebP 数据的 `sk_sp<SkData>`，失败返回 `nullptr`

### GPU 图像编码

```cpp
SK_API sk_sp<SkData> Encode(GrDirectContext* ctx, const SkImage* img, const Options& options);
```

编码一个 `SkImage` 对象，支持 GPU 纹理图像。对于在 GPU 上下文中创建的纹理图像，必须提供 `GrDirectContext` 以便读回像素数据；对于光栅图像，`ctx` 可传 `nullptr`。

- **返回值**: 成功返回 `sk_sp<SkData>`，像素无法读取或编码失败返回 `nullptr`

### 动画编码

```cpp
SK_API bool EncodeAnimated(SkWStream* dst,
                           SkSpan<const SkEncoder::Frame> src,
                           const Options& options);
```

将多帧图像序列编码为 WebP 动画并写入输出流。这是 Skia 编码器子系统中唯一的动画编码 API。

- **参数**:
  - `dst` - 目标输出流
  - `src` - 帧序列，每帧包含 `SkPixmap` 像素数据和持续时间（毫秒）
  - `options` - 编码选项（对所有帧统一应用）
- **画布尺寸**: 以第一帧的尺寸作为动画画布大小，后续帧必须匹配此尺寸，否则编码将失败
- **返回值**: 成功返回 `true`，输入无效或不支持时返回 `false`

#### `SkEncoder::Frame` 结构体

动画编码中每一帧的数据结构：

```cpp
struct Frame {
    SkPixmap pixmap;  // 帧的像素数据
    int duration;     // 帧持续时间（毫秒）
};
```

#### 动画编码示例

```cpp
// 准备帧数据
std::vector<SkEncoder::Frame> frames;
frames.push_back({pixmap1, 100});  // 第 1 帧，显示 100ms
frames.push_back({pixmap2, 200});  // 第 2 帧，显示 200ms
frames.push_back({pixmap3, 100});  // 第 3 帧，显示 100ms

// 编码为动画 WebP
SkWebpEncoder::Options options;
options.fCompression = SkWebpEncoder::Compression::kLossy;
options.fQuality = 80.0f;

SkDynamicMemoryWStream stream;
bool success = SkWebpEncoder::EncodeAnimated(&stream, frames, options);
```

> 注意：当前 API 不支持设置背景色、循环次数限制以及为每帧单独配置有损/无损模式等 libwebp 高级特性。这些功能在未来按需添加。

## 内部实现细节

### 编码流程（静态图像）

1. **输入验证**: 验证 `SkPixmap` 的颜色类型和尺寸是否有效
2. **像素格式转换**: 将 Skia 内部像素格式转换为 libwebp 期望的格式
3. **WebP 编码配置**: 根据 `Options` 设置 libwebp 的 `WebPConfig` 结构
4. **调用 libwebp**: 执行实际的 WebP 编码（VP8 有损或无损算法）
5. **输出写入**: 将编码结果写入目标流

### 编码流程（动画）

1. **画布尺寸确定**: 从第一帧提取画布尺寸
2. **帧尺寸验证**: 确认所有帧与画布尺寸一致
3. **WebP Mux 初始化**: 创建动画容器
4. **逐帧编码**: 使用 `Options` 中的统一参数编码每一帧
5. **容器封装**: 将所有编码帧组装为动画 WebP 文件
6. **输出写入**: 将完整的动画 WebP 数据写入目标流

### 禁用构建支持

与其他编码器一致，`SkWebpEncoder_none.cpp` 提供了所有 API 的桩实现。当 WebP 编码未在构建中启用时，所有函数将返回失败。

### 无增量编码器

与 JPEG 和 PNG 编码器不同，`SkWebpEncoder` 没有提供 `Make()` 工厂函数。这反映了 libwebp 的 API 设计特点——WebP 编码更适合一次性处理整个图像，而非逐行增量编码。

## 依赖关系

### 头文件依赖

| 依赖 | 说明 |
|------|------|
| `include/core/SkRefCnt.h` | 引用计数智能指针 `sk_sp` |
| `include/core/SkSpan.h` | `SkSpan` 容器视图（用于帧序列参数） |
| `include/encode/SkEncoder.h` | 编码器基类和 `Frame` 结构体定义 |
| `include/private/base/SkAPI.h` | `SK_API` 导出宏定义 |

### 前向声明依赖

| 类型 | 说明 |
|------|------|
| `SkPixmap` | 光栅像素数据视图 |
| `SkWStream` | 可写流抽象接口 |
| `SkData` | 不可变二进制数据容器 |
| `GrDirectContext` | GPU 上下文（Ganesh 后端） |
| `SkImage` | 图像对象（可能是 GPU 支持的） |
| `skcms_ICCProfile` | ICC 色彩配置文件 |

### 第三方库依赖

- **libwebp**: WebP 编码/解码库，包含：
  - `libwebp` 核心编码器（VP8 有损 / 无损）
  - `libwebpmux` 动画容器封装

## 设计模式与设计决策

### 压缩模式枚举而非布尔标志

使用 `Compression` 枚举（`kLossy` / `kLossless`）而非简单的布尔值来控制压缩模式，这提供了更好的可读性和类型安全。如果未来需要添加新的压缩模式（如混合模式），枚举可以方便地扩展。

### fQuality 的双重语义

`fQuality` 在有损和无损模式下具有不同的含义。这种设计直接映射了 libwebp 原生 API 的行为：
- 有损模式：质量 = 视觉保真度
- 无损模式：质量 = 编码努力程度

虽然这增加了 API 的认知负担，但避免了引入额外的参数或不必要的抽象。

### 统一的 Options 结构体

与 `SkJpegEncoder::Options` 和 `SkPngEncoder::Options` 保持一致的设计风格，所有配置通过单个 `Options` 结构体传递，字段均有合理的默认值。这使得最简单的用法只需 `SkWebpEncoder::Options{}` 即可。

### 动画编码的简化设计

`EncodeAnimated()` 当前不支持 libwebp 的一些高级动画特性（背景色、循环限制、逐帧压缩模式），这是有意为之的简化设计，遵循 YAGNI（You Aren't Gonna Need It）原则。注释中明确表示这些功能可以在需要时后续添加。

### SK_API 导出标记

`Options` 结构体本身带有 `SK_API` 标记，这与 JPEG 和 PNG 编码器的 `Options` 不同。这可能是因为 WebP 的 `Options` 结构体在某些平台上需要作为公共符号导出，以支持跨动态库边界的传递。

### 命名空间 API 模式

与其他编码器保持一致，使用命名空间自由函数而非类方法。这种模式：
- 简化了对象生命周期管理
- 避免了不必要的状态持有
- 提供了清晰的函数式 API 风格

## 性能考量

### 有损 vs 无损的权衡

| 压缩模式 | 编码速度 | 解码速度 | 文件大小 | 适用场景 |
|----------|----------|----------|----------|----------|
| `kLossy` | 较快 | 快 | 小 | 照片、自然场景 |
| `kLossless` | 较慢 | 较慢 | 中等 | 截图、图标、精确像素 |

### 质量参数调优建议

**有损模式（kLossy）**：
- `fQuality = 75-85`: 大多数场景的最佳平衡点，视觉质量接近原图
- `fQuality = 50-75`: 适用于缩略图或带宽敏感场景
- `fQuality < 50`: 明显的压缩伪影，仅用于极端压缩需求
- `fQuality = 100`: 最高质量但文件较大，通常不必要

**无损模式（kLossless）**：
- `fQuality = 0`: 最快编码，文件较大
- `fQuality = 75`: 合理的编码速度和压缩比平衡
- `fQuality = 100`: 最慢编码但文件最小

### 动画编码性能

- 动画 WebP 编码需要逐帧编码并封装，帧数越多编码时间越长
- 所有帧必须与画布尺寸一致，不支持帧偏移优化
- 所有帧使用相同的 `Options` 配置，无法对不同帧采用不同策略
- 对于大量帧的动画，编码过程中的内存消耗可能较高

### WebP vs JPEG vs PNG 对比

| 特性 | WebP | JPEG | PNG |
|------|------|------|-----|
| 有损压缩 | 支持（通常比 JPEG 小 25-34%） | 支持 | 不支持 |
| 无损压缩 | 支持（通常比 PNG 小 26%） | 不支持 | 支持 |
| Alpha 通道 | 原生支持 | 不支持 | 原生支持 |
| 动画 | 支持 | 不支持 | 不支持 |
| 编码速度 | 较慢 | 快 | 中等 |
| 浏览器兼容性 | 广泛 | 通用 | 通用 |

### GPU 图像读回

与其他编码器相同，从 GPU 纹理编码 WebP 需要同步读回像素数据到 CPU 内存。建议在非关键渲染路径上执行此操作以避免 GPU 管线停顿。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/encode/SkWebpEncoder.h` | 公共 API 头文件（本文件） |
| `include/encode/SkEncoder.h` | 编码器基类定义，包含 `Frame` 结构体 |
| `src/encode/SkWebpEncoderImpl.cpp` | WebP 编码器内部实现 |
| `src/encode/SkWebpEncoder_none.cpp` | WebP 编码功能禁用时的桩实现 |
| `include/encode/SkJpegEncoder.h` | JPEG 编码器公共 API |
| `include/encode/SkPngEncoder.h` | PNG 编码器公共 API |
| `include/core/SkPixmap.h` | 像素数据视图 |
| `include/core/SkSpan.h` | 容器视图模板 |
