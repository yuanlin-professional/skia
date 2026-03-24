# Caps (GPU 能力查询)

> 源文件：[src/gpu/graphite/Caps.h](../../../../src/gpu/graphite/Caps.h)、[src/gpu/graphite/Caps.cpp](../../../../src/gpu/graphite/Caps.cpp)

## 概述

`Caps` 是 Skia Graphite 后端中用于查询 GPU 硬件能力和功能支持情况的核心抽象基类。它封装了后端（Metal、Vulkan、Dawn 等）所支持的纹理格式、采样数、缓冲区对齐需求、混合模式支持、动态状态能力等各种硬件特性信息。子类（如 `MtlCaps`、`VulkanCaps`、`DawnCaps`）负责在初始化时探测具体设备的能力，并填充 `Caps` 提供的字段。

`Caps` 同时管理 `SkSL::ShaderCaps`（着色器语言层面的能力信息）和 `SkCapabilities`（面向公共 API 的能力导出）。通过 `ContextOptions`，客户端也可以覆盖部分运行时参数（如最大纹理尺寸、MSAA 采样数、字体渲染配置等）。

## 架构位置

`Caps` 位于 Graphite 渲染管线的最底层能力抽象层。它被以下模块广泛引用：

- **Context / Recorder**：在创建时持有 `Caps` 实例，用于全局能力查询。
- **ResourceProvider / ResourceCache**：根据能力决定资源格式与创建参数。
- **Pipeline 编译**：通过 `makeGraphicsPipelineKey` / `makeComputePipelineKey` 生成管线缓存键。
- **RenderPassDesc**：利用能力信息选择深度/模板格式和采样数。
- **DrawAtlas / ClipAtlasManager**：查询纹理格式和 atlas 大小限制。

## 主要类与结构体

### `ResourceBindingRequirements`
描述后端资源绑定需求的结构体，包含：
- `fBackendApi`：使用的后端 API 类型（Metal、Vulkan、Dawn 等）。
- `fUniformBufferLayout` / `fStorageBufferLayout`：Uniform 和 Storage Buffer 的内存布局规则（`Layout::kStd140`、`Layout::kStd430`、`Layout::kMetal` 等）。
- `fSeparateTextureAndSamplerBinding`：是否需要分离纹理与采样器绑定（Vulkan/Dawn 需要，Metal 不需要）。
- `fUsePushConstantsForIntrinsicConstants`：是否使用 Push Constants 传递内部常量。
- 各种 set/binding 索引：`fUniformsSetIdx`、`fTextureSamplerSetIdx`、`fInputAttachmentSetIdx` 等。

### `Caps::ColorTypeInfo`
内部结构体，描述特定纹理格式下某一 `SkColorType` 的信息：
- `fColorType`：对应的颜色类型。
- `fTransferColorType`：用于 readPixels/writePixels 时的传输颜色类型。
- `fFlags`：标志位（`kUploadData_Flag`、`kRenderable_Flag`）。
- `fReadSwizzle` / `fWriteSwizzle`：读写时的通道重排信息。

### `Caps` (抽象基类)
核心能力查询类，包含大量的成员变量和虚方法，子类必须实现纯虚方法以适配具体后端。

## 公共 API 函数

### 着色器与能力导出
- `shaderCaps() -> const SkSL::ShaderCaps*`：返回着色器级别的能力描述。
- `capabilities() -> sk_sp<SkCapabilities>`：返回面向公共 API 的能力对象。

### 管线键生成（纯虚）
- `makeGraphicsPipelineKey(GraphicsPipelineDesc, RenderPassDesc) -> UniqueKey`：根据图形管线描述和渲染通道描述生成唯一缓存键。
- `makeComputePipelineKey(ComputePipelineDesc) -> UniqueKey`：根据计算管线描述生成缓存键。
- `extractGraphicsDescs(UniqueKey, ...) -> bool`：从缓存键中反向提取管线描述（默认返回 false）。

### 纹理能力查询
- `isTexturable(TextureInfo, allowMSAA) -> bool`：纹理是否可在着色器中采样。
- `isRenderable(TextureInfo) -> bool`：纹理是否可作为渲染目标。
- `isRenderableWithMSRTSS(TextureInfo) -> bool`：纹理是否支持 MSAA Render-To-Single-Sampled。
- `isCopyableSrc(TextureInfo) / isCopyableDst(TextureInfo) -> bool`：纹理是否可作为复制源/目标。
- `isStorage(TextureInfo) -> bool`：纹理是否可作为计算存储纹理。
- `isSampleCountSupported(TextureFormat, SampleCount) -> bool`：检查特定格式和采样数的支持。

### 默认纹理信息获取
- `getDefaultSampledTextureInfo(SkColorType, Mipmapped, Protected, Renderable) -> TextureInfo`：获取采样纹理的默认配置。
- `getDefaultAttachmentTextureInfo(AttachmentDesc, Protected, Discardable) -> TextureInfo`：获取附件纹理的默认配置。
- `getDefaultCompressedTextureInfo(...)` / `getDefaultStorageTextureInfo(...)`：获取压缩/存储纹理的默认配置。
- `getTextureInfoForSampledCopy(TextureInfo, Mipmapped) -> TextureInfo`：获取用于采样拷贝的纹理配置。

### MSAA 相关
- `avoidMSAA() -> bool`：是否应避免使用 MSAA（由设备问题或客户端选项触发）。
- `msaaRenderToSingleSampledSupport() -> bool`：是否支持 MSAA 渲染到单采样纹理。
- `getCompatibleMSAASampleCount(TextureInfo) -> SampleCount`：获取兼容的 MSAA 采样数。

### 缓冲区与对齐
- `requiredUniformBufferAlignment() -> size_t`：Uniform Buffer 绑定的偏移对齐要求。
- `requiredStorageBufferAlignment() -> size_t`：Storage Buffer 绑定的偏移对齐要求。
- `requiredTransferBufferAlignment() -> size_t`：传输缓冲区复制操作的对齐要求。
- `getAlignedTextureDataRowBytes(rowBytes) -> size_t`：获取对齐后的纹理数据行字节数。

### 混合模式
- `blendEquationSupport() -> BlendEquationSupport`：返回混合方程的硬件支持级别（`kBasic`、`kAdvancedNoncoherent`、`kAdvancedCoherent`）。
- `supportsHardwareAdvancedBlending() -> bool`：是否支持高级混合模式。

### 动态管线状态（Vulkan 相关）
- `useBasicDynamicState() -> bool`：是否使用基础动态状态（深度/模板/图元拓扑等）。
- `useVertexInputDynamicState() -> bool`：是否使用动态顶点输入状态。
- `usePipelineLibraries() -> bool`：是否使用 `VK_EXT_graphics_pipeline_library`。

### 其他重要查询
- `storageBufferSupport() / gradientBufferSupport()`：Storage/Gradient Buffer 支持。
- `computeSupport()`：计算着色器支持。
- `protectedSupport()`：受保护内容支持。
- `semaphoreSupport()`：后端信号量支持。
- `getDstReadStrategy() -> DstReadStrategy`：目标颜色读取策略（Framebuffer Fetch 或纹理拷贝）。
- `getSubRunControl(useSDFTForSmallText) -> SubRunControl`：文本渲染子运行控制参数。

## 内部实现细节

### 初始化流程
`Caps` 的构造函数创建默认的 `ShaderCaps` 和 `SkCapabilities`。子类在各自的 `init()` 方法中探测硬件能力并填充字段，最后调用 `finishInitialization(ContextOptions)` 完成初始化。该方法会：
1. 调用 `fCapabilities->initSkCaps()` 初始化公共能力。
2. 从 `ContextOptions` 读取客户端覆盖参数（MSAA 采样数、着色器错误处理器、字体大小等）。
3. 在测试模式下读取 `ContextOptionsPriv` 中的调试覆盖。

### 纹理支持查询的分层设计
纹理能力查询采用三层分离：
1. **`getTextureUsage(TextureInfo)`**（纯虚）：从具体 TextureInfo 中提取该纹理声明的用途和 Tiling 模式。
2. **`getTextureSupport(TextureFormat, Tiling)`**（纯虚）：查询某格式在特定 Tiling 下支持的用途和采样数。
3. **`isSupported(TextureInfo, test, ...)`**：将上述两者交集后判断是否满足请求的用途。

这种分层设计使得公共 API（`isTexturable`、`isRenderable` 等）只需传入不同的 `test` 标志位即可。

### 深度/模板格式选择
`getDepthStencilFormat()` 采用优先级策略：
- 仅深度：优先 D16 -> D32F -> 组合 D/S 格式。
- 仅模板：优先 S8 -> 组合 D/S 格式。
- 深度+模板：优先 D24_S8 -> D32F_S8（D24_S8 占用更少内存）。

### 默认纹理创建的主动标志添加
`getDefaultTextureInfo()` 在满足条件时会主动添加额外 usage 标志：
- 如果格式支持 MSRTSS 且请求了 kRender，主动添加 `TextureUsage::kMSRTSS`。
- 如果格式支持 HostCopy 且请求了 kCopyDst（且非渲染/非 Protected），主动添加 `TextureUsage::kHostCopy`。

### DstRead 策略
默认实现优先使用 Framebuffer Fetch（如果着色器支持 `fFBFetchSupport`），否则回退到纹理拷贝。

## 依赖关系

### 上游依赖
- `SkSL::ShaderCaps`：着色器语言能力。
- `SkCapabilities`：面向公共 API 的能力导出。
- `ContextOptions`：客户端配置选项。
- `TextureInfo` / `TextureFormat`：纹理格式和信息抽象。
- `ResourceTypes.h`：资源类型枚举（`Layout`、`TextureUsage`、`SampleCount` 等）。

### 下游使用者
- `Context`、`Recorder`、`DrawContext`：全局能力查询。
- `ResourceProvider`：资源创建时根据能力选择参数。
- `RenderPassDesc`：渲染通道描述中查询附件格式。
- `ShaderCodeDictionary`：生成着色器代码时查询能力。
- `BufferManager`：根据对齐要求管理缓冲区。

## 设计模式与设计决策

1. **模板方法模式（Template Method）**：`Caps` 定义了公共查询接口和通用逻辑，子类通过覆盖纯虚函数（`onGetDefaultTextureInfo`、`getTextureSupport`、`getTextureUsage`）提供具体后端实现。

2. **能力位掩码**：使用 `SkEnumBitMask<TextureUsage>` 和 `SkEnumBitMask<SampleCount>` 进行位操作，高效表达和查询多种能力的组合。

3. **配置与能力分离**：通过 `ContextOptions` 允许客户端覆盖部分参数，与硬件实际能力相互独立。例如 `avoidMSAA()` 同时考虑驱动问题和客户端选项。

4. **格式优先级列表**：`getDefaultSampledTextureInfo` 等方法接受 `SkSpan<const TextureFormat>` 参数，按照优先级逐一尝试，第一个支持的格式即为最终选择。

5. **防御性编程**：多处使用 `SkASSERT` 确保调用者遵守前置条件（如 `Discardable::kYes` 仅允许配合特定 usage 使用）。

## 性能考量

- **能力缓存**：`Caps` 在初始化时一次性探测所有能力并缓存到成员变量，后续查询均为 O(1) 常量时间。
- **格式表驱动**：后端子类通常使用格式表（format table）存储每种格式的能力，避免重复计算。
- **MSAA 采样数降级**：`getCompatibleMSAASampleCount` 从最大配置采样数向下逐级查找支持的采样数，确保在不支持高采样数时自动降级。
- **主动标志优化**：在创建默认纹理时主动添加 MSRTSS 和 HostCopy 标志，使纹理在后续使用中无需重新创建即可支持更多操作。

## 相关文件

- `src/gpu/graphite/mtl/MtlCaps.h/.mm`：Metal 后端能力实现。
- `src/gpu/graphite/vk/VulkanCaps.h/.cpp`：Vulkan 后端能力实现。
- `src/gpu/graphite/dawn/DawnCaps.h/.cpp`：Dawn 后端能力实现。
- `include/gpu/graphite/ContextOptions.h`：客户端配置选项。
- `include/gpu/graphite/TextureInfo.h`：纹理信息公共 API。
- `src/gpu/graphite/ResourceTypes.h`：资源类型与枚举定义。
- `src/sksl/SkSLUtil.h`：ShaderCaps 定义。
- `src/gpu/graphite/RenderPassDesc.h`：渲染通道描述。
