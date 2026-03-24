# SkImageGenerator_FromEncoded - 编码图像生成器

> 源文件: `src/codec/SkImageGenerator_FromEncoded.cpp`

## 概述

`SkImageGenerator_FromEncoded.cpp` 实现了从编码图像数据（如 JPEG、PNG、WebP 等）创建 `SkImageGenerator` 和延迟解码 `SkImage` 的功能。该文件提供了三个核心入口点：`SkImageGenerators::MakeFromEncoded`（创建图像生成器）、`SkImages::DeferredFromEncodedData`（从编码数据创建延迟解码图像）以及 `SkCodecs::DeferredImage`（从已有解码器创建延迟图像）。它还支持通过全局工厂函数自定义图像生成器的创建行为。

## 架构位置

该文件位于 `src/codec/` 目录下，是 Skia 图像解码管线的入口层。它连接了编码数据（`SkData`）、解码器（`SkCodec`）和图像生成器（`SkImageGenerator`）三者之间的关系。通过 `SkCodecImageGenerator` 桥接解码器和图像生成器接口，实现了延迟解码（deferred decoding）模式。

## 主要类与结构体

该文件不定义新的类，而是实现了以下命名空间中的函数。

## 公共 API 函数

### `SkGraphics::SetImageGeneratorFromEncodedDataFactory(factory)`
设置全局的图像生成器工厂函数。当设置后，`MakeFromEncoded` 会优先使用该工厂创建生成器。返回之前的工厂函数指针。

### `SkImageGenerators::MakeFromEncoded(sk_sp<const SkData>, optional<SkAlphaType>)`
从编码数据创建 `SkImageGenerator`。
- 如果数据为空或 alpha 类型为 `kOpaque`，返回 `nullptr`
- 优先使用全局工厂函数，失败时回退到 `SkCodecImageGenerator::MakeFromEncodedCodec`

### `SkImages::DeferredFromEncodedData(sk_sp<const SkData>, optional<SkAlphaType>)`
从编码数据创建延迟解码的 `SkImage`。内部调用 `MakeFromEncoded` 后通过 `DeferredFromGenerator` 包装为图像。

### `SkCodecs::DeferredImage(unique_ptr<SkCodec>, optional<SkAlphaType>)`
从已有的 `SkCodec` 实例创建延迟解码的 `SkImage`。通过 `SkCodecImageGenerator::MakeFromCodec` 创建生成器。

## 内部实现细节

1. **全局工厂模式**: `gFactory` 是一个全局静态变量（`SkGraphics::ImageGeneratorFromEncodedDataFactory` 类型），允许客户端在运行时替换默认的图像生成器创建逻辑。`SetImageGeneratorFromEncodedDataFactory` 返回之前的工厂函数，支持工厂链式替换。

2. **延迟解码**: 图像数据不会立即解码，而是在首次需要像素时才触发解码，节省内存和启动时间。`DeferredFromGenerator` 和 `DeferredFromEncodedData` 均利用此机制。

3. **空数据保护**: 所有入口函数都对空数据进行了检查。`MakeFromEncoded` 检查 `!data`，`DeferredFromEncodedData` 额外检查 `encoded->empty()`，防止无效输入传递到解码器。

4. **alpha 类型验证**: `kOpaque` alpha 类型被视为无效输入并返回 `nullptr`。这是因为编码数据的实际 alpha 类型应由解码器在解析图像头时确定，强制指定 opaque 可能导致数据不一致。alpha 参数通过 `std::optional<SkAlphaType>` 传递，允许不指定。

5. **工厂优先级**: `MakeFromEncoded` 中，全局工厂函数的返回值优先。只有当全局工厂未设置（`gFactory` 为 nullptr）或工厂函数返回 nullptr 时，才回退到基于 `SkCodecImageGenerator` 的默认实现。

6. **三命名空间入口**:
   - `SkImageGenerators::MakeFromEncoded`: 最底层，返回 `SkImageGenerator`
   - `SkImages::DeferredFromEncodedData`: 中间层，从编码数据到延迟图像
   - `SkCodecs::DeferredImage`: 从已有 codec 实例到延迟图像，跳过编码数据解析

## 依赖关系

- `include/codec/SkCodec.h`: 图像解码器基类
- `include/core/SkImageGenerator.h`: 图像生成器基类
- `include/core/SkImage.h`: 图像接口
- `include/core/SkGraphics.h`: 全局工厂设置
- `src/codec/SkCodecImageGenerator.h`: 基于 codec 的图像生成器实现
- `src/image/SkImageGeneratorPriv.h`: 图像生成器内部接口

## 设计模式与设计决策

1. **策略模式**: 通过全局工厂函数允许运行时替换图像生成器的创建策略。这使得嵌入 Skia 的应用（如 Chromium）可以提供自定义的图像解码实现。

2. **延迟初始化**: 延迟解码模式推迟了昂贵的像素解码操作，仅在图像首次被绘制或像素被请求时才执行解码。

3. **命名空间组织**: 功能按 `SkImageGenerators`、`SkImages`、`SkCodecs` 三个命名空间组织，分别对应生成器层、图像层和编解码器层，各司其职。

4. **const 数据语义**: 所有函数接受 `sk_sp<const SkData>`，明确表示编码数据在整个生命周期内不会被修改。

## 性能考量

- **延迟解码**: 避免了不必要的图像解码操作
- **零拷贝数据传递**: `sk_sp<const SkData>` 通过 `std::move` 传递，避免引用计数操作
- **工厂回退机制**: 全局工厂失败时自动回退到默认实现，确保可用性

## 相关文件

- `src/codec/SkCodecImageGenerator.h`: 将 SkCodec 包装为 SkImageGenerator，实际的延迟解码逻辑
- `src/codec/SkCodecImageGenerator.cpp`: SkCodecImageGenerator 的实现
- `include/core/SkImageGenerator.h`: 图像生成器基类，定义了 `onGetPixels` 等虚函数接口
- `include/core/SkImage.h`: 图像接口，`DeferredFromGenerator` 方法在此声明
- `include/codec/SkCodec.h`: 图像解码器基类，提供实际的格式解码能力
- `include/core/SkGraphics.h`: 包含 `SetImageGeneratorFromEncodedDataFactory` 声明
- `src/image/SkImageGeneratorPriv.h`: 图像生成器私有接口，提供 `DeferredFromGenerator` 的内部实现
