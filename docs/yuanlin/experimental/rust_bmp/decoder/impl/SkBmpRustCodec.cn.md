# SkBmpRustCodec

> 源文件：experimental/rust_bmp/decoder/impl/SkBmpRustCodec.h, experimental/rust_bmp/decoder/impl/SkBmpRustCodec.cpp

## 概述

`SkBmpRustCodec` 是 Skia 中基于 Rust 实现的完整 BMP 图像解码器类。该类继承自 `SkCodec` 基类，提供了 BMP 格式图像的完整解码能力，包括全量解码和增量解码两种模式。它结合了 Rust 的 `image` crate 进行 BMP 解压缩和解码，以及 Skia 的 `SkSwizzler` 和 `skcms_Transform` 进行像素格式转换和色彩空间变换，展现了 Rust 和 C++ 混合编程在图像处理领域的实践应用。

## 架构位置

`SkBmpRustCodec` 在 Skia 编解码器体系中的位置：

- 位于 `experimental/rust_bmp/decoder/impl/` 目录
- 继承自 `SkCodec` 基类，实现标准的编解码器接口
- 依赖 Rust FFI 层 (`rust_bmp::Reader`) 进行实际的图像数据解码
- 使用 `SkSwizzler` 进行像素格式转换（如 RGB 到 RGBA）
- 使用 `skcms_Transform` 进行色彩空间转换
- 通过 `SkStreamAdapter` 桥接 C++ 流和 Rust 读取器
- 支持 ICC 色彩配置文件解析

该类是 Skia 编解码器插件体系的一部分，可通过 `SkBmpRustDecoder::Decoder()` 注册到编解码器工厂。

## 主要类与结构体

### SkBmpRustCodec 类

**核心成员变量**：
```cpp
rust::Box<rust_bmp::Reader> fReader;              // Rust 实现的解码器核心
std::unique_ptr<SkStream> fPrivStream;            // 私有流对象（不传递给父类）
std::unique_ptr<SkSwizzler> fSwizzler;            // 像素格式转换器
std::unique_ptr<uint32_t[]> fXformBuffer;         // 色彩变换缓冲区
std::optional<DecodingState> fIncrementalDecodingState; // 增量解码状态
```

**静态工厂方法**：
```cpp
static std::unique_ptr<SkBmpRustCodec> MakeFromStream(
    std::unique_ptr<SkStream>,
    Result*
);
```
从流创建解码器实例，执行元数据解析和验证。

### DecodingState 结构体

用于维护增量解码的内部状态：
```cpp
struct DecodingState {
    SkSpan<uint8_t> fDst;           // 目标缓冲区
    size_t fDstRowStride;           // 目标行跨度
    int fTotalRowsDecoded = 0;      // 已解码的总行数
};
```

### 枚举映射

**rust_bmp::BmpColor 到 SkEncodedInfo::Color**：
- `RGB` → `kRGB_Color`
- `RGBA` → `kRGBA_Color`
- `BGR` → `kBGR_Color`
- `BGRA` → `kBGRA_Color`

**rust_bmp::BmpAlpha 到 SkEncodedInfo::Alpha**：
- `Opaque` → `kOpaque_Alpha`
- `Unpremul` → `kUnpremul_Alpha`

**rust_bmp::DecodingResult 到 SkCodec::Result**：
- `Success` → `kSuccess`
- `FormatError` → `kErrorInInput`
- `ParameterError` → `kInvalidParameters`
- `UnsupportedFeature` → `kUnimplemented`
- `IncompleteInput` → `kIncompleteInput`
- `MemoryError` → `kInternalError`

## 公共 API 函数

### MakeFromStream
**功能**：从流创建 BMP 解码器实例
- **参数**：
  - `stream`: 输入流的唯一指针
  - `result`: 输出参数，返回创建结果
- **返回值**：`SkBmpRustCodec` 智能指针，失败时返回 nullptr
- **流程**：
  1. 创建 `SkStreamAdapter` 桥接 C++ 流到 Rust
  2. 调用 Rust 的 `rust_bmp::new_reader()` 创建解码器
  3. 读取并验证图像元数据
  4. 提取尺寸、颜色格式、透明度信息
  5. 解析 ICC 色彩配置文件（如果存在）
  6. 执行整数溢出检查确保内存安全
  7. 构造并返回解码器实例

### 析构函数
```cpp
~SkBmpRustCodec() override;
```
使用默认析构，通过智能指针自动清理资源。

## 保护和私有方法

### 元数据查询

**onGetEncodedFormat()**
```cpp
SkEncodedImageFormat onGetEncodedFormat() const override
```
返回 `SkEncodedImageFormat::kBMP`，标识格式类型。

**onGetFrameInfo()**
```cpp
bool onGetFrameInfo(int index, FrameInfo* info) const override
```
获取帧信息，BMP 为单帧图像，仅支持 index=0。

**getEncodedData()**
```cpp
sk_sp<const SkData> getEncodedData() const override
```
返回原始编码数据，优先使用流的 `getData()`，否则复制整个流。

### 流控制

**onRewind()**
```cpp
bool onRewind() override
```
重置解码器状态，重新创建 Rust Reader，清除增量解码状态。

### 解码核心

**onGetPixels()**
```cpp
Result onGetPixels(const SkImageInfo& info, void* dst,
                   size_t dstRowStride, const Options& options,
                   int* rowsDecoded) override
```
执行全量解码，一次性解码整个图像。

**performFullDecode()**
```cpp
Result performFullDecode(const SkImageInfo& dstInfo,
                        void* dst, size_t dstRowStride)
```
实际的全量解码实现：
1. 重置 Rust 解码器状态
2. 调用 `read_image_data()` 读取所有图像数据
3. 通过 `get_next_rows()` 获取解码后的像素数据
4. 逐行执行像素格式转换（swizzle）

### 增量解码

**onSupportsIncrementalDecode()**
```cpp
bool onSupportsIncrementalDecode(const SkImageInfo&) override
```
返回 `true`，表示支持增量解码。

**onStartIncrementalDecode()**
```cpp
Result onStartIncrementalDecode(const SkImageInfo& dstInfo,
                                void* dst, size_t dstRowBytes,
                                const Options&) override
```
初始化增量解码：
1. 初始化 swizzler
2. 重置 Rust 解码器状态
3. 设置目标缓冲区信息
4. 保存解码状态到 `fIncrementalDecodingState`

**onIncrementalDecode()**
```cpp
Result onIncrementalDecode(int* rowsDecoded) override
```
执行增量解码步骤，返回 `kIncompleteInput` 表示需要更多数据，返回 `kSuccess` 表示完成。

**incrementalDecode()**
```cpp
Result incrementalDecode(DecodingState& state, int* rowsDecoded)
```
增量解码的实际实现：
1. 调用 `read_image_data()` 尝试读取更多数据
2. 通过 `get_next_rows()` 获取新解码的行
3. 将新解码的行复制到目标缓冲区的正确位置
4. 更新已解码行计数
5. 根据数据完整性返回相应状态

### 辅助方法

**initializeSwizzler()**
```cpp
Result initializeSwizzler(const SkImageInfo& dstInfo,
                         const Options& opts)
```
创建并配置 `SkSwizzler` 对象：
- 如果需要色彩空间转换，分配转换缓冲区
- 调整 swizzler 的色彩类型和透明度类型
- 验证目标格式的支持性

**swizzleRow()**
```cpp
void swizzleRow(const uint8_t* srcRow, void* dstRow)
```
转换单行像素数据：
- 如果需要色彩空间转换，先 swizzle 到临时缓冲区，再应用色彩变换
- 否则直接 swizzle 到目标缓冲区

## 内部实现细节

### 流管理策略

该类采用私有流管理策略，不将流传递给 `SkCodec` 父类：
```cpp
SkCodec(std::move(encodedInfo), skcms_PixelFormat_RGB_888,
        /* stream = */ nullptr)
```

原因是避免父类对流的不必要 rewind 操作，这会导致重新读取整个流数据。流由 `fPrivStream` 成员独立管理。

### 类型安全的枚举映射

使用 `static_assert` 在编译时验证 Rust 和 C++ 枚举值的对应关系：
```cpp
static_assert(static_cast<int>(rust_bmp::BmpColor::RGB) ==
              static_cast<int>(SkEncodedInfo::kRGB_Color),
              "BmpColor::RGB must match SkEncodedInfo::kRGB_Color");
```

这确保了类型转换的安全性，避免运行时错误。

### 内存安全检查

在 `MakeFromStream()` 中执行严格的整数溢出检查：
```cpp
SkSafeMath safe;
size_t srcRowBytes = safe.mul(safe.castTo<size_t>(width), bytesPerPixel);
(void)safe.mul(safe.castTo<size_t>(height), srcRowBytes);
if (!safe.ok()) {
    *result = kInternalError;
    return nullptr;
}
```

### 增量解码行跟踪

Rust 侧的 `Reader` 维护解码进度，每次调用 `get_next_rows()` 只返回新解码的行：
```cpp
rust_bmp::DecodedRowsInfo rowsInfo = fReader->get_next_rows(imageData);
const uint32_t dstRowStart = rowsInfo.dst_row_start;
const uint32_t rowCount = rowsInfo.row_count;
```

这避免了 C++ 侧重复处理已解码的行。

### 行顺序处理

BMP 格式支持自顶向下和自底向上两种行顺序，但 Rust 的 `image` crate 内部已处理这一差异，始终返回逻辑顺序（自顶向下）的数据，C++ 侧无需再次翻转。

## 依赖关系

**Skia 核心依赖**：
- `include/codec/SkCodec.h` - 编解码器基类
- `include/core/SkImageInfo.h` - 图像信息描述
- `include/core/SkStream.h` - 流抽象
- `include/private/SkEncodedInfo.h` - 编码信息
- `src/codec/SkSwizzler.h` - 像素格式转换

**Rust 互操作依赖**：
- `experimental/rust_bmp/ffi/FFI.rs.h` - Rust FFI 接口
- `rust/common/SkStreamAdapter.h` - 流适配器
- `rust/common/SpanUtils.h` - Span 工具
- `third_party/rust/cxx/v1/cxx.h` - cxx crate 互操作库

**色彩管理依赖**：
- `skcms` - Skia 色彩管理系统

**辅助依赖**：
- `src/base/SkSafeMath.h` - 安全的整数运算
- `include/private/base/SkAssert.h` - 断言宏
- `include/private/base/SkTemplates.h` - 模板工具

## 设计模式与设计决策

### 适配器模式
`SkStreamAdapter` 作为适配器，将 Skia 的 `SkStream` 接口适配到 Rust 的 IO trait。

### 外观模式
该类为 Rust 解码器提供 Skia 风格的外观，隐藏 FFI 调用的复杂性。

### 策略模式
通过 `SkSwizzler` 抽象像素格式转换策略，支持多种颜色类型转换。

### 状态模式
`DecodingState` 封装增量解码的状态，支持暂停和恢复。

### 关键设计决策

**1. 私有流管理**
不将流传递给父类，避免不必要的 rewind 操作，这是针对流式解码场景的性能优化。

**2. 延迟元数据加载**
支持流式场景下的元数据延迟加载，在数据不完整时返回 `kIncompleteInput`。

**3. 增量解码支持**
完整实现增量解码，支持网络流或大文件的渐进式加载。

**4. 类型安全的 FFI**
使用 `cxx` crate 而非传统的 C FFI，提供类型安全和内存安全保证。

**5. 零拷贝数据传递**
通过 `rust::Slice` 在 FFI 边界传递数据，避免不必要的内存复制。

**6. 行顺序规范化**
将 BMP 的行顺序处理逻辑封装在 Rust 侧，简化 C++ 侧的实现。

## 性能考量

### 内存分配优化

**转换缓冲区**：
- `fXformBuffer` 仅在需要色彩空间转换时分配
- 按行复用，避免为整个图像分配大型临时缓冲区

**流复制避免**：
- 优先使用 `fPrivStream->getData()` 获取零拷贝的数据视图
- 仅在必要时才通过 `duplicate()` 和 `MakeFromStream()` 复制数据

### FFI 开销最小化

**批量操作**：
- `get_next_rows()` 一次返回多行数据，减少 FFI 调用次数
- 全量解码时一次性读取所有数据

**零拷贝传递**：
- 使用 `rust::Slice` 传递指针和长度，不复制像素数据
- Rust 侧数据直接暴露给 C++ 侧使用

### 增量解码性能

**渐进式解码**：
- 支持边下载边解码，降低首次显示延迟
- 每次调用处理新到达的数据，不重复处理已解码部分

**状态保持**：
- 通过 `DecodingState` 保持解码进度，避免重复初始化

### 整数溢出保护

使用 `SkSafeMath` 进行所有尺寸计算，防止整数溢出导致的内存安全问题，开销极小但安全性显著提升。

### 性能瓶颈

1. **像素格式转换**：`SkSwizzler` 的逐行转换是主要性能瓶颈
2. **色彩空间转换**：当需要 ICC 色彩配置文件转换时，`skcms_Transform` 会增加显著开销
3. **流 IO**：非内存流的读取速度受 IO 性能限制

### 优化建议

1. **SIMD 优化**：`SkSwizzler` 已利用 SIMD，无需额外优化
2. **多线程解码**：考虑在 Rust 侧实现多线程解码，对大图像有显著提升
3. **缓存解码结果**：对于重复解码同一图像的场景，考虑缓存解码结果
4. **内存池**：为 `fXformBuffer` 使用内存池，避免频繁分配释放

## 相关文件

**接口定义**：
- `experimental/rust_bmp/decoder/SkBmpRustDecoder.h` - 公共接口
- `include/codec/SkCodec.h` - 编解码器基类接口

**Rust 实现**：
- `experimental/rust_bmp/ffi/FFI.rs.h` - FFI 接口定义
- `experimental/rust_bmp/src/*.rs` - Rust 侧实现（推测）

**辅助工具**：
- `rust/common/SkStreamAdapter.h` - 流适配器
- `src/codec/SkSwizzler.h` - 像素格式转换器

**测试文件**：
- `tests/CodecTest.cpp` - 编解码器测试套件
- `tests/BmpRustTest.cpp` - BMP Rust 解码器专项测试（推测）

**构建配置**：
- `BUILD.gn` - GN 构建配置
- `Cargo.toml` - Rust crate 配置

**参考实现**：
- `src/codec/SkBmpCodec.h` - Skia 原生 BMP 解码器（C++ 实现）
- `src/codec/SkPngCodec.h` - PNG 解码器（架构参考）
