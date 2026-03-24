# GrVkUniformHandler

> 源文件
> - `src/gpu/ganesh/vk/GrVkUniformHandler.h`
> - `src/gpu/ganesh/vk/GrVkUniformHandler.cpp`

## 概述

`GrVkUniformHandler` 是 Skia Ganesh 渲染引擎中负责管理 Vulkan 着色器 uniform 变量和采样器的核心类。它继承自 `GrGLSLUniformHandler`，负责计算 uniform 在缓冲区中的偏移量、管理描述符集绑定、决定是否使用 push constants，以及生成着色器 uniform 声明代码。该类遵循 Vulkan 的 std140 和 std430 内存布局规范，确保 CPU 和 GPU 之间的数据对齐一致性。

## 架构位置

在 Ganesh Vulkan 着色器编译管道中，`GrVkUniformHandler` 位于以下位置：

```
GrGLSLUniformHandler (基类)
    └── GrVkUniformHandler (Vulkan 实现)
        └── 被 GrVkPipelineStateBuilder 使用
```

该类在着色器编译阶段由 `GrVkPipelineStateBuilder` 创建，负责收集所有 uniform 和采样器信息，计算内存布局，并生成着色器声明代码。它与 `GrVkDescriptorSetManager` 紧密协作，共同管理描述符集的分配和绑定。

## 主要类与结构体

### GrVkUniformHandler 类

**核心常量**：
```cpp
static const int kUniformsPerBlock = 8;  // 每个块分配的 uniform 数量

// 描述符集索引（绑定顺序很重要）
static constexpr int kUniformBufferDescSet = 0;
static constexpr int kSamplerDescSet = 1;
static constexpr int kInputDescSet = 2;
static constexpr int kDescSetCount = 3;

// 绑定索引
static constexpr int kUniformBinding = 0;
static constexpr int kInputBinding = 0;
```

**内存布局类型**：
```cpp
enum Layout {
    kStd140Layout = 0,  // Uniform Buffer 使用
    kStd430Layout = 1,  // Push Constants 使用
};
static constexpr int kLayoutCount = 2;
```

**成员变量**：
- `UniformInfoArray fUniforms`: uniform 变量列表
- `UniformInfoArray fSamplers`: 采样器列表
- `skia_private::TArray<skgpu::Swizzle> fSamplerSwizzles`: 采样器 swizzle 映射
- `UniformInfo fInputUniform`: Input attachment uniform
- `skgpu::Swizzle fInputSwizzle`: Input attachment swizzle
- `mutable bool fUsePushConstants`: 是否使用 push constants
- `uint32_t fCurrentOffsets[kLayoutCount]`: 当前偏移量（两种布局）

### VkUniformInfo 结构体

```cpp
struct VkUniformInfo : public UniformInfo {
    uint32_t fOffsets[kLayoutCount];  // 两种布局的偏移量
    const GrVkSampler* fImmutableSampler = nullptr;  // 不可变采样器（YCbCr）
};
```

扩展基类 `UniformInfo`，添加 Vulkan 特定的偏移量计算和不可变采样器支持。

## 公共 API 函数

### Uniform 访问方法

**getUniformVariable**
```cpp
const GrShaderVar& getUniformVariable(UniformHandle u) const override;
```
获取指定 uniform 的着色器变量定义。

**getUniformCStr**
```cpp
const char* getUniformCStr(UniformHandle u) const override;
```
获取 uniform 变量名的 C 字符串。

**numUniforms**
```cpp
int numUniforms() const override;
```
返回 uniform 总数。

**uniform**
```cpp
UniformInfo& uniform(int idx) override;
const UniformInfo& uniform(int idx) const override;
```
按索引访问 uniform 信息。

### 偏移量与布局管理

**getRTFlipOffset**
```cpp
uint32_t getRTFlipOffset() const;
```
计算 RT flip 合成 uniform 的偏移量，用于处理坐标翻转。

**usePushConstants**
```cpp
bool usePushConstants() const;
```
返回是否使用 push constants。

**currentOffset**
```cpp
uint32_t currentOffset() const;
```
返回当前偏移量（根据 push constants 状态选择 std430 或 std140）。

### 内部方法

**internalAddUniformArray**
```cpp
UniformHandle internalAddUniformArray(
    const GrProcessor* owner,
    uint32_t visibility,
    SkSLType type,
    const char* name,
    bool mangleName,
    int arrayCount,
    const char** outName) override;
```
添加 uniform 数组，计算两种布局的偏移量。

**addSampler**
```cpp
SamplerHandle addSampler(
    const GrBackendFormat& backendFormat,
    GrSamplerState state,
    const skgpu::Swizzle& swizzle,
    const char* name,
    const GrShaderCaps* shaderCaps) override;
```
添加纹理采样器，生成描述符集布局限定符，处理 YCbCr 不可变采样器。

**addInputSampler**
```cpp
SamplerHandle addInputSampler(
    const skgpu::Swizzle& swizzle,
    const char* name) override;
```
添加 input attachment 采样器，用于 subpass 输入。

**appendUniformDecls**
```cpp
void appendUniformDecls(GrShaderFlags visibility, SkString* out) const override;
```
生成着色器 uniform 声明代码，包括描述符集布局和 push constants 布局。

## 内部实现细节

### 内存对齐计算

**sksltype_to_alignment_mask** 函数根据 Vulkan 规范计算对齐掩码：
```cpp
static uint32_t sksltype_to_alignment_mask(SkSLType type);
```

对齐规则（遵循 Vulkan spec 14.5.4）：
- `short/ushort`: 2 字节对齐（mask = 0x1）
- `short2/ushort2`: 4 字节对齐（mask = 0x3）
- `int/uint/float`: 4 字节对齐（mask = 0x3）
- `vec2`: 8 字节对齐（mask = 0x7）
- `vec3/vec4/mat`: 16 字节对齐（mask = 0xF）

**get_aligned_offset** 函数计算实际偏移量：
```cpp
static uint32_t get_aligned_offset(
    uint32_t* currentOffset,
    SkSLType type,
    int arrayCount,
    int layout);
```

算法：
1. 获取对齐掩码
2. std140 布局中数组和 2x2 矩阵强制 16 字节对齐
3. 计算对齐差值：`offsetDiff = currentOffset & alignmentMask`
4. 如果不对齐，添加填充：`padding = alignmentMask - offsetDiff + 1`
5. 数组元素对齐到至少 16 字节

### Uniform 添加流程

**internalAddUniformArray** 实现：
1. **名称处理**：如果名称以 'u' 开头或包含 `GR_NO_MANGLE_PREFIX`，则不添加前缀
2. **名称混淆**：调用 `fProgramBuilder->nameVariable()` 生成唯一名称
3. **偏移量计算**：为两种布局（std140 和 std430）计算偏移量
4. **信息存储**：将 `VkUniformInfo` 添加到 `fUniforms` 列表
5. **句柄返回**：返回 uniform 索引作为句柄

关键代码：
```cpp
for (int layout = 0; layout < kLayoutCount; ++layout) {
    tempInfo.fOffsets[layout] = get_aligned_offset(
        &fCurrentOffsets[layout], type, arrayCount, layout);
}
```

### 采样器管理

**addSampler** 实现：
1. **布局限定符生成**：
```cpp
layoutQualifier.appendf("vulkan, set=%d, binding=%d",
                       kSamplerDescSet, fSamplers.count());
```

2. **YCbCr 外部格式处理**：
```cpp
auto ycbcrInfo = GrBackendFormats::GetVkYcbcrConversionInfo(backendFormat);
if (ycbcrInfo && ycbcrInfo->isValid()) {
    GrVkSampler* sampler = gpu->resourceProvider()
        .findOrCreateCompatibleSampler(state, *ycbcrInfo);
    fSamplers.back().fImmutableSampler = sampler;
}
```

不可变采样器用于 YCbCr 转换，在描述符集布局创建时指定。

3. **Swizzle 同步**：
```cpp
fSamplerSwizzles.push_back(swizzle);
SkASSERT(fSamplerSwizzles.size() == fSamplers.count());
```

### Input Attachment 支持

**addInputSampler** 生成特殊的布局限定符：
```cpp
auto layoutQualifier = SkStringPrintf(
    "vulkan, input_attachment_index=%d, set=%d, binding=%d",
    kDstInputAttachmentIndex, kInputDescSet, kInputBinding);
```

Input attachment 用于 subpass 之间的数据传递，属于 `SkSLType::kInput` 类型。

### Push Constants 决策

**determineIfUsePushConstants** 逻辑：
```cpp
void GrVkUniformHandler::determineIfUsePushConstants() const {
    static constexpr uint32_t kPad = 2*sizeof(float);  // RTFlip 预留空间
    fUsePushConstants =
        fCurrentOffsets[kStd430Layout] > 0 &&
        fCurrentOffsets[kStd430Layout] + kPad <=
            fProgramBuilder->caps()->maxPushConstantsSize();
}
```

使用条件：
- 有 uniform 数据（偏移量 > 0）
- 总大小加预留空间不超过设备 push constants 限制

Push constants 比 uniform buffer 更快，但容量有限（通常 128-256 字节）。

### 着色器代码生成

**appendUniformDecls** 生成三部分声明：

1. **采样器声明**：
```cpp
for (const VkUniformInfo& sampler : fSamplers.items()) {
    if (visibility == sampler.fVisibility) {
        sampler.fVariable.appendDecl(fProgramBuilder->shaderCaps(), out);
        out->append(";\n");
    }
}
```

2. **Input attachment 声明**：
```cpp
if (fInputUniform.fVariable.getType() == SkSLType::kInput) {
    fInputUniform.fVariable.appendDecl(..., out);
    out->append(";\n");
}
```

3. **Uniform block 声明**：
```cpp
if (fUsePushConstants) {
    out->append("layout (vulkan, push_constant) ");
} else {
    out->appendf("layout (vulkan, set=%d, binding=%d) ",
                 kUniformBufferDescSet, kUniformBinding);
}
out->append("uniform uniformBuffer\n{\n");
// 每个 uniform 带 layout(offset=X)
out->appendf("%s\n};\n", uniformsString.c_str());
```

### 资源清理

析构函数释放不可变采样器：
```cpp
GrVkUniformHandler::~GrVkUniformHandler() {
    for (VkUniformInfo& sampler : fSamplers.items()) {
        if (sampler.fImmutableSampler) {
            sampler.fImmutableSampler->unref();
            sampler.fImmutableSampler = nullptr;
        }
    }
}
```

YCbCr 不可变采样器通过引用计数管理生命周期。

## 依赖关系

### 内部依赖
- `GrVkGpu`: GPU 接口，获取资源提供器
- `GrVkPipelineStateBuilder`: 管道状态构建器，提供程序构建器接口
- `GrVkResourceProvider`: 资源提供器，创建不可变采样器
- `GrVkSampler`: Vulkan 采样器对象
- `GrVkDescriptorSetManager`: 描述符集管理器

### 基类依赖
- `GrGLSLUniformHandler`: 跨后端 uniform 处理基类
- `GrGLSLProgramBuilder`: 着色器程序构建器

### 工具类依赖
- `SkTBlockList`: 块列表容器，用于存储 uniform 信息
- `skgpu::Swizzle`: 通道 swizzle 映射
- `GrShaderVar`: 着色器变量定义
- `GrSamplerState`: 采样器状态封装

### 外部依赖
- `GrBackendFormat`: 后端格式信息
- `GrCaps`: GPU 能力查询（maxPushConstantsSize）
- `SkSLType`: SkSL 类型系统
- `GrShaderCaps`: 着色器能力查询

## 设计模式与设计决策

### 双布局策略

同时维护 std140 和 std430 两种布局的偏移量：
- **std140**: Uniform Buffer 使用，对齐规则更严格（数组 16 字节对齐）
- **std430**: Push Constants 使用，对齐规则更紧凑（节省空间）

在 uniform 添加阶段计算两种偏移量，延迟到 `appendUniformDecls` 时决定使用哪种。

### 描述符集绑定顺序设计

```cpp
kUniformBufferDescSet = 0;  // 最先绑定
kSamplerDescSet = 1;        // 其次绑定
kInputDescSet = 2;          // 最后绑定
```

设计理由：
- Vulkan 绑定描述符集会使所有更高索引的描述符集失效
- Uniform buffer 每管道绑定一次
- 采样器可能因动态状态每绘制重新绑定
- Input attachment 在采样器之后，避免频繁失效

### 不可变采样器机制

对于 YCbCr 格式纹理，使用不可变采样器：
```cpp
fSamplers.back().fImmutableSampler = sampler;
```

不可变采样器在描述符集布局创建时指定，无法在描述符集更新时修改，适用于固定的格式转换配置。

### 延迟决策模式

Push constants 的使用决策延迟到 `appendUniformDecls` 调用时：
```cpp
this->determineIfUsePushConstants();
```

此时所有 uniform 已添加完毕，可以准确计算总大小并与设备限制比较。

### 名称混淆策略

自动为 uniform 名称添加前缀（默认 'u'），但支持例外：
```cpp
if ('u' == name[0] || !strncmp(name, GR_NO_MANGLE_PREFIX, ...)) {
    prefix = '\0';  // 不添加前缀
}
```

这允许特殊 uniform（如 view matrix）使用预定义名称，避免与处理器代码不匹配。

### 块分配策略

使用 `SkTBlockList` 而非 `std::vector`：
```cpp
UniformInfoArray fUniforms(kUniformsPerBlock);
```

`SkTBlockList` 按块分配内存（每块 8 个元素），避免频繁扩容导致的元素地址变化，适合需要返回元素指针的场景。

## 性能考量

### Push Constants 优化

优先使用 push constants：
- **延迟更低**：直接写入命令缓冲区，无需描述符集绑定
- **带宽更高**：通常位于芯片缓存中，访问更快
- **限制严格**：容量小（128-256 字节），需谨慎决策

### 对齐优化

std430 布局比 std140 更紧凑：
- 2x2 矩阵：std430 = 16 字节，std140 = 32 字节
- 数组元素：std430 按实际大小对齐，std140 强制 16 字节

使用 push constants 时选择 std430，节省宝贵的空间。

### 描述符集绑定优化

按更新频率排序描述符集：
- Uniform buffer（频率低）→ set 0
- 采样器（频率高）→ set 1
- Input attachment（频率高）→ set 2

这样动态状态变化时只需重新绑定高索引描述符集，减少状态切换开销。

### 不可变采样器缓存

通过 `GrVkResourceProvider::findOrCreateCompatibleSampler` 复用不可变采样器，避免重复创建相同配置的采样器对象。

### 内存对齐掩码优化

使用位掩码检查对齐：
```cpp
uint32_t offsetDiff = *currentOffset & alignmentMask;
```

比取模运算更快，利用对齐值总是 2 的幂的特性。

### 偏移量预计算

在 uniform 添加时计算偏移量，`appendUniformDecls` 时直接使用：
```cpp
uniformsString.appendf("layout(offset=%u) ", localUniform.fOffsets[layout]);
```

避免在代码生成阶段重新计算，提高编译性能。

## 相关文件

### 核心实现文件
- `src/gpu/ganesh/vk/GrVkGpu.h/cpp`: Vulkan GPU 接口
- `src/gpu/ganesh/vk/GrVkPipelineStateBuilder.h/cpp`: 管道状态构建器
- `src/gpu/ganesh/vk/GrVkDescriptorSetManager.h/cpp`: 描述符集管理器
- `src/gpu/ganesh/vk/GrVkResourceProvider.h/cpp`: 资源提供器
- `src/gpu/ganesh/vk/GrVkSampler.h/cpp`: Vulkan 采样器

### 基类文件
- `src/gpu/ganesh/glsl/GrGLSLUniformHandler.h`: Uniform 处理基类
- `src/gpu/ganesh/glsl/GrGLSLProgramBuilder.h/cpp`: 程序构建器

### 工具类文件
- `src/base/SkTBlockList.h`: 块列表容器
- `src/gpu/Swizzle.h`: Swizzle 定义
- `src/gpu/ganesh/GrShaderVar.h`: 着色器变量定义
- `src/gpu/ganesh/GrSamplerState.h`: 采样器状态
- `src/core/SkSLTypeShared.h`: SkSL 类型系统

### 接口文件
- `include/gpu/ganesh/GrBackendSurface.h`: 后端表面接口
- `include/gpu/ganesh/vk/GrVkBackendSurface.h`: Vulkan 后端表面
- `include/gpu/vk/VulkanTypes.h`: Vulkan 类型定义
