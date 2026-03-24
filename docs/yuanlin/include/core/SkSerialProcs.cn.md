# SkSerialProcs

> 源文件: `include/core/SkSerialProcs.h`

## 概述

`SkSerialProcs.h` 定义了 Skia 的自定义序列化与反序列化回调（Proc）机制。通过该文件中定义的 `SkSerialProcs` 和 `SkDeserialProcs` 结构体，客户端可以为 Skia 的 `SkPicture`、`SkImage` 和 `SkTypeface` 对象注入自定义的序列化和反序列化逻辑，从而替代 Skia 的默认行为。

这套机制的典型应用场景包括：
- 自定义图像编码/解码策略（例如使用特定的压缩格式或从远程服务器加载图像）
- 跨进程或网络传输 SkPicture 时的自定义编码
- 字体文件的自定义序列化（例如仅传输字体名称而非完整字体数据）
- 在 GPU 后端中支持 Slug（文本渲染中间表示）的反序列化

## 架构位置

`SkSerialProcs` 在 Skia 的序列化子系统中处于接口层：

```
客户端代码
    │
    ├── SkSerialProcs（序列化回调配置）
    │   └── SkPicture::serialize(const SkSerialProcs&)
    │
    ├── SkDeserialProcs（反序列化回调配置）
    │   └── SkPicture::MakeFromData(data, SkDeserialProcs&)
    │
    └── Skia 内部序列化格式（默认行为）
```

这些回调结构体被传递给 `SkPicture::serialize()` 和 `SkPicture::MakeFromStream()` 等方法，在序列化/反序列化过程中被调用。

## 主要类与结构体

### `SkSerialProcs`（序列化回调集合）

```cpp
struct SK_API SkSerialProcs {
    SkSerialPictureProc  fPictureProc = nullptr;
    void*                fPictureCtx = nullptr;
    SkSerialImageProc    fImageProc = nullptr;
    void*                fImageCtx = nullptr;
    SkSerialTypefaceProc fTypefaceProc = nullptr;
    void*                fTypefaceCtx = nullptr;
};
```

包含三组回调函数及其上下文指针：
- **Picture 序列化**: `fPictureProc` + `fPictureCtx`
- **Image 序列化**: `fImageProc` + `fImageCtx`
- **Typeface 序列化**: `fTypefaceProc` + `fTypefaceCtx`

所有字段默认为 `nullptr`，表示使用 Skia 的默认序列化行为。

### `SkDeserialProcs`（反序列化回调集合）

```cpp
struct SK_API SkDeserialProcs {
    SkDeserialPictureProc        fPictureProc = nullptr;
    void*                        fPictureCtx = nullptr;
    SkDeserialImageProc          fImageProc = nullptr;
    SkDeserialImageFromDataProc  fImageDataProc = nullptr;
    void*                        fImageCtx = nullptr;
    SkSlugProc                   fSlugProc = nullptr;
    void*                        fSlugCtx = nullptr;
    SkDeserialTypefaceStreamProc fTypefaceStreamProc = nullptr;
    void*                        fTypefaceCtx = nullptr;
    bool                         fAllowSkSL = true;
};
```

反序列化结构体比序列化结构体更复杂，包含：
- **Picture 反序列化**: `fPictureProc` + `fPictureCtx`
- **Image 反序列化**: `fImageProc`（基于 void* 数据）和 `fImageDataProc`（基于 `sk_sp<SkData>`）共享 `fImageCtx`
- **Slug 反序列化**: `fSlugProc` + `fSlugCtx`（由 `sktext::gpu::AddDeserialProcs` 设置）
- **Typeface 反序列化**: `fTypefaceStreamProc` + `fTypefaceCtx`
- **SkSL 控制**: `fAllowSkSL` 标志（默认 true），控制是否允许 SkSL 着色器的反序列化

## 公共 API 函数

本文件不包含函数实现，仅定义类型别名和结构体。实际的序列化/反序列化操作由使用这些类型的 API（如 `SkPicture::serialize()`）执行。

### 序列化回调类型

#### `SkSerialPictureProc`
```cpp
using SkSerialPictureProc = sk_sp<const SkData> (*)(SkPicture*, void* ctx);
```
序列化 SkPicture 的回调。返回非空 `SkData` 表示使用自定义序列化结果（即使长度为零），返回 `nullptr` 表示回退到 Skia 默认格式。

#### `SkSerialImageProc`
```cpp
using SkSerialImageProc = sk_sp<const SkData> (*)(SkImage*, void* ctx);
```
序列化 SkImage 的回调。默认行为是以原生格式或 PNG 编码图像。

#### `SkSerialTypefaceProc`
```cpp
using SkSerialTypefaceProc = sk_sp<const SkData> (*)(SkTypeface*, void* ctx);
```
序列化 SkTypeface 的回调。默认使用 Skia 内部格式。

### 反序列化回调类型

#### `SkDeserialPictureProc`
```cpp
using SkDeserialPictureProc = sk_sp<SkPicture> (*)(const void* data, size_t length, void* ctx);
```
从自定义序列化数据中恢复 SkPicture。

#### `SkDeserialImageProc`
```cpp
using SkDeserialImageProc = sk_sp<SkImage> (*)(const void* data, size_t length, void* ctx);
```
从编码数据中恢复 SkImage。返回 `nullptr` 时 Skia 会尝试默认解码。注意：实现必须在回调返回前拷贝所需数据，因为序列化结束后数据缓冲区将被释放。

使用 `SK_LEGACY_DESERIAL_IMAGE_PROC` 宏时，额外接收可选的 `SkAlphaType` 参数。

#### `SkDeserialImageFromDataProc`
```cpp
using SkDeserialImageFromDataProc = sk_sp<SkImage> (*)(sk_sp<SkData>,
                                                        std::optional<SkAlphaType>, void* ctx);
```
当内部实现已拥有 `SkData` 副本时调用的替代回调。接收 `sk_sp<SkData>` 参数，避免不必要的数据拷贝。

#### `SkSlugProc`
```cpp
using SkSlugProc = sk_sp<sktext::gpu::Slug> (*)(SkReadBuffer&, void* ctx);
```
反序列化 Slug 对象的回调。Slug 目前仅在 GPU 后端中可反序列化。客户端不能提供自定义实现，但可以通过 `sktext::gpu::AddDeserialProcs` 启用 Skia 的内置实现。

#### `SkDeserialTypefaceStreamProc` / `SkDeserialTypefaceProc`
```cpp
using SkDeserialTypefaceStreamProc = sk_sp<SkTypeface> (*)(SkStream&, void* ctx);
using SkDeserialTypefaceProc = sk_sp<SkTypeface> (*)(const void* data, size_t length, void* ctx);
```
从流或缓冲区中恢复 SkTypeface。注意：客户端不应复制或持有传入的流。

## 内部实现细节

### 返回类型语义
```cpp
using SkSerialReturnType = sk_sp<const SkData>;
```
所有序列化回调的返回类型统一为 `sk_sp<const SkData>`。返回值的语义设计如下：
- 返回非空 `SkData`（包括零长度）：使用自定义序列化结果
- 返回 `nullptr`：Skia 使用默认序列化行为

这种设计允许客户端选择性地处理部分对象，对不感兴趣的对象返回 `nullptr` 即可回退到默认行为。

### Legacy 反序列化接口兼容

```cpp
#if !defined(SK_LEGACY_DESERIAL_IMAGE_PROC)
using SkDeserialImageProc = sk_sp<SkImage> (*)(const void* data, size_t length, void* ctx);
#else
using SkDeserialImageProc = sk_sp<SkImage> (*)(const void* data, size_t length,
                                                std::optional<SkAlphaType>, void* ctx);
#endif
```
通过条件编译宏 `SK_LEGACY_DESERIAL_IMAGE_PROC` 维护向后兼容性。新版接口移除了 `SkAlphaType` 参数，旧版仍保留。

### `fAllowSkSL` 安全标志
```cpp
bool fAllowSkSL = true;
```
控制是否允许在反序列化过程中执行 SkSL 着色器代码。虽然看起来像布尔标志，但设计注释指出它在概念上可被视为一个"返回布尔值且不接受参数的回调"。默认为 `true`。

## 依赖关系

- **`include/core/SkRefCnt.h`** - 提供 `sk_sp` 智能指针
- **`include/private/base/SkAPI.h`** - `SK_API` 导出宏
- **前向声明**: `SkData`, `SkImage`, `SkPicture`, `SkTypeface`, `SkReadBuffer`, `SkStream`, `SkAlphaType`, `sktext::gpu::Slug`

## 设计模式与设计决策

### 1. 回调 + 上下文指针模式
所有回调都采用 C 风格的函数指针加 `void*` 上下文指针的模式。这种设计比使用 `std::function` 更轻量、ABI 更稳定，且易于跨语言绑定。每个回调都配有独立的上下文指针，允许不同类型的序列化使用不同的状态。

### 2. 选择性覆盖
所有回调默认为 `nullptr`。客户端只需设置关心的回调，其余使用 Skia 默认行为。这是"选择性覆盖"（opt-in override）的经典设计。

### 3. 序列化/反序列化对称设计
`SkSerialProcs` 和 `SkDeserialProcs` 形成对称的序列化/反序列化配对，每种对象类型都有对应的序列化和反序列化回调。

### 4. 双重图像反序列化入口
`SkDeserialProcs` 提供了 `fImageProc`（基于裸指针）和 `fImageDataProc`（基于 `sk_sp<SkData>`）两个入口。后者在内部已有 `SkData` 副本时避免了不必要的数据拷贝。

### 5. 安全考量
`fAllowSkSL` 提供了控制 SkSL 代码执行的能力，这对于处理不可信数据源（如网络传输的 SkPicture）时的安全性至关重要。

## 性能考量

1. **函数指针 vs `std::function`**: 使用函数指针避免了 `std::function` 的堆分配和虚调用开销，在频繁的序列化操作中更高效。

2. **零拷贝反序列化**: `SkDeserialImageFromDataProc` 接收 `sk_sp<SkData>` 参数，避免了数据拷贝。但基于 `void*` 的 `SkDeserialImageProc` 回调需要在返回前拷贝数据。

3. **选择性处理**: `nullptr` 回调直接跳过自定义逻辑，使用 Skia 默认路径，无额外的条件分支开销。

4. **结构体零初始化**: 所有字段使用默认值初始化，无需客户端显式清零。

## 相关文件

- `include/core/SkPicture.h` - SkPicture 序列化的主要使用者
- `include/core/SkImage.h` - SkImage 对象类型
- `include/core/SkTypeface.h` - SkTypeface 对象类型
- `include/core/SkData.h` - 二进制数据容器
- `include/core/SkRefCnt.h` - `sk_sp` 智能指针定义
- `include/core/SkStream.h` - 流接口（Typeface 反序列化使用）
- `src/core/SkReadBuffer.h` - 读取缓冲区（Slug 反序列化使用）
- `include/gpu/ganesh/SkTextureSlug.h` - Slug 相关的 GPU 文本渲染
