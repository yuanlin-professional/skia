# DawnCaps

> 源文件
> - src/gpu/graphite/dawn/DawnCaps.h
> - src/gpu/graphite/dawn/DawnCaps.cpp

## 概述

`DawnCaps` 是 Skia Graphite 中针对 WebGPU/Dawn 后端的能力查询类,继承自 `Caps` 基类。该类负责初始化和管理 Dawn 设备的硬件和软件能力信息,包括纹理格式支持、着色器特性、内存限制、扩展功能等。它是 Graphite 适配不同 GPU 硬件和浏览器环境的核心组件,为资源创建、管线编译、渲染通道配置提供能力查询接口。

`DawnCaps` 的主要职责包括:初始化格式支持表(31 种纹理格式)、配置着色器能力、查询设备限制、生成管线和资源的唯一键、处理平台特定扩展(MSAA Render To Single Sampled、Transient Attachments、Load Resolve Texture 等)、适配 Emscripten 和原生 Dawn 的差异。

## 架构位置

`DawnCaps` 位于 Skia Graphite 的 Dawn 后端能力层,在架构中的位置如下:

```
skgpu::graphite
├── Caps (基类 - 跨后端能力抽象)
├── SharedContext (使用 Caps 查询能力)
└── dawn/
    ├── DawnCaps (Dawn 能力查询)
    ├── DawnSharedContext (持有 DawnCaps)
    ├── DawnResourceProvider (使用 DawnCaps)
    └── DawnGraphicsPipeline (使用 DawnCaps)
```

`DawnCaps` 在系统初始化时由 `DawnSharedContext` 创建,之后被所有 Dawn 后端组件共享使用。它是 Graphite 抽象层与 Dawn 具体实现之间的桥梁。

## 主要类与结构体

### DawnCaps 类

```cpp
class DawnCaps final : public Caps {
public:
    DawnCaps(const DawnBackendContext&, const ContextOptions&);
    ~DawnCaps() override;

    // Dawn 特定能力查询
    bool supportsHalfPrecision() const { return fSupportsHalfPrecision; }
    bool useAsyncPipelineCreation() const { return fUseAsyncPipelineCreation; }
    bool allowScopedErrorChecks() const { return fAllowScopedErrorChecks; }
    std::optional<wgpu::LoadOp> resolveTextureLoadOp() const;
    bool supportsPartialLoadResolve() const;
    bool supportsRenderPassRenderArea() const;
    bool supportsCommandBufferTimestamps() const;
    bool emulateLoadStoreResolve() const;

    // 管线键生成
    UniqueKey makeGraphicsPipelineKey(const GraphicsPipelineDesc&,
                                      const RenderPassDesc&) const override;
    UniqueKey makeComputePipelineKey(const ComputePipelineDesc&) const override;
    uint32_t getRenderPassDescKeyForPipeline(const RenderPassDesc&,
                                             bool additionalFlag = false) const;

    // 纹理信息相关
    SkISize getDepthAttachmentDimensions(const TextureInfo&,
                                         const SkISize colorAttachmentDimensions) const override;
    ImmutableSamplerInfo getImmutableSamplerInfo(const TextureInfo&) const override;
    void buildKeyForTexture(SkISize, const TextureInfo&, ResourceType,
                           GraphiteResourceKey*) const override;

private:
    struct FormatInfo {
        enum Flags {
            kTexturable_Flag  = 0x01,
            kRenderable_Flag  = 0x02,
            kMSAA_Flag        = 0x04,
            kResolve_Flag     = 0x08,
            kStorage_Flag     = 0x10,
        };
        uint16_t fFlags = 0;
        std::unique_ptr<ColorTypeInfo[]> fColorTypeInfos;
        int fColorTypeInfoCount = 0;
    };

    void initCaps(const DawnBackendContext&, const ContextOptions&);
    void initShaderCaps(const wgpu::Device&);
    void initFormatTable(const wgpu::Device&);

    static constexpr int kFormatCount = 31;
    std::array<FormatInfo, kFormatCount> fFormatTable;

    wgpu::TextureUsage fSupportedTransientAttachmentUsage = wgpu::TextureUsage::None;
    std::optional<wgpu::LoadOp> fSupportedResolveTextureLoadOp;
    bool fSupportsPartialLoadResolve = false;
    bool fSupportsRenderPassRenderArea = false;
    bool fEmulateLoadStoreResolve = false;
    bool fUseAsyncPipelineCreation = true;
    bool fAllowScopedErrorChecks = true;
    bool fSupportsCommandBufferTimestamps = false;
    bool fSupportsHalfPrecision = false;
};
```

### 关键常量和映射

```cpp
// 支持的纹理格式列表(31 种)
static constexpr wgpu::TextureFormat kFormats[] = {
    wgpu::TextureFormat::RGBA8Unorm,
    wgpu::TextureFormat::R8Unorm,
    wgpu::TextureFormat::BGRA8Unorm,
    wgpu::TextureFormat::RGBA16Float,
    wgpu::TextureFormat::RGB10A2Unorm,
    wgpu::TextureFormat::Depth24PlusStencil8,
    // ... 更多格式
};

// 渲染通道描述符键的位域布局
static constexpr int kFormatBits = 8;
static constexpr int kResolveBits = 1;
static constexpr int kDepthStencilNumSamplesOffset = kResolveBits;
static constexpr int kDepthStencilFormatOffset = kDepthStencilNumSamplesOffset + kNumSampleKeyBits;
static constexpr int kColorNumSamplesOffset = kDepthStencilFormatOffset + kFormatBits;
static constexpr int kColorFormatOffset = kColorNumSamplesOffset + kNumSampleKeyBits;
static constexpr int kAdditionalFlagOffset = kColorFormatOffset + kFormatBits;
```

## 公共 API 函数

### 能力查询

```cpp
bool supportsHalfPrecision() const
```
查询设备是否支持 FP16(半精度浮点)着色器。依赖 `wgpu::FeatureName::ShaderF16`。

```cpp
std::optional<wgpu::LoadOp> resolveTextureLoadOp() const
```
返回设备支持的 resolve texture load 操作,如果支持则为 `wgpu::LoadOp::ExpandResolveTexture`,否则为空。该特性允许在渲染通道中直接从 resolve 纹理加载数据到 MSAA 纹理。

```cpp
bool emulateLoadStoreResolve() const
```
查询是否需要模拟 load/resolve 操作。当设备不支持 partial load resolve 且不支持 transient attachments 时返回 true,此时使用分离的渲染通道模拟,以提高 MSAA 纹理复用率。

### 管线键生成

```cpp
UniqueKey makeGraphicsPipelineKey(const GraphicsPipelineDesc& pipelineDesc,
                                  const RenderPassDesc& renderPassDesc) const
```
为图形管线生成唯一键,包含 4 个 uint32_t:
- `[0]`: RenderStep ID
- `[1]`: Paint Params ID
- `[2]`: RenderPassDesc 键(格式、采样数、load resolve 标志)
- `[3]`: 写入 swizzle 键

```cpp
uint32_t getRenderPassDescKeyForPipeline(const RenderPassDesc& renderPassDesc,
                                         bool additionalFlag = false) const
```
将渲染通道描述符压缩为 32 位键,位域布局:
- [0]: Load resolve 标志(1 bit)
- [1-3]: Depth/Stencil 采样数(3 bits)
- [4-11]: Depth/Stencil 格式(8 bits)
- [12-14]: Color 采样数(3 bits)
- [15-22]: Color 格式(8 bits)
- [23]: 额外标志(1 bit)

### 纹理支持查询

```cpp
std::pair<SkEnumBitMask<TextureUsage>, SkEnumBitMask<SampleCount>>
getTextureSupport(TextureFormat format, Tiling tiling) const
```
查询指定格式和平铺模式的纹理支持情况,返回支持的用途标志和采样数。Dawn 仅支持 Optimal 平铺。

```cpp
TextureInfo onGetDefaultTextureInfo(SkEnumBitMask<TextureUsage> usage,
                                   TextureFormat format,
                                   SampleCount sampleCount,
                                   Mipmapped mipmapped,
                                   Protected,
                                   Discardable discardable) const
```
根据用途和格式创建默认的 `TextureInfo`,将 Graphite 的 `TextureUsage` 映射为 Dawn 的 `wgpu::TextureUsage`,并处理 transient attachments 和 load/store resolve 模拟的特殊情况。

## 内部实现细节

### 格式表初始化

`initFormatTable()` 方法初始化 31 种纹理格式的支持信息,每种格式包含:
- **能力标志**: Texturable, Renderable, MSAA, Resolve, Storage
- **颜色类型映射**: 每种格式可支持多种 `SkColorType`,例如 `RGBA8Unorm` 支持 `kRGBA_8888`, `kBGRA_8888`, `kRGB_888x`
- **Swizzle 映射**: 处理通道重排序,如 `R8Unorm` 作为 `kAlpha_8` 时使用 swizzle `"000r"` (读取) 和 `"a000"` (写入)

关键代码模式:
```cpp
info = &fFormatTable[GetFormatIndex(wgpu::TextureFormat::RGBA8Unorm)];
info->fFlags = FormatInfo::kAllFlags;
info->fColorTypeInfoCount = 3;
info->fColorTypeInfos = std::make_unique<ColorTypeInfo[]>(3);
// 为每个 ColorType 设置转换、标志和 swizzle
```

### 扩展功能检测

代码通过 `wgpu::Device::HasFeature()` 检测扩展并设置相应标志:

```cpp
// MSAA Render To Single Sampled
fMSAARenderToSingleSampledSupport =
    device.HasFeature(wgpu::FeatureName::MSAARenderToSingleSampled);

// Transient Attachments(仅限非 Emscripten)
if (device.HasFeature(wgpu::FeatureName::TransientAttachments)) {
    fSupportedTransientAttachmentUsage = wgpu::TextureUsage::TransientAttachment;
}

// Load Resolve Texture
if (device.HasFeature(wgpu::FeatureName::DawnLoadResolveTexture)) {
    fSupportedResolveTextureLoadOp = wgpu::LoadOp::ExpandResolveTexture;
    fSupportsPartialLoadResolve =
        device.HasFeature(wgpu::FeatureName::DawnPartialLoadResolveTexture);
}
```

### Load/Store Resolve 模拟逻辑

当设备不支持 partial load resolve 且不支持 transient attachments 时,启用模拟模式:

```cpp
if (!fSupportsPartialLoadResolve &&
    fSupportedTransientAttachmentUsage == wgpu::TextureUsage::None) {
    fEmulateLoadStoreResolve = true;
    fDifferentResolveAttachmentSizeSupport = true;
    // 禁用 ExpandResolveTexture 避免重复管线
    fSupportedResolveTextureLoadOp = std::nullopt;
}
```

模拟模式下,MSAA 纹理需要 `TextureBinding` 用途以便采样到 resolve 纹理:
```cpp
if (fEmulateLoadStoreResolve && !TextureFormatIsDepthOrStencil(format)) {
    dawnUsage |= wgpu::TextureUsage::TextureBinding;
}
```

### 着色器能力初始化

`initShaderCaps()` 方法配置 SkSL 编译器能力:

```cpp
// WGSL 不支持无穷大(未来可能通过扩展支持)
shaderCaps->fInfinitySupport = false;

// WGSL 支持片段着色器导数
shaderCaps->fShaderDerivativeSupport = true;

// 双源混合和帧缓冲获取(Feature Gated)
if (device.HasFeature(wgpu::FeatureName::DualSourceBlending)) {
    shaderCaps->fDualSourceBlendingSupport = true;
}
if (device.HasFeature(wgpu::FeatureName::FramebufferFetch)) {
    shaderCaps->fFBFetchSupport = true;
}
```

### 平台差异处理

代码广泛使用条件编译处理 Emscripten 和原生 Dawn 的差异:

```cpp
#if !defined(__EMSCRIPTEN__)
    // 原生 Dawn 特有功能
    fResourceBindingReqs.fUsePushConstantsForIntrinsicConstants =
        limits.maxImmediateSize >= DawnGraphicsPipeline::kIntrinsicUniformSize;
#else
    // Emscripten 限制
    fStorageBufferSupport = false;
#endif
```

关键差异点:
- **SSBO 支持**: Emscripten 悲观假设不支持,原生 Dawn 根据后端类型判断
- **推送常量**: 仅在原生 Dawn 中可用
- **多平面格式**: Emscripten 不支持 `R8BG8Biplanar420Unorm` 等格式
- **时间戳查询**: Emscripten 需要 3.1.48+ 版本

## 依赖关系

### 对外依赖

| 依赖类/模块 | 用途 | 依赖类型 |
|------------|------|---------|
| `Caps` | Graphite 能力基类 | 继承 |
| `wgpu::Device` | 查询 Dawn 设备能力 | 强依赖 |
| `DawnBackendContext` | Dawn 后端上下文信息 | 初始化参数 |
| `ContextOptions` | Graphite 上下文选项 | 初始化参数 |
| `DawnTextureInfo` | Dawn 纹理信息结构体 | 辅助 |
| `GraphiteResourceKey` | 资源键构建 | 辅助 |

### 被依赖关系

- **DawnSharedContext**: 持有 `DawnCaps` 实例
- **DawnResourceProvider**: 使用 `DawnCaps` 查询格式支持和创建资源
- **DawnGraphicsPipeline**: 使用 `DawnCaps` 获取管线配置
- **DawnCommandBuffer**: 使用 `DawnCaps` 查询扩展支持

## 设计模式与设计决策

### 策略模式

`DawnCaps` 实现了策略模式,封装了 Dawn 后端的能力查询策略,与 Vulkan、Metal 等其他后端的 Caps 类并存,由 `SharedContext` 根据运行时后端类型选择。

### 延迟初始化

格式表通过 `std::unique_ptr` 延迟分配 `ColorTypeInfo` 数组,避免不支持的格式占用内存:
```cpp
info->fColorTypeInfoCount = 3;
info->fColorTypeInfos = std::make_unique<ColorTypeInfo[]>(3);
```

### 位域键设计

渲染通道描述符键使用紧凑的位域布局,将多个参数压缩到单个 uint32_t:
- 节省内存和哈希表空间
- 快速比较和哈希计算
- 支持额外标志位的扩展

### 条件编译策略

大量使用 `#if !defined(__EMSCRIPTEN__)` 处理平台差异,优点:
- 清晰分离平台特定代码
- 避免运行时分支开销
- 支持平台特定优化

### 防御性编程

代码包含大量断言和调试检查:
```cpp
SkASSERT(RenderStep::IsValidRenderStepID(rawKeyData[0]));
SkASSERT(!loadFromResolve || this->loadOpAffectsMSAAPipelines());
SkDEBUGFAILF("Unsupported wgpu::TextureFormat: 0x%08X\n", static_cast<uint32_t>(format));
```

## 性能考量

### 格式表查找优化

使用静态数组索引而非哈希表查找格式信息:
```cpp
size_t DawnCaps::GetFormatIndex(wgpu::TextureFormat format) {
    for (size_t i = 0; i < std::size(kFormats); ++i) {
        if (format == kFormats[i]) return i;
    }
    // 调试模式失败,发布模式返回 0
}
```

线性搜索对于 31 个元素是高效的,因为:
- 格式按使用频率排序,常见格式在前
- CPU 缓存友好的顺序访问
- 避免哈希计算开销

### 管线键缓存

生成的管线键被 Graphite 的资源缓存系统使用,避免重复创建相同配置的管线。键的生成是轻量级的位操作,但缓存避免了昂贵的管线编译。

### 条件特性检测

扩展功能在初始化时一次性检测并存储布尔标志:
```cpp
fSupportsHalfPrecision = device.HasFeature(wgpu::FeatureName::ShaderF16);
```

后续查询通过内联访问器直接返回布尔值,避免重复调用 Dawn API。

### 模拟模式权衡

Load/Store Resolve 模拟通过额外的渲染通道换取更好的内存复用:
- **优点**: 减少 MSAA 纹理内存占用,提高移动设备性能
- **缺点**: 增加渲染通道切换开销,需要额外的 blit 操作
- **适用场景**: 不支持 transient attachments 的移动 GPU

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/graphite/Caps.h` | 基类定义 | Graphite 能力抽象接口 |
| `src/gpu/graphite/dawn/DawnSharedContext.h` | 使用者 | 持有 DawnCaps 实例 |
| `src/gpu/graphite/dawn/DawnGraphiteUtils.h` | 辅助工具 | 格式转换和工具函数 |
| `include/gpu/graphite/dawn/DawnBackendContext.h` | 初始化参数 | Dawn 后端上下文 |
| `include/gpu/graphite/dawn/DawnGraphiteTypes.h` | 类型定义 | DawnTextureInfo 等类型 |
| `src/gpu/graphite/GraphiteResourceKey.h` | 键构建 | 资源唯一键系统 |
| `src/sksl/SkSLUtil.h` | 着色器能力 | SkSL 编译器配置 |
| `webgpu/webgpu_cpp.h` | 外部依赖 | WebGPU C++ API |
